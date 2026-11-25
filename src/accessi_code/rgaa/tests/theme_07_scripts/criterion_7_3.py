"""
RGAA 4.1.2 — critère 7.3 : chaque script est-il contrôlable par le clavier et par
tout dispositif de pointage (hors cas particuliers) ?

7.3.1 — chaque élément qui possède un gestionnaire d'événement est utilisable au
clavier, ou un autre élément de la page permet la même action au clavier :
- élément natif (bouton, lien, champ…) → PASS ;
- élément non natif atteignable (tabindex ≥ 0) avec une gestion des touches → PASS ;
- élément non natif qu'on ne peut pas atteindre au clavier, ou sans aucune gestion
  des touches → l'existence d'un équivalent est une question de sens, jugée par
  l'IA (``keyboard_equivalent``) : PASS / FAIL, NEEDS_REVIEW si elle est incertaine
  ou absente ; FAIL sans IA si la page n'a aucun autre contrôle utilisable au clavier ;
- gestion des touches possible ailleurs (écoute sur document) → NEEDS_REVIEW ;
- contenu affiché au survol sans équivalent au focus → NEEDS_REVIEW.

7.3.2 — un script ne retire pas le focus d'un élément qui le reçoit :
- ``.blur()`` appelé quand un élément reçoit le focus (onfocus, focusin) → FAIL ;
- autre appel à ``.blur()`` → NEEDS_REVIEW ;
- aucun appel → PASS (NOT_APPLICABLE si la page n'a aucun script).
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import component_identifier, component_name, component_role, normalize
from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.scripts import inline_handlers, page_scripts, trigger_at
from accessi_code.analysis.structure import accessible_text, is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_07_scripts._common import (
    ACTIVATION_EVENTS,
    FOCUS_EVENTS,
    HOVER_EVENTS,
    KEY_EVENTS,
    handlers_by_element,
    is_disabled,
    is_focusable,
    is_native_control,
    native_replacement,
)

EMPTY_731 = "Aucun élément avec un gestionnaire d'événement contrôlé par un script."
KEYBOARD_RECOMMENDATION = (
    'Utiliser un élément natif (button ou lien), ou rendre le composant atteignable (tabindex="0") et '
    "activable avec les touches Entrée et Espace."
)
HOVER_RECOMMENDATION = (
    "Déclencher aussi l'affichage quand le composant reçoit le focus (onfocus), et le rendre atteignable au "
    "clavier s'il ne l'est pas."
)
BLUR = re.compile(r"\.\s*blur\s*\(\s*\)")
FOCUS_DETAIL = re.compile(r"événement focus(?:in)?\b")
BLUR_RECOMMENDATION = "Ne pas retirer le focus d'un élément qui le reçoit (supprimer l'appel à blur())."


class KeyboardTest(RGAATest):
    criterion_id = "7.3"
    required_capabilities = frozenset({Capability.DOM})

    def _soup(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom


def keyboard_controls(soup: BeautifulSoup, exclude: Tag) -> list[str]:
    """Contrôles natifs de la page, utilisables au clavier, sous la forme « rôle « nom » »."""
    controls: list[str] = []
    for element in soup.find_all(True):
        if element is exclude or not is_native_control(element) or is_disabled(element) or is_hidden(element):
            continue
        role, _ = component_role(element)
        name, _ = component_name(element, soup)
        entry = f"{role or element.name} « {name} »" if name else ""
        if entry and entry not in controls:
            controls.append(entry)
    return controls[:40]


class Test731(KeyboardTest):
    """7.3.1 : éléments avec un gestionnaire d'événement utilisables au clavier (ou équivalent)."""

    test_id = "7.3.1"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        sources = page_scripts(context)
        grouped, global_listeners, _unresolved = handlers_by_element(sources, soup)
        global_keys = any(listener.event in KEY_EVENTS for listener in global_listeners)

        candidates = [
            handlers
            for handlers in grouped
            if handlers.events & (ACTIVATION_EVENTS | HOVER_EVENTS)
            and not is_hidden(handlers.element)
            and not is_disabled(handlers.element)
        ]
        if not candidates:
            return not_applicable(self, EMPTY_731)

        outcomes: list[Outcome | None] = [None] * len(candidates)
        to_judge: list[tuple[int, str, RelevanceItem]] = []
        for index, handlers in enumerate(candidates):
            element = handlers.element
            identifier = component_identifier(element, index)
            events = handlers.events
            evidence = {"events": sorted(events), "code": normalize(handlers.code(events))[:300]}
            focusable = is_focusable(element)
            keyboard = is_native_control(element) or (focusable and bool(events & KEY_EVENTS))

            if events & ACTIVATION_EVENTS and not keyboard:
                if focusable and global_keys:
                    outcomes[index] = make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        identifier,
                        "Le composant reçoit le focus mais ne gère pas lui-même les touches : vérifier que la "
                        "gestion du clavier ajoutée sur le document l'active avec Entrée et Espace.",
                        KEYBOARD_RECOMMENDATION,
                        node=element,
                        **evidence,
                    )
                    continue
                reason = (
                    "il ne réagit à aucune touche du clavier"
                    if focusable
                    else "on ne peut pas l'atteindre avec la touche Tab"
                )
                controls = keyboard_controls(soup, element)
                recommendation = KEYBOARD_RECOMMENDATION + native_replacement(element, handlers.code(ACTIVATION_EVENTS))
                if not controls:
                    outcomes[index] = make_outcome(
                        TestStatus.FAIL,
                        identifier,
                        f"Le composant n'est utilisable qu'à la souris : {reason}, et la page n'a aucun autre "
                        "contrôle utilisable au clavier.",
                        recommendation,
                        node=element,
                        **evidence,
                    )
                    continue
                to_judge.append(
                    (
                        index,
                        reason,
                        RelevanceItem(
                            text=normalize(accessible_text(element))[:200] or "(sans texte)",
                            element_html=str(element)[:400],
                            context="Contrôles utilisables au clavier : " + "; ".join(controls),
                            details={"action": evidence["code"]},
                        ),
                    )
                )
                continue

            if events & HOVER_EVENTS and not events & FOCUS_EVENTS:
                hover_code = handlers.code(HOVER_EVENTS)
                inline = all(listener.element is not None for listener in handlers.listeners)
                changes = {"onfocus": hover_code} if inline and hover_code else {}
                if not focusable:
                    changes["tabindex"] = "0"
                example = f" Exemple : {opening_tag(element)} → {opening_tag(element, **changes)}" if changes else ""
                outcomes[index] = make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    identifier,
                    "Le script réagit au survol de la souris, mais pas au focus : vérifier que la même "
                    "information est disponible au clavier.",
                    HOVER_RECOMMENDATION + example,
                    node=element,
                    **evidence,
                )
                continue

            outcomes[index] = make_outcome(TestStatus.PASS)

        verdicts = await judge_relevance(services, "keyboard_equivalent", [item for _, _, item in to_judge])
        for (index, reason, item), verdict in zip(to_judge, verdicts, strict=True):
            handlers = candidates[index]
            outcomes[index] = make_outcome(
                verdict.status,
                component_identifier(handlers.element, index),
                verdict.message(
                    f"Le composant n'est utilisable qu'à la souris : {reason}, et aucun autre élément de la page "
                    "ne permet la même action au clavier.",
                    f"Le composant n'est utilisable qu'à la souris ({reason}) : l'existence d'un équivalent "
                    "utilisable au clavier reste à vérifier.",
                ),
                KEYBOARD_RECOMMENDATION + native_replacement(handlers.element, handlers.code(ACTIVATION_EVENTS)),
                node=handlers.element,
                events=sorted(handlers.events),
                code=item.details["action"],
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=EMPTY_731,
            noun="élément(s) avec gestionnaire d'événement",
        )


class Test732(KeyboardTest):
    """7.3.2 : un script ne retire pas le focus d'un élément qui le reçoit."""

    test_id = "7.3.2"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        sources = page_scripts(context)
        handlers = inline_handlers(soup)
        if not sources and not handlers:
            return not_applicable(self, "Aucun script dans la page.")

        outcomes: list[Outcome] = []
        for index, handler in enumerate(handlers):
            if not BLUR.search(handler.code):
                continue
            element = handler.element
            if handler.event in FOCUS_EVENTS:
                rest = BLUR.sub("", handler.code).replace("this", "").strip(" ;")
                example = (
                    f" Exemple : {opening_tag(element)} → {opening_tag(element, **{'on' + handler.event: None})}"
                    if not rest
                    else ""
                )
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        component_identifier(element, index),
                        f"Le focus est retiré de l'élément dès qu'il le reçoit (attribut on{handler.event}).",
                        BLUR_RECOMMENDATION + example,
                        node=element,
                        code=handler.code[:300],
                    )
                )
            else:
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        component_identifier(element, index),
                        f"Un appel à blur() dans l'attribut on{handler.event} retire le focus : vérifier qu'il ne "
                        "le retire pas à un élément qui vient de le recevoir.",
                        BLUR_RECOMMENDATION,
                        node=element,
                        code=handler.code[:300],
                    )
                )

        for source in sources:
            for match in BLUR.finditer(source.masked):
                info = trigger_at(sources, source, match.start(), soup)
                on_focus = bool(FOCUS_DETAIL.search(info.detail))
                location = source.location(match.start())
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL if on_focus else TestStatus.NEEDS_REVIEW,
                        source.label,
                        "Le script retire le focus d'un élément dès qu'il le reçoit."
                        if on_focus
                        else f"Le script retire le focus d'un élément ({info.detail}) : vérifier qu'il ne le retire "
                        "pas à un élément qui vient de le recevoir.",
                        BLUR_RECOMMENDATION,
                        **location,
                        code=source.snippet(match.start()),
                    )
                )

        if not outcomes:
            result = build_result(self, [make_outcome(TestStatus.PASS)], empty_summary="")
            result.summary = "Aucun script ne retire le focus d'un élément."
            return result
        return build_result(self, outcomes, empty_summary="", noun="retrait(s) du focus")

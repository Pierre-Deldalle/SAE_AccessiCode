"""
RGAA 4.1.2 — critère 7.4 : pour chaque script qui initie un changement de
contexte, l'utilisateur est-il averti ou en a-t-il le contrôle ?

Changements de contexte repérés dans le code des gestionnaires d'événement :
nouvelle fenêtre (window.open), nouvelle page (location, history), envoi de
formulaire (submit()).

7.4.1 — chaque changement vérifie une de ces conditions : il est initié par un
bouton ou un lien explicite, ou l'utilisateur est averti par un texte avant :
- clic sur un bouton ou un lien natif → PASS ;
- sinon (choix dans une liste, saisie, clic sur un élément non natif…), aucun texte
  autour du composant → FAIL ; un texte existe → l'IA juge s'il avertit
  (``context_change_warning``) : PASS / FAIL, NEEDS_REVIEW si elle est incertaine
  ou absente ;
- écoute de script dont l'élément n'est pas trouvé → NEEDS_REVIEW.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import component_identifier, normalize
from accessi_code.analysis.dom import get_labelledby_text, get_matching_label, get_wrapping_label
from accessi_code.analysis.location import opening_tag, source_file_name
from accessi_code.analysis.scripts import page_scripts
from accessi_code.analysis.structure import is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_07_scripts._common import (
    ACTIVATION_EVENTS,
    ElementHandlers,
    handlers_by_element,
    is_explicit_button_or_link,
    is_text_field,
    native_replacement,
)

CONTEXT_CHANGES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![\w$])window\s*\.\s*open\s*\("), "nouvelle fenêtre"),
    (
        re.compile(
            r"(?<![\w$])(?:window\s*\.\s*|document\s*\.\s*)?location(?:\s*\.\s*href)?\s*=(?!=)"
            r"|location\s*\.\s*(?:assign|replace)\s*\(|history\s*\.\s*(?:back|forward|go)\s*\("
        ),
        "nouvelle page",
    ),
    (re.compile(r"\.\s*submit\s*\(\s*\)"), "envoi de formulaire"),
)
EMPTY_SUMMARY = (
    "Aucun script ne provoque de changement de contexte (nouvelle page, nouvelle fenêtre, envoi de formulaire)."
)
RECOMMENDATION = (
    "Déclencher le changement de contexte par un bouton ou un lien explicite, ou avertir l'utilisateur par un "
    "texte placé avant le composant."
)
EVENT_LABELS = {
    "change": "un choix dans une liste ou un champ",
    "input": "une saisie",
    "blur": "la sortie du champ",
    "focusout": "la sortie du champ",
    "focus": "l'arrivée sur le composant",
    "focusin": "l'arrivée sur le composant",
    "keydown": "une touche",
    "keyup": "une touche",
    "keypress": "une touche",
    "mouseover": "le survol",
    "mouseenter": "le survol",
}


def context_change(code: str) -> str | None:
    """Type de changement de contexte provoqué par ``code``, ou None."""
    for pattern, label in CONTEXT_CHANGES:
        if pattern.search(code):
            return label
    return None


def warning_text(element: Tag, soup: BeautifulSoup) -> str:
    """Textes présentés avec le composant : étiquette, title, description, texte qui le précède."""
    parts: list[str] = []
    for label in (get_matching_label(element, soup), get_wrapping_label(element)):
        if isinstance(label, Tag):
            parts.append(label.get_text(" ", strip=True))
    valid, described = get_labelledby_text(element, soup)
    if valid:
        parts.append(described)
    for attribute in ("aria-label", "title"):
        parts.append(str(element.get(attribute) or ""))
    if not is_text_field(element) and element.name != "input":
        # Texte du composant lui-même (« Aide (ouvre une nouvelle page) ») ; pas pour une liste, dont le
        # texte est celui des options.
        parts.append(element.get_text(" ", strip=True))
    for reference in str(element.get("aria-describedby") or "").split():
        target = soup.find(id=reference)
        if isinstance(target, Tag):
            parts.append(target.get_text(" ", strip=True))
    previous = element.find_previous_sibling()
    if isinstance(previous, Tag) and not is_hidden(previous):
        parts.append(previous.get_text(" ", strip=True))
    if isinstance(element.parent, Tag):
        before = [
            str(node) if not isinstance(node, Tag) else node.get_text(" ", strip=True)
            for node in element.previous_siblings
            if not (isinstance(node, Tag) and (node.name in {"script", "style"} or is_hidden(node)))
        ]
        parts.append(" ".join(reversed(before)))
    unique: list[str] = []
    for part in (normalize(part) for part in parts):
        if part and part not in unique:
            unique.append(part)
    return " — ".join(unique)[:400]


def _example(element: Tag, event: str, code: str) -> str:
    """Correction « avant → après » : bouton de validation pour un champ, élément natif sinon."""
    if event in ACTIVATION_EVENTS:
        return native_replacement(element, code)
    if is_text_field(element) and element.has_attr(f"on{event}"):
        return (
            f" Exemple : {opening_tag(element)} → {opening_tag(element, **{'on' + event: None})} suivi de "
            '<button type="button">Valider</button>, qui exécute l\'action.'
        )
    return ""


class Test741(RGAATest):
    test_id = "7.4.1"
    criterion_id = "7.4"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        sources = page_scripts(context)
        grouped, _global, unresolved = handlers_by_element(sources, soup)

        outcomes: list[Outcome | None] = []
        to_judge: list[tuple[int, ElementHandlers, str, str, RelevanceItem]] = []
        for index, handlers in enumerate(grouped):
            element = handlers.element
            changes = [
                (listener, change)
                for listener in handlers.listeners
                if (change := context_change(listener.code)) is not None
            ]
            if not changes:
                continue
            listener, change = changes[0]
            event = listener.event
            evidence = {"event": event, "change": change, "code": normalize(listener.code)[:300]}

            if event in ACTIVATION_EVENTS and is_explicit_button_or_link(element):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue

            trigger = (
                "un clic sur un élément qui n'est ni un bouton ni un lien"
                if event in ACTIVATION_EVENTS
                else (EVENT_LABELS.get(event, f"l'événement {event}"))
            )
            text = warning_text(element, soup)
            if not text:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        component_identifier(element, index),
                        f"Le script provoque un changement de contexte ({change}) déclenché par {trigger}, sans "
                        "bouton ni lien explicite et sans texte qui en avertit l'utilisateur.",
                        RECOMMENDATION + _example(element, event, listener.code),
                        node=element,
                        **evidence,
                    )
                )
                continue
            outcomes.append(None)
            to_judge.append(
                (
                    len(outcomes) - 1,
                    handlers,
                    trigger,
                    change,
                    RelevanceItem(
                        text=text,
                        element_html=str(element)[:400],
                        context=f"Déclenché par {trigger}",
                        details={"change": change, "action": evidence["code"]},
                    ),
                )
            )

        verdicts = await judge_relevance(services, "context_change_warning", [entry[-1] for entry in to_judge])
        for (position, handlers, trigger, change, item), verdict in zip(to_judge, verdicts, strict=True):
            element = handlers.element
            listener = next(entry for entry in handlers.listeners if context_change(entry.code))
            outcomes[position] = make_outcome(
                verdict.status,
                component_identifier(element, grouped.index(handlers)),
                verdict.message(
                    f"Le script provoque un changement de contexte ({change}) déclenché par {trigger}, et le texte "
                    "présenté n'en avertit pas l'utilisateur.",
                    f"Le script provoque un changement de contexte ({change}) déclenché par {trigger} : vérifier "
                    "que le texte présenté en avertit l'utilisateur.",
                ),
                verdict.recommendation(RECOMMENDATION) + _example(element, listener.event, listener.code),
                node=element,
                event=listener.event,
                change=change,
                warning_text=item.text,
                **verdict.evidence,
            )

        for listener in unresolved:
            change = context_change(listener.code)
            if change is None or listener.source is None:
                continue
            source = listener.source
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    source.label,
                    f"Le script provoque un changement de contexte ({change}) sur l'événement {listener.event}, "
                    "pour un élément non identifié : vérifier qu'il s'agit d'un bouton ou d'un lien explicite, "
                    "ou que l'utilisateur est averti.",
                    RECOMMENDATION,
                    file=source_file_name(context, source.path) if source.path else None,
                    line=source.line_of(listener.position),
                    event=listener.event,
                    change=change,
                    code=source.snippet(listener.position),
                )
            )

        found = [item for item in outcomes if item is not None]
        if not found:
            return not_applicable(self, EMPTY_SUMMARY)
        return build_result(self, found, empty_summary=EMPTY_SUMMARY, noun="changement(s) de contexte")

"""
RGAA 4.1.2 — critère 13.2 : dans chaque page web, l'ouverture d'une nouvelle
fenêtre ne doit pas être déclenchée sans action de l'utilisateur.

Chaque appel à ``window.open()`` (script ou attribut ``on…``) est rattaché à
ce qui le déclenche (``analysis/scripts.trigger_at``) :
- action de l'utilisateur (clic, touche, soumission…) → PASS ;
- chargement de la page (code exécuté directement, load, DOMContentLoaded…)
  → FAIL, ou NEEDS_REVIEW si l'appel dépend d'une condition ;
- minuteur, focus, survol ou fonction appelée ailleurs → NEEDS_REVIEW.

Les liens ``target="_blank"`` s'ouvrent sur action de l'utilisateur : ils ne
sont pas concernés.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.components import component_identifier
from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.scripts import (
    ScriptSource,
    Trigger,
    TriggerInfo,
    event_trigger,
    inline_handlers,
    matching_paren,
    page_scripts,
    trigger_at,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

WINDOW_OPEN = re.compile(r"(?<![\w$])window\s*\.\s*open\s*\(")
EMPTY_SUMMARY = "Aucune ouverture de fenêtre par window.open() dans la page."
RECOMMENDATION = "Ne déclencher l'ouverture d'une nouvelle fenêtre qu'à la suite d'une action de l'utilisateur."
# Texte à remplacer dans l'exemple : l'intitulé du bouton dépend de la fenêtre ouverte.
BUTTON_LABEL = "[intitulé du bouton]"


def open_button(code: str) -> str:
    """Bouton qui ouvre la fenêtre au clic, avec le vrai code d'ouverture."""
    button = BeautifulSoup("", "html.parser").new_tag("button", attrs={"type": "button", "onclick": code})
    return f"{opening_tag(button)}{BUTTON_LABEL}</button>"


def window_open_call(source: ScriptSource, start: int) -> str:
    """Texte de l'appel window.open(…) commençant à ``start``."""
    closing = matching_paren(source.masked, source.masked.find("(", start))
    return " ".join(source.code[start : closing + 1].split())


def handler_example(element: Tag, event: str, code: str) -> str:
    """Attribut on… retiré de l'élément, ouverture déplacée sur un bouton."""
    attribute = next(name for name in element.attrs if str(name).lower() == f"on{event}")
    return f"Exemple : {opening_tag(element)} → {opening_tag(element, **{attribute: None})} et {open_button(code)}"


def _outcome(info: TriggerInfo, element: str, code: str, location: dict[str, Any], example: str) -> Outcome:
    evidence = {"trigger": info.trigger.value, "detail": info.detail, "code": code}
    if info.trigger is Trigger.USER:
        return make_outcome(TestStatus.PASS)
    if info.trigger is Trigger.LOAD and not info.conditional:
        return make_outcome(
            TestStatus.FAIL,
            element,
            f"Une nouvelle fenêtre s'ouvre sans action de l'utilisateur ({info.detail}).",
            f"{RECOMMENDATION} {example}",
            **location,
            **evidence,
        )
    reason = {
        Trigger.LOAD: f"au chargement de la page, sous condition ({info.detail})",
        Trigger.TIMER: f"par un minuteur ({info.detail})",
    }.get(info.trigger, f"par un déclencheur qui n'est pas forcément une action de l'utilisateur ({info.detail})")
    return make_outcome(
        TestStatus.NEEDS_REVIEW,
        element,
        f"L'ouverture d'une nouvelle fenêtre est déclenchée {reason} : vérifier qu'elle suit une action "
        "de l'utilisateur.",
        RECOMMENDATION,
        **location,
        **evidence,
    )


class Test1321(RGAATest):
    test_id = "13.2.1"
    criterion_id = "13.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        sources = page_scripts(context)
        outcomes: list[Outcome] = []
        for source in sources:
            for match in WINDOW_OPEN.finditer(source.masked):
                info = trigger_at(sources, source, match.start(), soup)
                call = window_open_call(source, match.start())
                example = f"Exemple : {call} exécuté au chargement → {open_button(call)}"
                outcomes.append(
                    _outcome(info, source.label, source.snippet(match.start()), source.location(match.start()), example)
                )

        for index, handler in enumerate(inline_handlers(soup)):
            if not WINDOW_OPEN.search(handler.code):
                continue
            trigger = event_trigger(handler.event)
            info = TriggerInfo(trigger, f"attribut on{handler.event}")
            element = component_identifier(handler.element, index)
            example = handler_example(handler.element, handler.event, handler.code)
            outcomes.append(_outcome(info, element, handler.code[:200], {"node": handler.element}, example))

        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="ouverture(s) de fenêtre")

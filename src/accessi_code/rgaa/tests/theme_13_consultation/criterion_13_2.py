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

from bs4 import BeautifulSoup

from accessi_code.analysis.components import component_identifier
from accessi_code.analysis.scripts import Trigger, TriggerInfo, event_trigger, inline_handlers, page_scripts, trigger_at
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

WINDOW_OPEN = re.compile(r"(?<![\w$])window\s*\.\s*open\s*\(")
EMPTY_SUMMARY = "Aucune ouverture de fenêtre par window.open() dans la page."
RECOMMENDATION = "Ne déclencher l'ouverture d'une nouvelle fenêtre qu'à la suite d'une action de l'utilisateur."


def _outcome(info: TriggerInfo, element: str, code: str) -> Outcome:
    evidence = {"trigger": info.trigger.value, "detail": info.detail, "code": code}
    if info.trigger is Trigger.USER:
        return make_outcome(TestStatus.PASS)
    if info.trigger is Trigger.LOAD and not info.conditional:
        return make_outcome(
            TestStatus.FAIL,
            element,
            f"Une nouvelle fenêtre s'ouvre sans action de l'utilisateur ({info.detail}).",
            RECOMMENDATION,
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
                outcomes.append(_outcome(info, source.label, source.snippet(match.start())))

        for index, handler in enumerate(inline_handlers(soup)):
            if not WINDOW_OPEN.search(handler.code):
                continue
            trigger = event_trigger(handler.event)
            info = TriggerInfo(trigger, f"attribut on{handler.event}")
            outcomes.append(_outcome(info, component_identifier(handler.element, index), handler.code[:200]))

        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="ouverture(s) de fenêtre")

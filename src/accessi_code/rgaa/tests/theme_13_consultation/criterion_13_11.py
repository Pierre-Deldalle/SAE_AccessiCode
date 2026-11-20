"""
RGAA 4.1.2 — critère 13.11 : dans chaque page web, les actions déclenchées au
moyen d'un dispositif de pointage sur un point unique de l'écran peuvent-elles
faire l'objet d'une annulation (hors cas particuliers) ?

Une action est conforme si elle est déclenchée au relâchement (click, mouseup…),
ou déclenchée à l'appui puis annulée au relâchement, ou si un mécanisme permet
de l'annuler.

- actions au relâchement seulement (liens, boutons, click) → PASS ;
- action à l'appui (mousedown, pointerdown, touchstart) sans gestionnaire de
  relâchement ni bouton « Annuler » dans la page → FAIL (sauf cas particulier
  comme une touche de piano ou un jeu) ;
- action à l'appui avec un gestionnaire de relâchement ou un bouton
  « Annuler » → NEEDS_REVIEW (vérifier que l'action est bien annulée) ;
- un gestionnaire d'appui qui ne fait que de la mise en forme
  (preventDefault, focus, classe active) n'est pas une action : ignoré ;
- un touchstart qui suit plusieurs doigts ou un déplacement relève de 13.10.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.components import component_identifier, interface_controls, script_components
from accessi_code.analysis.scripts import ListenerCall, event_listeners, page_scripts
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

DOWN_EVENTS = {"mousedown", "pointerdown", "touchstart"}
UP_EVENTS = {"mouseup", "pointerup", "touchend", "click", "pointercancel", "touchcancel", "mouseleave", "pointerleave"}
GESTURE = re.compile(r"\btouches\b|targetTouches|changedTouches", re.IGNORECASE)
COSMETIC = re.compile(
    r"\b(?:e|ev|evt|event)\s*\.\s*(?:preventDefault|stopPropagation|stopImmediatePropagation)\s*\(\s*\)"
    r"|(?:this|[\w$.]+)\s*\.\s*focus\s*\(\s*\)"
    r"|(?:this|[\w$.]+)\s*\.\s*classList\s*\.\s*(?:add|remove|toggle)\s*\([^)]*\)"
    r"|(?:this|[\w$.]+)\s*\.\s*style\s*\.\s*[\w-]+\s*=\s*[^;]+"
    r"|\breturn\s+(?:false|true)\b",
    re.IGNORECASE,
)
UNDO = re.compile(r"\b(?:annuler|undo|rétablir|retablir|défaire|defaire)\b", re.IGNORECASE)
EMPTY_SUMMARY = "Aucune action déclenchée par un dispositif de pointage."
PASS_SUMMARY = "Les actions au pointeur de la page sont déclenchées au relâchement (clic)."
RECOMMENDATION = (
    "Déclencher l'action au relâchement (événement click ou mouseup), ou l'annuler au relâchement, "
    "ou proposer un moyen de l'annuler."
)


def _is_cosmetic(code: str) -> bool:
    remaining = COSMETIC.sub("", code)
    return not re.sub(r"[\s;{}]|function\s*\w*\s*\([^)]*\)|\([^)]*\)\s*=>|\w+\s*=>", "", remaining)


def _has_release(listener: ListenerCall, listeners: list[ListenerCall]) -> bool:
    if listener.element is not None:
        return any(str(name).lower()[2:] in UP_EVENTS for name in listener.element.attrs if str(name).startswith("on"))
    return any(other.source is listener.source for other in listeners if other.event in UP_EVENTS)


class Test13111(RGAATest):
    test_id = "13.11.1"
    criterion_id = "13.11"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        sources = page_scripts(context)
        listeners = event_listeners(sources, soup, DOWN_EVENTS | UP_EVENTS | {"touchmove"})
        undo = [control for control in interface_controls(soup) if UNDO.search(control)]
        outcomes: list[Outcome] = []

        for index, listener in enumerate(listeners):
            if listener.event not in DOWN_EVENTS:
                continue
            if listener.event == "touchstart" and (
                GESTURE.search(listener.code)
                or any(other.event == "touchmove" and other.source is listener.source for other in listeners)
            ):
                continue
            if _is_cosmetic(listener.code):
                continue
            element = component_identifier(listener.element, index) if listener.element is not None else listener.label
            evidence = {"event": listener.event, "code": " ".join(listener.code.split())[:300]}
            if _has_release(listener, listeners) or undo:
                means = (
                    "un gestionnaire de relâchement"
                    if _has_release(listener, listeners)
                    else (f"un bouton d'annulation ({', '.join(undo[:3])})")
                )
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        element,
                        f"Une action est déclenchée à l'appui ({listener.event}) ; la page propose {means} : "
                        "vérifier que l'action peut être annulée.",
                        RECOMMENDATION,
                        **evidence,
                    )
                )
            else:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        element,
                        f"Une action est déclenchée dès l'appui ({listener.event}), sans annulation possible au "
                        "relâchement ni moyen de l'annuler (non conforme sauf cas particulier, comme un jeu).",
                        RECOMMENDATION,
                        **evidence,
                    )
                )

        if not outcomes:
            interactive = soup.find(["a", "button", "input", "select", "textarea", "summary", "area"])
            if interactive is None and not script_components(soup):
                return build_result(self, [], empty_summary=EMPTY_SUMMARY)
            result = build_result(self, [make_outcome(TestStatus.PASS)], empty_summary=EMPTY_SUMMARY)
            result.summary = PASS_SUMMARY
            return result
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="action(s) à l'appui")

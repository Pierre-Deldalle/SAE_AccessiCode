"""
RGAA 4.1.2 — critère 13.10 : dans chaque page web, les fonctionnalités
utilisables ou disponibles au moyen d'un geste complexe peuvent-elles être
également disponibles au moyen d'un geste simple ?

Gestes repérés dans les scripts :
- 13.10.1 : contact multipoint (``touches.length > 1``, ``touches[1]``,
  événements gesture*, pincement ou rotation d'une bibliothèque tactile) ;
- 13.10.2 : suivi de trajectoire (balayage, glisser calculé à partir de la
  position du doigt ou du pointeur).

Savoir si un contrôle de la page offre la même fonctionnalité en un seul
contact, ou si le geste est essentiel (signature, dessin), est une question de
sens : l'IA juge (``gesture_alternative``) à partir de l'extrait de code et de
la liste des contrôles de la page → PASS / FAIL, NEEDS_REVIEW si l'IA est
incertaine ou absente. Aucun geste complexe → NOT_APPLICABLE.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import interface_controls
from accessi_code.analysis.scripts import ScriptSource, page_scripts
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome

MULTIPOINT = re.compile(
    r"(?:touches|pointers|pointerCache|evCache)\w*\s*\.\s*(?:length|size)\s*(?:>=?\s*[12]|===?\s*[2-9])"
    r"|(?:targetTouches|changedTouches|touches)\s*\[\s*1\s*\]"
    r"|['\"`]gesture(?:start|change|end)['\"`]|\.ongesture(?:start|change)"
    r"|['\"`](?:pinch|rotate)(?:start|move|end|in|out)?['\"`]|new\s+Hammer\s*\.\s*(?:Pinch|Rotate)\b",
    re.IGNORECASE,
)
PATH = re.compile(
    r"['\"`](?:swipe|pan)(?:left|right|up|down|start|move|end)?['\"`]|new\s+Hammer\s*\.\s*(?:Swipe|Pan)\b"
    r"|\bswipe\w*\s*[(=:]|\bon\s*swipe"
    r"|(?:touchmove|pointermove)['\"`][\s\S]{0,400}?(?:clientX|pageX|screenX|clientY|pageY|screenY)",
    re.IGNORECASE,
)
RECOMMENDATION = (
    "Proposer la même fonctionnalité avec un contact en un point unique (boutons, liens), sauf si le geste "
    "est essentiel."
)


def gesture_candidates(sources: list[ScriptSource], pattern: re.Pattern[str]) -> list[tuple[ScriptSource, int]]:
    """Première occurrence du geste dans chaque script (un script = une fonctionnalité à juger)."""
    found: list[tuple[ScriptSource, int]] = []
    for source in sources:
        match = pattern.search(source.masked)
        if match:
            found.append((source, match.start()))
    return found


class GestureTest(RGAATest):
    criterion_id = "13.10"
    required_capabilities = frozenset({Capability.DOM})
    pattern: re.Pattern[str]
    gesture: str

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        candidates = gesture_candidates(page_scripts(context), self.pattern)
        controls = interface_controls(soup)
        context_text = "Contrôles de la page : " + ("; ".join(controls) if controls else "aucun")
        items = [
            RelevanceItem(
                text=source.snippet(position, before=200, after=400),
                context=context_text,
                details={"gesture": self.gesture, "script": source.label},
            )
            for source, position in candidates
        ]
        verdicts = await judge_relevance(services, "gesture_alternative", items)
        outcomes = [
            make_outcome(
                verdict.status,
                source.label,
                verdict.message(
                    f"La fonctionnalité utilisable par {self.gesture} n'a pas d'équivalent en un seul contact.",
                    f"L'existence d'un équivalent en un seul contact pour la fonctionnalité utilisable par "
                    f"{self.gesture} reste à vérifier.",
                ),
                RECOMMENDATION,
                **source.location(position),
                gesture=self.gesture,
                code=item.text,
                controls=controls,
                **verdict.evidence,
            )
            for (source, position), item, verdict in zip(candidates, items, verdicts, strict=True)
        ]
        return build_result(self, outcomes, empty_summary=self.empty, noun="fonctionnalité(s)")

    @property
    def empty(self) -> str:
        return f"Aucune fonctionnalité utilisable par {self.gesture} dans les scripts de la page."


class Test13101(GestureTest):
    """13.10.1 : contact multipoint."""

    test_id = "13.10.1"
    pattern = MULTIPOINT
    gesture = "un contact multipoint"


class Test13102(GestureTest):
    """13.10.2 : geste basé sur le suivi d'une trajectoire."""

    test_id = "13.10.2"
    pattern = PATH
    gesture = "un geste de trajectoire"

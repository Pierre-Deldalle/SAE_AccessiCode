"""
RGAA 4.1.2 — critère 2.2 : pour chaque cadre ayant un titre de cadre, ce titre
est-il pertinent ?

Un titre vide est non conforme sans appel à l'IA. Sinon, l'IA juge si le
titre décrit le contenu ou la fonction du cadre, à partir de sa source et du
texte qui l'entoure.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.dom import get_element_identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

RECOMMENDATION = "Rédiger un titre de cadre qui décrit son contenu ou sa fonction."


def frame_context(frame: Tag) -> str:
    """Texte autour du cadre : titre de section le plus proche et texte du parent."""
    heading = frame.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    parent = frame.parent if isinstance(frame.parent, Tag) else None
    parts = [heading.get_text(" ", strip=True) if heading else "", parent.get_text(" ", strip=True) if parent else ""]
    return " — ".join(part for part in parts if part)[:600]


class Test221(RGAATest):
    """2.2.1 : pour chaque cadre ayant un title, le contenu de ce titre est-il pertinent ?"""

    test_id = "2.2.1"
    criterion_id = "2.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 2.2.1 nécessite un DOM.")

        frames = [frame for frame in context.dom.find_all(["iframe", "frame"]) if frame.has_attr("title")]
        if not frames:
            return not_applicable(self, "Aucun cadre avec un attribut title.")

        outcomes: list[Outcome | None] = [None] * len(frames)
        to_judge: list[int] = []
        for position, frame in enumerate(frames):
            if not str(frame.get("title") or "").strip():
                outcomes[position] = make_outcome(
                    TestStatus.FAIL,
                    self._identifier(frame, context.dom),
                    "Le titre du cadre est vide.",
                    RECOMMENDATION,
                    node=frame,
                )
            else:
                to_judge.append(position)

        items = [
            RelevanceItem(
                text=" ".join(str(frames[position].get("title")).split()),
                element_html=str(frames[position])[:400],
                context=frame_context(frames[position]),
                details={"src": str(frames[position].get("src") or frames[position].get("srcdoc") or "")[:300]},
            )
            for position in to_judge
        ]
        verdicts = await judge_relevance(services, "frame_title", items)

        for position, item, verdict in zip(to_judge, items, verdicts, strict=True):
            outcomes[position] = make_outcome(
                verdict.status,
                self._identifier(frames[position], context.dom),
                verdict.message(
                    f"Le titre du cadre « {item.text[:100]} » n'est pas pertinent.",
                    f"La pertinence du titre du cadre « {item.text[:100]} » reste à vérifier.",
                ),
                RECOMMENDATION,
                node=frames[position],
                title=item.text,
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary="Aucun cadre avec un attribut title.",
            noun="cadre(s)",
        )

    @staticmethod
    def _identifier(frame: Tag, soup: BeautifulSoup) -> str:
        return get_element_identifier(frame, soup.find_all(["iframe", "frame"]).index(frame))

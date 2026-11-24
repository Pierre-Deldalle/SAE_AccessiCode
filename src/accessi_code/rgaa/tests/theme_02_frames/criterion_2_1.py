"""RGAA 4.1.2 — critère 2.1 : chaque cadre a-t-il un titre de cadre ?"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.dom import get_element_identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable


class Test211(RGAATest):
    """2.1.1 : chaque cadre (iframe ou frame) a-t-il un attribut title ?"""

    test_id = "2.1.1"
    criterion_id = "2.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 2.1.1 nécessite un DOM.")

        frames = context.dom.find_all(["iframe", "frame"])
        if not frames:
            return not_applicable(self, "Aucun cadre <iframe> ou <frame> détecté.")

        # Un title vide est un titre présent : sa pertinence relève du test 2.2.1.
        outcomes = [
            make_outcome(TestStatus.PASS)
            if frame.has_attr("title")
            else make_outcome(
                TestStatus.FAIL,
                get_element_identifier(frame, index),
                "Le cadre ne possède pas d'attribut title.",
                "Ajouter un attribut title décrivant le contenu ou la fonction du cadre.",
                node=frame,
                src=str(frame.get("src") or ""),
            )
            for index, frame in enumerate(frames)
        ]
        return build_result(self, outcomes, empty_summary="Aucun cadre détecté.", noun="cadre(s)")

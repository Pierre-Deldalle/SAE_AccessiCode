from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test211(RGAATest):
    test_id = "2.1.1"
    criterion_id = "2.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        # Select all iframe and frame elements
        elements = list(soup.select("iframe, frame"))

        if not elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun cadre <iframe> ou <frame> détecté.",
            )

        findings: list[Finding] = []
        compliant = 0
        failed = 0

        for index, element in enumerate(elements):
            if element.has_attr("title"):
                compliant += 1
            else:
                failed += 1
                findings.append(
                    Finding(
                        element=self._identifier(element, index),
                        message="Le cadre ne possède pas d'attribut title.",
                        recommendation="Ajouter un attribut title décrivant le contenu du cadre.",
                    )
                )

        if failed:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(elements)} cadre(s) détecté(s) : "
                f"{compliant} conforme(s), {failed} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(elements),
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 2.1.1 nécessite un DOM.")
        return context.dom

    @staticmethod
    def _identifier(element: Tag, index: int) -> str:
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"
        # Fallback to index-based identifier
        return f"{element.name}[index={index}]"
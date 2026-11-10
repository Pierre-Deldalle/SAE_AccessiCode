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


class Test221(RGAATest):
    test_id = "2.2.1"
    criterion_id = "2.2"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    # Titres considérés comme non pertinents (liste non exhaustive)
    NON_PERTINENT_TITLES = frozenset(
        {
            "",  # vide
            "iframe",
            "frame",
            "title",
            "sans titre",
            "no title",
            "untitled",
            "pub",
            "publicité",
            "ad",
            "ads",
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        # Sélectionner tous les iframe et frame qui possèdent un attribut title
        elements = list(soup.select("iframe[title], frame[title]"))

        if not elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun cadre <iframe> ou <frame> avec un attribut title détecté.",
            )

        findings: list[Finding] = []
        compliant = 0
        non_pertinent = 0

        for index, element in enumerate(elements):
            title_attr = element.get("title", "")
            if isinstance(title_attr, list):
                # Au cas où l'attribut title serait une liste (rare mais possible)
                title_attr = " ".join(title_attr)
            original_title = str(title_attr)
            stripped_title = original_title.strip()

            if not stripped_title or stripped_title.lower() in self.NON_PERTINENT_TITLES:
                non_pertinent += 1
                findings.append(
                    Finding(
                        element=self._identifier(element, index),
                        message=f"Le titre du cadre «{original_title}» n'est pas pertinent.",
                        recommendation=(
                            "Fournir un titre décrivant clairement le contenu ou la fonction du cadre."
                        ),
                    )
                )
            else:
                compliant += 1

        if non_pertinent:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(elements)} cadre(s) avec attribut title : "
                f"{compliant} pertinent(s), {non_pertinent} non pertinent(s)."
            ),
            findings=findings,
            tested_elements=len(elements),
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 2.2.1 nécessite un DOM.")
        return context.dom

    @staticmethod
    def _identifier(element: Tag, index: int) -> str:
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"
        return f"{element.name}[index={index}]"
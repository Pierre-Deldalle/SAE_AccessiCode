from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import (
    get_labelledby_text,
    has_aria_label,
    has_title,
)
from accessi_code.analysis.tables import (
    find_tables,
    has_complex_header_structure,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test541(RGAATest):
    test_id = "5.4.1"
    criterion_id = "5.4"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.4.1 nécessite un DOM.")

        soup = context.dom

        tables = find_tables(soup)

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables: list[Tag] = []
        findings: list[Finding] = []

        for index, table in enumerate(tables):
            # Skip layout tables (those without header cells)
            if not self._is_data_table(table):
                continue

            data_tables.append(table)

            # Check if table has a title mechanism
            title_mechanisms = self._get_title_evidence(table, soup)

            if not title_mechanisms:
                table_id = table.get("id")
                element = (
                    f"table#{table_id}" if (isinstance(table_id, str) and table_id.strip()) else f"table[index={index}]"
                )

                findings.append(
                    Finding(
                        element=element,
                        message=("Aucun titre associé à ce tableau de données."),
                        recommendation=("Associer un titre au tableau de données au moyen d'un élément <caption>, d'un attribut 'title', d'un attribut 'aria-label' ou d'un attribut 'aria-labelledby' faisant référence à un texte descriptif."),
                    )
                )

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(data_tables)} tableau(x) de données, {len(findings)} sans titre associé."),
            findings=findings,
            tested_elements=len(data_tables),
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
            },
        )

    def _is_data_table(self, table: Tag) -> bool:
        """
        Détermine si un tableau est un tableau de données (au sens large).
        Un tableau de données contient au moins une cellule d'en-tête.
        """
        # Vérifier si le tableau contient des cellules d'en-tête
        for element in table.find_all(recursive=False):
            if isinstance(element, Tag) and self._is_header_cell(element):
                return True
            # Récursivement vérifier les enfants
            if self._contains_header_cell(element):
                return True
        return False

    def _is_header_cell(self, cell: Tag) -> bool:
        """Vérifie si une cellule est une cellule d'en-tête."""
        return cell.name == "th" or cell.get("role") in {
            "columnheader",
            "rowheader",
        }

    def _contains_header_cell(self, element: Tag) -> bool:
        """Vérifie récursivement si un élément contient une cellule d'en-tête."""
        for child in element.find_all(recursive=False):
            if isinstance(child, Tag):
                if self._is_header_cell(child):
                    return True
                if self._contains_header_cell(child):
                    return True
        return False

    def _get_title_evidence(self, table: Tag, soup: BeautifulSoup) -> list[str]:
        """
        Retourne les mécanismes de titre utilisables pour le test 5.4.1.
        """
        evidence: list[str] = []

        # Vérifier la présence d'un élément caption
        caption = table.find("caption", recursive=False)
        if isinstance(caption, Tag) and caption.get_text(" ", strip=True):
            evidence.append("caption")

        # Vérifier la présence d'un attribut title
        if has_title(table):
            evidence.append("title")

        # Vérifier la présence d'un attribut aria-label
        if has_aria_label(table):
            evidence.append("aria-label")

        # Vérifier la présence d'un attribut aria-labelledby valide
        labelledby_valid, _ = get_labelledby_text(table, soup)
        if labelledby_valid:
            evidence.append("aria-labelledby")

        return evidence
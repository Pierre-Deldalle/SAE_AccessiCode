from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.tables import (
    find_tables,
    is_header_cell,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test531(RGAATest):
    test_id = "5.3.1"
    criterion_id = "5.3"

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
            raise ValueError("Le test 5.3.1 nécessite un DOM.")

        soup = context.dom

        tables = find_tables(soup)

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        layout_tables: list[Tag] = []
        findings: list[Finding] = []

        for index, table in enumerate(tables):
            if self._is_data_table(table):
                continue

            layout_tables.append(table)

            role = table.get("role")
            has_presentation_role = (
                isinstance(role, str) and
                role.strip().lower() == "presentation"
            )

            content_comprehensible = self._is_linearized_content_comprehensible(table, soup)

            if not has_presentation_role or not content_comprehensible:
                table_id = table.get("id")
                element = (
                    f"table#{table_id}" if (isinstance(table_id, str) and table_id.strip()) else f"table[index={index}]"
                )

                issues = []
                if not has_presentation_role:
                    issues.append("l'attribut role='presentation' est manquant")
                if not content_comprehensible:
                    issues.append("le contenu linéarisé n'est pas compréhensible")

                findings.append(
                    Finding(
                        element=element,
                        message=("Et non : " + " ; ".join(issues)),
                        recommendation=("Pour un tableau de mise en forme, ajouter l'attribut role='presentation' et s'assurer que le contenu reste compréhensible lorsqu'il est linéarisé."),
                    )
                )

        if not layout_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de mise en forme détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(layout_tables)} tableau(x) de mise en forme, {len(findings)} non conforme(s)."),
            findings=findings,
            tested_elements=len(layout_tables),
            metadata={
                "total_tables": len(tables),
                "layout_tables": len(layout_tables),
            },
        )

    def _is_data_table(self, table: Tag) -> bool:
        """
        Détermine si un tableau est un tableau de données (au sens large).
        Un tableau de données contient au moins une cellule d'en-tête.
        """
        for element in table.find_all(recursive=False):
            if isinstance(element, Tag) and is_header_cell(element):
                return True
            if self._contains_header_cell(element):
                return True
        return False

    def _contains_header_cell(self, element: Tag) -> bool:
        """Vérifie récursivement si un élément contient une cellule d'en-tête."""
        for child in element.find_all(recursive=False):
            if isinstance(child, Tag):
                if is_header_cell(child):
                    return True
                if self._contains_header_cell(child):
                    return True
        return False

    def _is_linearized_content_comprehensible(self, table: Tag, soup: BeautifulSoup) -> bool:
        """
        Vérifie si le contenu du tableau reste compréhensible lorsqu'il est linéarisé.
        Lis le contenu dans l'ordre DOM (de gauche à droite, de haut en bas).
        """
        texts = []

        def extract_text_from_element(element):
            if isinstance(element, Tag):
                if element.name in ['td', 'th'] or element.get('role') in ['cell', 'columnheader', 'rowheader']:
                    text = element.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
                for child in element.children:
                    extract_text_from_element(child)
            elif hasattr(element, 'strip') and str(element).strip():
                text = str(element).strip()
                if text:
                    texts.append(text)

        extract_text_from_element(table)

        linearized_content = " ".join(texts)

        if not linearized_content or len(linearized_content.strip()) < 3:
            return False

        content_lower = linearized_content.lower()
        words = content_lower.split()

        if len(words) < 2:
            return False

        filler_indicators = {
            'cellule', 'cell', 'column', 'colonne', 'row', 'ligne',
            'item', 'element', 'data', 'texte', 'text',
            'lorem', 'ipsum', 'dummy', 'placeholder',
            'bloc', 'zone', 'section', 'div', 'span'
        }

        filler_word_count = sum(1 for word in words if word in filler_indicators)

        if len(words) > 0 and (filler_word_count / len(words)) > 0.5:
            return False

        if len(words) >= 4:
            pattern_count = 0
            for i in range(0, len(words) - 2, 2):  # Check pairs of words
                if (i + 1 < len(words) and
                    words[i].isalpha() and
                    words[i + 1].isdigit()):
                    pattern_count += 1

            if len(words) >= 2 and (pattern_count * 2) / len(words) > 0.4:
                return False

        meaningful_words = [word for word in words if word not in filler_indicators and len(word) > 2]
        if len(meaningful_words) == 0:
            return False  # Aucun mot significatif

        return True

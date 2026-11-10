from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test551(RGAATest):
    test_id = "5.5.1"
    criterion_id = "5.5"

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
            raise ValueError("Le test 5.5.1 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        tables_with_title: list[Tag] = []
        findings: list[Finding] = []

        for index, table in enumerate(tables):
            caption = table.find("caption", recursive=False)
            if not (isinstance(caption, Tag) and caption.get_text(" ", strip=True)):
                continue

            tables_with_title.append(table)

            title_text = caption.get_text(" ", strip=True)

            if not self._is_title_pertinent(title_text, table, soup):
                table_id = table.get("id")
                element = (
                    f"table#{table_id}" if (isinstance(table_id, str) and table_id.strip()) else f"table[index={index}]"
                )

                findings.append(
                    Finding(
                        element=element,
                        message=("Le titre du tableau de données n'est pas pertinent."),
                        recommendation=("Fournir un titre qui identifie clairement et concisément le contenu du tableau."),
                    )
                )

        if not tables_with_title:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau avec titre détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(tables_with_title)} tableau(x) avec titre, {len(findings)} avec titre non pertinent."),
            findings=findings,
            tested_elements=len(tables_with_title),
            metadata={
                "total_tables": len(tables),
                "tables_with_title": len(tables_with_title),
            },
        )

    def _is_title_pertinent(self, title_text: str, table: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if a title is pertinent/relevant to the table's content.

        A title is considered pertinent if it:
        1. Is not empty or just whitespace
        2. Contains meaningful information about the table's purpose or content
        3. Is not just generic placeholder text
        4. Is sufficiently descriptive (not too short/vague)
        """
        if not title_text or not title_text.strip():
            return False

        title_normalized = re.sub(r'\s+', ' ', title_text.strip().lower())

        non_pertinent_patterns = [
            r'^\s*tableau\s*$',
            r'^\s*données\s*$',
            r'^\s*info\s*$',
            r'^\s*table\s*$',
            r'^\s*data\s*$',
            r'^\s*\d+\s*$',  # Just numbers
            r'^\s*[^a-zA-Z]*\s*$',  # No letters at all
            r'^\s*title\s*$',  # Generic "title"
            r'^\s*nom\s*$',  # Generic "name"
        ]

        for pattern in non_pertinent_patterns:
            if re.match(pattern, title_normalized):
                return False

        header_texts = self._get_table_header_texts(table)

        if header_texts:
            title_words = set(re.findall(r'\b\w+\b', title_normalized))
            header_words = set(re.findall(r'\b\w+\b', ' '.join(header_texts).lower()))

            stop_words = {
                'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'avec',
                'sur', 'dans', 'par', 'pour', 'vers', 'aux', 'ce', 'cet', 'cette',
                'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
                'tableau', 'table', 'données', 'data', 'information', 'info', 'titre', 'title', 'nom'
            }

            meaningful_title_words = title_words - stop_words
            meaningful_header_words = header_words - stop_words

            if meaningful_title_words and meaningful_header_words:
                if meaningful_title_words & meaningful_header_words:
                    return True

            if meaningful_title_words:
                if len(title_normalized) > 10 and len(meaningful_title_words) > 0:
                    return True

        if len(title_normalized) >= 15 and len(title_normalized.split()) >= 3:
            return True

        return False

    def _get_table_header_texts(self, table: Tag) -> list[str]:
        """Extract all header text from a table."""
        header_texts = []

        for element in table.find_all(['th', 'td']):
            if (element.name == 'th' or
                element.get('role') in ['columnheader', 'rowheader'] or
                element.get('scope') in ['col', 'row', 'colgroup', 'rowgroup']):
                text = element.get_text(" ", strip=True)
                if text:
                    header_texts.append(text)

        return header_texts

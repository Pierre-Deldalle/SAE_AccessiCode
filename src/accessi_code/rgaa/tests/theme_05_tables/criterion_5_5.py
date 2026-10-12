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

        # Find all tables (including role="table")
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
            # Check if table has a title (caption element)
            caption = table.find("caption", recursive=False)
            if not (isinstance(caption, Tag) and caption.get_text(" ", strip=True)):
                # No caption, so this table is not in scope for criterion 5.5
                continue

            tables_with_title.append(table)

            # Extract the caption text
            title_text = caption.get_text(" ", strip=True)

            # Check if the title is pertinent
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

        # Normalize the title text for comparison
        title_normalized = re.sub(r'\s+', ' ', title_text.strip().lower())

        # Check for obviously non-pertinent title text
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

        # Extract table content to check if title relates to it
        # Get table headers to see if title contains relevant terms
        header_texts = self._get_table_header_texts(table)

        # If we have header text, check if title contains at least some relevant terms
        if header_texts:
            # Extract words from title and headers
            title_words = set(re.findall(r'\b\w+\b', title_normalized))
            header_words = set(re.findall(r'\b\w+\b', ' '.join(header_texts).lower()))

            # Remove common French stop words that aren't meaningful for relevance checking
            stop_words = {
                'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'avec',
                'sur', 'dans', 'par', 'pour', 'vers', 'aux', 'ce', 'cet', 'cette',
                'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
                'tableau', 'table', 'données', 'data', 'information', 'info', 'titre', 'title', 'nom'
            }

            meaningful_title_words = title_words - stop_words
            meaningful_header_words = header_words - stop_words

            # If there are meaningful words in both, check for overlap
            if meaningful_title_words and meaningful_header_words:
                # At least one meaningful word should overlap
                if meaningful_title_words & meaningful_header_words:
                    return True

            # If no overlap but title has meaningful content, it might still be pertinent
            # (e.g., it describes the purpose rather than just repeating headers)
            if meaningful_title_words:
                # Allow titles that are descriptive even if they don't repeat header words exactly
                # Basic check: reasonable length and some meaningful content
                if len(title_normalized) > 10 and len(meaningful_title_words) > 0:
                    return True

        # If we can't determine relevance from headers, check if title is descriptively meaningful
        # This is a fallback - a good title should be reasonably descriptive
        if len(title_normalized) >= 15 and len(title_normalized.split()) >= 3:
            return True

        return False

    def _get_table_header_texts(self, table: Tag) -> list[str]:
        """Extract all header text from a table."""
        header_texts = []

        # Look for header cells in the table
        for element in table.find_all(['th', 'td']):
            # Check if it's a header cell
            if (element.name == 'th' or
                element.get('role') in ['columnheader', 'rowheader'] or
                element.get('scope') in ['col', 'row', 'colgroup', 'rowgroup']):
                text = element.get_text(" ", strip=True)
                if text:
                    header_texts.append(text)

        return header_texts
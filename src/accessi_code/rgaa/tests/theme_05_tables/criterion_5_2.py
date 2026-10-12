from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.page import (
    is_html5_doctype,
)
from accessi_code.analysis.tables import (
    find_tables,
    get_table_summary_evidence,
    get_referenced_text,
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


class Test521(RGAATest):
    test_id = "5.2.1"
    criterion_id = "5.2"

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
            raise ValueError("Le test 5.2.1 nécessite un DOM.")

        soup = context.dom

        tables = find_tables(soup)

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        complex_tables_with_summary: list[Tag] = []
        findings: list[Finding] = []

        legacy_summary_allowed = not is_html5_doctype(context.doctype)

        for index, table in enumerate(tables):
            if not has_complex_header_structure(table):
                continue

            # Check if this complex table has a summary (as per criterion 5.1)
            evidence = get_table_summary_evidence(
                table,
                soup,
                allow_legacy_summary=(legacy_summary_allowed),
            )

            if not evidence:
                # This table doesn't have a summary, so it's not in scope for criterion 5.2
                continue

            complex_tables_with_summary.append(table)

            # Extract the actual summary text to check its pertinence
            summary_text = self._extract_summary_text(table, soup)

            # Check if the summary is pertinent/relevant to the table content
            if not self._is_summary_pertinent(summary_text, table, soup):
                table_id = table.get("id")
                element = (
                    f"table#{table_id}" if (isinstance(table_id, str) and table_id.strip()) else f"table[index={index}]"
                )

                findings.append(
                    Finding(
                        element=element,
                        message=("Le résumé du tableau de données complexe n'est pas pertinent."),
                        recommendation=("Fournir un résumé qui décrit précisément la structure ou le contenu du tableau."),
                    )
                )

        if not complex_tables_with_summary:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données complexe avec résumé détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(complex_tables_with_summary)} tableau(x) complexe(s) avec résumé, {len(findings)} avec résumé non pertinent."),
            findings=findings,
            tested_elements=len(complex_tables_with_summary),
            metadata={
                "total_tables": len(tables),
                "complex_tables_with_summary": len(complex_tables_with_summary),
                "complexity_detection": ("structural"),
            },
        )

    def _extract_summary_text(self, table: Tag, soup: BeautifulSoup) -> str:
        """Extract the actual summary text from a table using the same mechanisms as criterion 5.1."""
        # Try caption first
        caption = table.find("caption", recursive=False)
        if isinstance(caption, Tag) and caption.get_text(" ", strip=True):
            return caption.get_text(" ", strip=True)

        # Try aria-describedby
        is_valid, referenced_text = get_referenced_text(table, soup, "aria-describedby")
        if is_valid:
            return referenced_text

        # Try summary attribute (only for legacy doctype)
        summary = table.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        return ""

    def _is_summary_pertinent(self, summary_text: str, table: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if a summary is pertinent/relevant to the table's content.

        A summary is considered pertinent if it:
        1. Is not empty or just whitespace
        2. Contains meaningful information about the table's purpose or content
        3. Is not just generic placeholder text
        """
        if not summary_text or not summary_text.strip():
            return False

        # Normalize the summary text for comparison
        summary_normalized = re.sub(r'\s+', ' ', summary_text.strip().lower())

        # Check for obviously non-pertinent summary text
        non_pertinent_patterns = [
            r'^\s*tableau\s*$',
            r'^\s*données\s*$',
            r'^\s*info\s*$',
            r'^\s*table\s*$',
            r'^\s*data\s*$',
            r'^\s*\d+\s*$',  # Just numbers
            r'^\s*[^a-zA-Z]*\s*$',  # No letters at all
        ]

        for pattern in non_pertinent_patterns:
            if re.match(pattern, summary_normalized):
                return False

        # Extract table headers to check if summary relates to them
        header_texts = self._get_table_header_texts(table)

        # If we have header text, check if summary contains at least some relevant terms
        if header_texts:
            # Extract words from summary and headers
            summary_words = set(re.findall(r'\b\w+\b', summary_normalized))
            header_words = set(re.findall(r'\b\w+\b', ' '.join(header_texts).lower()))

            # Remove common French stop words that aren't meaningful for relevance checking
            stop_words = {
                'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'avec',
                'sur', 'dans', 'par', 'pour', 'vers', 'aux', 'aux', 'ce', 'cet', 'cette',
                'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
                'tableau', 'table', 'données', 'data', 'information', 'info'
            }

            meaningful_summary_words = summary_words - stop_words
            meaningful_header_words = header_words - stop_words

            # If there are meaningful words in both, check for overlap
            if meaningful_summary_words and meaningful_header_words:
                # At least one meaningful word should overlap
                if meaningful_summary_words & meaningful_header_words:
                    return True

            # If no overlap but summary has meaningful content, it might still be pertinent
            # (e.g., it describes the purpose rather than just repeating headers)
            if meaningful_summary_words:
                # Allow summaries that are descriptive even if they don't repeat header words exactly
                # This is a basic check - in practice, we might want more sophisticated NLP
                return len(summary_normalized) > 10  # Reasonable length threshold

        # If we can't determine relevance from headers, check if summary is descriptively meaningful
        # This is a fallback - a good summary should be reasonably descriptive
        if len(summary_normalized) >= 15 and len(summary_normalized.split()) >= 3:
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
from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.page import (
    is_html5_doctype,
)
from accessi_code.analysis.tables import (
    find_tables,
    get_table_summary_evidence,
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


class Test511(RGAATest):
    test_id = "5.1.1"
    criterion_id = "5.1"

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
            raise ValueError("Le test 5.1.1 nécessite un DOM.")

        soup = context.dom

        tables = find_tables(soup)

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        complex_tables: list[Tag] = []
        findings: list[Finding] = []

        legacy_summary_allowed = not is_html5_doctype(context.doctype)

        for index, table in enumerate(tables):
            if not has_complex_header_structure(table):
                continue

            complex_tables.append(table)

            evidence = get_table_summary_evidence(
                table,
                soup,
                allow_legacy_summary=(legacy_summary_allowed),
            )

            if evidence:
                continue

            table_id = table.get("id")

            element = (
                f"table#{table_id}" if (isinstance(table_id, str) and table_id.strip()) else f"table[index={index}]"
            )

            findings.append(
                Finding(
                    element=element,
                    message=("Aucun résumé disponible pour ce tableau de données complexe."),
                    recommendation=("Fournir un passage de texte décrivant la nature et la structure du tableau."),
                )
            )

        if not complex_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données complexe détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(complex_tables)} tableau(x) complexe(s), {len(findings)} sans résumé."),
            findings=findings,
            tested_elements=len(complex_tables),
            metadata={
                "total_tables": len(tables),
                "complex_tables": len(complex_tables),
                "complexity_detection": ("structural"),
            },
        )

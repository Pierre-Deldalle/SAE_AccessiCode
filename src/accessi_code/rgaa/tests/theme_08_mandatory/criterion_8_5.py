from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.page import (
    has_page_title_element,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test851(RGAATest):
    test_id = "8.5.1"
    criterion_id = "8.5"

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
            raise ValueError("Le test 8.5.1 nécessite un DOM.")

        if has_page_title_element(context.dom):
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Une balise title est présente.",
                tested_elements=1,
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            "La page ne possède pas de balise title.",
            findings=[
                Finding(
                    element="head",
                    message="Balise title absente.",
                    recommendation=("Ajouter une balise title à la page."),
                )
            ],
            tested_elements=1,
        )

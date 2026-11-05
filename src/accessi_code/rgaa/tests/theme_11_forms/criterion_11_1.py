from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_labeling_evidence,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test1111(RGAATest):
    test_id = "11.1.1"
    criterion_id = "11.1"

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
            raise ValueError("Le test 11.1.1 nécessite un DOM.")

        soup = context.dom

        fields = find_form_fields(soup)

        if not fields:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun champ de formulaire détecté.",
            )

        findings: list[Finding] = []
        labelled = 0

        for index, field in enumerate(fields):
            evidence = get_labeling_evidence(
                field,
                soup,
                include_wrapping_label=False,
            )

            if evidence:
                labelled += 1
                continue

            findings.append(
                Finding(
                    element=get_element_identifier(
                        field,
                        index,
                    ),
                    message=("Aucun mécanisme d'étiquetage autorisé par le test 11.1.1 n'a été détecté."),
                    recommendation=("Utiliser aria-labelledby, aria-label, un label associé via for/id ou title."),
                    evidence={
                        "tag": field.name,
                        "attributes": dict(field.attrs),
                    },
                )
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{labelled} champ(s) avec étiquette, {len(findings)} sans étiquette."),
            findings=findings,
            tested_elements=len(fields),
            metadata={
                "labelled_fields": labelled,
                "unlabelled_fields": len(findings),
                "mechanisms": [
                    "aria-labelledby",
                    "aria-label",
                    "label-for",
                    "title",
                ],
            },
        )

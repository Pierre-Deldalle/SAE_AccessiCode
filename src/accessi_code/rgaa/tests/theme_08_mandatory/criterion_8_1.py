from __future__ import annotations

from accessi_code.analysis.page import (
    get_document_doctype,
    is_doctype_before_html,
    validate_document_doctype,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test811(RGAATest):
    test_id = "8.1.1"
    criterion_id = "8.1"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        source = context.html_source

        if source is None:
            raise ValueError("Source HTML indisponible.")

        doctype = get_document_doctype(source)

        if doctype is not None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Une déclaration DOCTYPE est présente.",
                tested_elements=1,
                metadata={
                    "doctype": doctype,
                },
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            "Aucune déclaration DOCTYPE détectée.",
            findings=[
                Finding(
                    element="document",
                    message="DOCTYPE absent.",
                    recommendation=("Ajouter une déclaration de type de document."),
                )
            ],
            tested_elements=1,
        )


class Test812(RGAATest):
    test_id = "8.1.2"
    criterion_id = "8.1"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        source = context.html_source

        if source is None:
            raise ValueError("Source HTML indisponible.")

        doctype = get_document_doctype(source)

        if doctype is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                "Aucun DOCTYPE valide ne peut être vérifié car il est absent.",
                tested_elements=1,
            )

        validation = validate_document_doctype(doctype)

        if validation is True:
            status = TestStatus.PASS
            summary = "Le DOCTYPE est reconnu comme valide."

        elif validation is False:
            status = TestStatus.FAIL
            summary = "Le DOCTYPE détecté est invalide."

        else:
            status = TestStatus.NEEDS_REVIEW
            summary = "Le DOCTYPE utilise une déclaration historique non reconnue automatiquement."

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            summary,
            tested_elements=1,
            metadata={
                "doctype": doctype,
            },
        )


class Test813(RGAATest):
    test_id = "8.1.3"
    criterion_id = "8.1"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        source = context.html_source

        if source is None:
            raise ValueError("Source HTML indisponible.")

        doctype = get_document_doctype(source)

        if doctype is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                ("Aucun DOCTYPE n'est présent ; sa position n'est donc pas vérifiable."),
            )

        position = is_doctype_before_html(source)

        if position is True:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Le DOCTYPE est situé avant l'élément html.",
                tested_elements=1,
            )

        if position is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                "L'élément html n'a pas été retrouvé dans le source.",
                tested_elements=1,
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            "Le DOCTYPE n'est pas situé avant l'élément html.",
            findings=[
                Finding(
                    element="document",
                    message="DOCTYPE mal positionné.",
                    recommendation=("Placer le DOCTYPE avant l'élément html."),
                )
            ],
            tested_elements=1,
        )

"""
RGAA 4.1.2 — critère 8.2 : pour chaque page web, le code source généré est-il
valide selon le type de document spécifié ?

Test 8.2.1, contrôle déterministe sans IA (``analysis/html_validation.py``) :
règles d'écriture, imbrication, ouverture et fermeture des balises, id
uniques, attributs non doublés. Une erreur → FAIL ; aucune → PASS.
Les éléments obsolètes ne sont signalés que pour un DOCTYPE HTML5.
"""

from __future__ import annotations

from typing import Any

from accessi_code.analysis.html_validation import validate_html
from accessi_code.analysis.page import get_document_doctype, is_html5_doctype
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

MAX_FINDINGS = 50
RECOMMENDATION = "Corriger le code source, puis le contrôler avec le validateur du W3C (validator.w3.org)."


class Test821(RGAATest):
    """8.2.1 : code source valide selon le type de document."""

    test_id = "8.2.1"
    criterion_id = "8.2"
    required_capabilities = frozenset({Capability.HTML_SOURCE})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        source = context.html_source
        if source is None:
            raise ValueError("Le test 8.2.1 nécessite la source HTML.")

        doctype = get_document_doctype(source)
        html5 = doctype is None or is_html5_doctype(doctype)
        errors = validate_html(source, html5=html5)

        counts: dict[str, int] = {}
        for error in errors:
            counts[error.condition] = counts.get(error.condition, 0) + 1

        if not errors:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Aucune erreur d'écriture, d'imbrication, de fermeture, d'id dupliqué ni d'attribut doublé.",
                tested_elements=1,
                metadata={"errors": 0},
            )

        findings = [
            Finding(
                element=f"ligne {error.line}, colonne {error.column}",
                message=error.message,
                recommendation=RECOMMENDATION,
                evidence={"condition": error.condition, "line": error.line, "column": error.column},
            )
            for error in errors[:MAX_FINDINGS]
        ]
        detail = ", ".join(f"{count} {condition}" for condition, count in sorted(counts.items()))
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            f"Le code source contient {len(errors)} erreur(s) ({detail}).",
            findings=findings,
            tested_elements=1,
            metadata={"errors": len(errors), "by_condition": counts, "html5": html5},
        )

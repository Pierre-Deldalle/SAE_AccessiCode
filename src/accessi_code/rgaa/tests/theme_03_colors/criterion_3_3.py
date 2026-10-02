from __future__ import annotations

from typing import Any

from accessi_code.analysis.colors import contrast_ratio
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.color_style import NonTextContrastSample
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


def _evaluate_non_text_samples(
    test: RGAATest,
    samples: list[NonTextContrastSample],
    *,
    kind: str,
    comparison: str,
) -> TestResult:
    """
    Évalue le contraste des composants ou éléments graphiques.
    """
    applicable = [
        sample for sample in samples if sample.kind == kind and sample.comparison == comparison and not sample.exempt
    ]

    if not applicable:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NOT_APPLICABLE,
            "Aucun élément concerné par ce test n'a été détecté.",
            tested_elements=0,
        )

    findings: list[Finding] = []
    failures = 0
    unknown = 0

    for sample in applicable:
        ratio = contrast_ratio(
            sample.foreground_color,
            sample.background_color,
        )

        if ratio is None:
            unknown += 1

            findings.append(
                Finding(
                    element=sample.element,
                    message=("Le rapport de contraste n'a pas pu être calculé."),
                    recommendation=("Vérifier manuellement le contraste de cet élément."),
                    evidence={
                        "foreground_color": (sample.foreground_color),
                        "background_color": (sample.background_color),
                        "state": sample.state,
                    },
                )
            )

            continue

        if ratio < 3:
            failures += 1

            findings.append(
                Finding(
                    element=sample.element,
                    message=(f"Le rapport de contraste est {ratio:.2f}:1 au lieu des 3:1 requis."),
                    recommendation=("Modifier les couleurs afin d'obtenir un rapport de contraste d'au moins 3:1."),
                    evidence={
                        "ratio": ratio,
                        "required_ratio": 3.0,
                        "foreground_color": (sample.foreground_color),
                        "background_color": (sample.background_color),
                        "state": sample.state,
                    },
                )
            )

    metadata = {
        "required_ratio": 3.0,
        "applicable_elements": len(applicable),
        "failed_elements": failures,
        "unknown_contrast": unknown,
    }

    if failures:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.FAIL,
            (f"{failures} élément(s) présentent un contraste insuffisant."),
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    if unknown:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NEEDS_REVIEW,
            ("Le contraste de certains éléments n'a pas pu être déterminé."),
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    return TestResult(
        test.test_id,
        test.criterion_id,
        TestStatus.PASS,
        ("Les éléments contrôlés présentent un contraste d'au moins 3:1."),
        tested_elements=len(applicable),
        metadata=metadata,
    )


class Test331(RGAATest):
    test_id = "3.3.1"
    criterion_id = "3.3"

    required_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _evaluate_non_text_samples(
            self,
            context.non_text_contrast_samples,
            kind="component",
            comparison="background",
        )


class Test332(RGAATest):
    test_id = "3.3.2"
    criterion_id = "3.3"

    required_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _evaluate_non_text_samples(
            self,
            context.non_text_contrast_samples,
            kind="graphic",
            comparison="background",
        )


class Test333(RGAATest):
    test_id = "3.3.3"
    criterion_id = "3.3"

    required_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _evaluate_non_text_samples(
            self,
            context.non_text_contrast_samples,
            kind="graphic",
            comparison="adjacent",
        )


class Test334(RGAATest):
    test_id = "3.3.4"
    criterion_id = "3.3"

    required_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _evaluate_non_text_samples(
            self,
            context.non_text_contrast_samples,
            kind="mechanism",
            comparison="background",
        )

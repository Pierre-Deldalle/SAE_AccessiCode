from __future__ import annotations

from typing import Any, Callable

from accessi_code.analysis.colors import (
    contrast_ratio,
    is_bold,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.color_style import TextContrastSample
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


def _evaluate_samples(
    test: RGAATest,
    samples: list[TextContrastSample],
    *,
    threshold: float,
    selector: Callable[[TextContrastSample], bool],
    summary_pass: str,
) -> TestResult:
    """
    Évalue un ensemble de textes pour un seuil de contraste donné.
    """
    applicable = [sample for sample in samples if not sample.exempt and selector(sample)]

    if not applicable:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NOT_APPLICABLE,
            "Aucun texte concerné par ce test n'a été détecté.",
            tested_elements=0,
        )

    findings: list[Finding] = []
    failures = 0
    unknown = 0

    for sample in applicable:
        ratio = contrast_ratio(
            sample.color,
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
                        "color": sample.color,
                        "background_color": (sample.background_color),
                    },
                )
            )

            continue

        if ratio < threshold:
            failures += 1

            findings.append(
                Finding(
                    element=sample.element,
                    message=(f"Le rapport de contraste est {ratio:.2f}:1 alors que {threshold}:1 est requis."),
                    recommendation=(
                        "Modifier les couleurs du texte ou de son arrière-plan afin d'obtenir un contraste suffisant."
                    ),
                    evidence={
                        "ratio": ratio,
                        "required_ratio": threshold,
                        "color": sample.color,
                        "background_color": (sample.background_color),
                    },
                )
            )

    metadata = {
        "required_ratio": threshold,
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
        summary_pass,
        tested_elements=len(applicable),
        metadata=metadata,
    )


class Test321(RGAATest):
    test_id = "3.2.1"
    criterion_id = "3.2"

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
        return _evaluate_samples(
            self,
            context.text_contrast_samples,
            threshold=4.5,
            selector=lambda sample: (
                not is_bold(sample.font_weight) and sample.font_size_px < 24 and not sample.is_contrast_mechanism
            ),
            summary_pass=("Les textes non gras de moins de 24px présentent un contraste suffisant."),
        )


class Test322(RGAATest):
    test_id = "3.2.2"
    criterion_id = "3.2"

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
        return _evaluate_samples(
            self,
            context.text_contrast_samples,
            threshold=4.5,
            selector=lambda sample: (
                is_bold(sample.font_weight) and sample.font_size_px < 18.5 and not sample.is_contrast_mechanism
            ),
            summary_pass=("Les textes gras de moins de 18,5px présentent un contraste suffisant."),
        )


class Test323(RGAATest):
    test_id = "3.2.3"
    criterion_id = "3.2"

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
        return _evaluate_samples(
            self,
            context.text_contrast_samples,
            threshold=3.0,
            selector=lambda sample: (
                not is_bold(sample.font_weight) and sample.font_size_px >= 24 and not sample.is_contrast_mechanism
            ),
            summary_pass=("Les grands textes non gras présentent un contraste suffisant."),
        )


class Test324(RGAATest):
    test_id = "3.2.4"
    criterion_id = "3.2"

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
        return _evaluate_samples(
            self,
            context.text_contrast_samples,
            threshold=3.0,
            selector=lambda sample: (
                is_bold(sample.font_weight) and sample.font_size_px >= 18.5 and not sample.is_contrast_mechanism
            ),
            summary_pass=("Les grands textes gras présentent un contraste suffisant."),
        )


class Test325(RGAATest):
    test_id = "3.2.5"
    criterion_id = "3.2"

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
        mechanisms = [
            sample for sample in context.text_contrast_samples if sample.is_contrast_mechanism and not sample.exempt
        ]

        if not mechanisms:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                ("Aucun mécanisme permettant d'afficher un contraste conforme n'a été détecté."),
                tested_elements=0,
            )

        findings: list[Finding] = []
        failures = 0
        unknown = 0

        for sample in mechanisms:
            large_text = (is_bold(sample.font_weight) and sample.font_size_px >= 18.5) or (
                not is_bold(sample.font_weight) and sample.font_size_px >= 24
            )

            threshold = 3.0 if large_text else 4.5

            ratio = contrast_ratio(
                sample.color,
                sample.background_color,
            )

            if ratio is None:
                unknown += 1

                findings.append(
                    Finding(
                        element=sample.element,
                        message=("Le contraste du mécanisme n'a pas pu être calculé."),
                        recommendation=("Vérifier manuellement le contraste du mécanisme."),
                        evidence={
                            "color": sample.color,
                            "background_color": (sample.background_color),
                        },
                    )
                )

                continue

            if ratio < threshold:
                failures += 1

                findings.append(
                    Finding(
                        element=sample.element,
                        message=("Le mécanisme de contraste ne présente pas un contraste suffisant."),
                        recommendation=("Corriger les couleurs utilisées par le mécanisme."),
                        evidence={
                            "ratio": ratio,
                            "required_ratio": threshold,
                        },
                    )
                )

        metadata = {
            "mechanisms": len(mechanisms),
            "failed_elements": failures,
            "unknown_contrast": unknown,
        }

        if failures:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                ("Au moins un mécanisme de contraste n'est pas conforme."),
                findings=findings,
                tested_elements=len(mechanisms),
                metadata=metadata,
            )

        if unknown:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                ("Le contraste de certains mécanismes doit être vérifié manuellement."),
                findings=findings,
                tested_elements=len(mechanisms),
                metadata=metadata,
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.PASS,
            ("Les mécanismes de contraste détectés sont suffisamment contrastés."),
            tested_elements=len(mechanisms),
            metadata=metadata,
        )

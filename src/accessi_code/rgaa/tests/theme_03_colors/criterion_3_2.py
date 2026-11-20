"""Tests RGAA 3.2 : contrastes des textes et textes en image."""

from __future__ import annotations

from typing import Any, Callable

from accessi_code.analysis.colors import contrast_ratio, is_bold
from accessi_code.models.audit_context import (
    AuditContext,
    UnresolvedTextContrast,
)
from accessi_code.models.capabilities import Capability
from accessi_code.models.color_style import TextContrastSample
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


def _is_partial_automatic_context(context: AuditContext) -> bool:
    """
    Détermine si la couverture automatique est partielle.

    Les contextes construits manuellement sans tentative
    d'extraction conservent leur comportement historique.

    La présence d'observations non résolues constitue
    également une raison de ne pas conclure à une
    conformité entièrement démontrée.
    """
    return context.text_contrast_is_partial or bool(context.unresolved_text_contrasts)


def _coverage_metadata(context: AuditContext) -> dict[str, Any]:
    """Décrit la couverture connue des contrastes textuels."""
    return {
        "text_contrast_extraction_attempted": (context.text_contrast_extraction_attempted),
        "text_contrast_coverage_complete": (context.text_contrast_coverage_complete),
        "text_contrast_unresolved_count": (context.text_contrast_unresolved_count),
    }


def _unresolved_test_id(
    observation: UnresolvedTextContrast,
) -> str | None:
    """
    Oriente une observation vers un sous-test typographique.

    Les règles sont identiques à celles appliquées aux
    échantillons de contraste mesurables.

    None signifie que la typographie n'est pas assez
    fiable pour déterminer le sous-test applicable.

    Cette classification ne démontre ni la présence
    d'un défaut de contraste ni la conformité du texte.
    """
    if not observation.has_valid_typography:
        return None

    font_size = observation.font_size_px
    font_weight = observation.font_weight

    if font_size is None or font_weight is None:
        return None

    bold = is_bold(font_weight)

    if bold:
        if font_size < 18.5:
            return "3.2.2"
        return "3.2.4"

    if font_size < 24:
        return "3.2.1"

    return "3.2.3"


def _unresolved_for_test(
    context: AuditContext,
    test_id: str,
) -> list[UnresolvedTextContrast]:
    """Retourne uniquement les observations associées à un test."""
    return [
        observation for observation in context.unresolved_text_contrasts if _unresolved_test_id(observation) == test_id
    ]


def _unclassified_observations(
    context: AuditContext,
) -> list[UnresolvedTextContrast]:
    """Retourne les observations impossibles à classer."""
    return [
        observation for observation in context.unresolved_text_contrasts if _unresolved_test_id(observation) is None
    ]


def _unresolved_finding(
    observation: UnresolvedTextContrast,
    *,
    unclassified: bool = False,
) -> Finding:
    """
    Construit un constat nécessitant une vérification humaine.

    Aucun rapport de contraste n'est inventé.

    Une observation non classée est explicitement désignée
    comme observation générale du critère 3.2.
    """
    if unclassified:
        message = (
            "Observation générale RGAA 3.2 non classée : "
            "le contraste de ce texte reste indéterminé "
            "et sa typographie ne permet pas de sélectionner "
            "un sous-test fiable."
        )
    else:
        message = f"Le contraste de ce texte n'a pas pu être déterminé automatiquement. Motif : {observation.reason}"

    recommendation = (
        "Vérifier manuellement le contraste du texte dans "
        "son rendu réel, notamment les arrière-plans, "
        "les pseudo-éléments et les éventuelles superpositions."
    )

    if unclassified:
        recommendation += " Vérifier également sa taille et sa graisse avant de déterminer le seuil applicable."

    return Finding(
        element=observation.element,
        message=message,
        recommendation=recommendation,
        evidence={
            "text": observation.text,
            "reason": observation.reason,
            "font_size_px": observation.font_size_px,
            "font_weight": observation.font_weight,
            "typography_valid": observation.has_valid_typography,
            "classification": ("unclassified" if unclassified else "typography"),
            "contrast_ratio": None,
            "requires_manual_review": True,
        },
    )


def _review_findings(
    context: AuditContext,
    test_id: str,
) -> tuple[list[Finding], int, int]:
    """
    Prépare les observations incertaines d'un sous-test.

    Les observations classables apparaissent uniquement
    dans leur sous-test respectif.

    Convention d'affichage :
        Les observations sans typographie fiable sont
        rassemblées dans le résultat 3.2.1 comme
        observations générales du critère 3.2.

    Elles ne sont jamais comptées comme échantillons
    applicables ou comme défauts confirmés.
    """
    assigned = _unresolved_for_test(context, test_id)

    findings = [_unresolved_finding(observation) for observation in assigned]

    unclassified_count = 0

    if test_id == "3.2.1":
        unclassified = _unclassified_observations(context)
        unclassified_count = len(unclassified)

        findings.extend(
            _unresolved_finding(
                observation,
                unclassified=True,
            )
            for observation in unclassified
        )

    return findings, len(assigned), unclassified_count


def _evaluate_samples(
    test: RGAATest,
    samples: list[TextContrastSample],
    *,
    threshold: float,
    selector: Callable[[TextContrastSample], bool],
    summary_pass: str,
    context: AuditContext,
) -> TestResult:
    """
    Évalue les contrastes mesurables d'un sous-test.

    Priorité des verdicts :
        FAIL si au moins un contraste mesuré est insuffisant.
        NEEDS_REVIEW si un contraste reste indéterminé
        ou si la couverture est partielle.
        PASS seulement lorsque les données le permettent.

    Les observations rejetées sont affichées séparément
    et ne sont pas comptées parmi les éléments mesurés.
    """
    applicable = [sample for sample in samples if not sample.exempt and selector(sample)]

    partial = _is_partial_automatic_context(context)

    review_findings, assigned_count, unclassified_count = _review_findings(context, test.test_id)

    findings: list[Finding] = list(review_findings)
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
                        "background_color": sample.background_color,
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
                        "background_color": sample.background_color,
                    },
                )
            )

    metadata: dict[str, Any] = {
        "required_ratio": threshold,
        "applicable_elements": len(applicable),
        "failed_elements": failures,
        "unknown_contrast": unknown,
        "unresolved_assigned_to_test": assigned_count,
        "unresolved_unclassified_displayed": unclassified_count,
    }

    if partial:
        metadata.update(_coverage_metadata(context))

    # Une mesure fiable insuffisante reste prioritaire
    # sur toutes les observations incertaines.
    if failures:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.FAIL,
            f"{failures} élément(s) présentent un contraste insuffisant.",
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    # Des observations réellement mesurées peuvent
    # elles-mêmes produire un contraste inconnu.
    if unknown:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NEEDS_REVIEW,
            "Le contraste de certains éléments n'a pas pu être déterminé.",
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    # Aucune mesure applicable ne signifie pas
    # automatiquement que le test est non applicable.
    if not applicable:
        if partial or findings:
            return TestResult(
                test.test_id,
                test.criterion_id,
                TestStatus.NEEDS_REVIEW,
                (
                    "Aucun échantillon applicable n'a été "
                    "identifié, mais une vérification "
                    "supplémentaire reste nécessaire."
                ),
                findings=findings,
                tested_elements=0,
                metadata=metadata,
            )

        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NOT_APPLICABLE,
            "Aucun texte concerné par ce test n'a été détecté.",
            tested_elements=0,
        )

    # Des observations incertaines ou une couverture
    # partielle empêchent de conclure à PASS.
    if partial or findings:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (
                "Les échantillons analysés présentent un "
                "contraste suffisant, mais des vérifications "
                "restent nécessaires ou la couverture de "
                "l'extraction automatique est partielle."
            ),
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
    """Test 3.2.1 : contraste des textes non gras de moins de 24 px."""

    test_id = "3.2.1"
    criterion_id = "3.2"

    required_capabilities = frozenset({Capability.TEXT_CONTRAST})

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
            context=context,
        )


class Test322(RGAATest):
    """Test 3.2.2 : contraste des textes gras de moins de 18,5 px."""

    test_id = "3.2.2"
    criterion_id = "3.2"

    required_capabilities = frozenset({Capability.TEXT_CONTRAST})

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
            context=context,
        )


class Test323(RGAATest):
    """Test 3.2.3 : contraste des textes non gras d'au moins 24 px."""

    test_id = "3.2.3"
    criterion_id = "3.2"

    required_capabilities = frozenset({Capability.TEXT_CONTRAST})

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
            context=context,
        )


class Test324(RGAATest):
    """Test 3.2.4 : contraste des textes gras d'au moins 18,5 px."""

    test_id = "3.2.4"
    criterion_id = "3.2"

    required_capabilities = frozenset({Capability.TEXT_CONTRAST})

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
            context=context,
        )


class Test325(RGAATest):
    """Test 3.2.5 : contraste d'un mécanisme explicitement identifié."""

    test_id = "3.2.5"
    criterion_id = "3.2"

    required_capabilities = frozenset({Capability.TEXT_CONTRAST})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        mechanisms = [
            sample for sample in context.text_contrast_samples if sample.is_contrast_mechanism and not sample.exempt
        ]

        partial = _is_partial_automatic_context(context)

        if not mechanisms:
            if partial:
                return TestResult(
                    self.test_id,
                    self.criterion_id,
                    TestStatus.NEEDS_REVIEW,
                    (
                        "Aucun mécanisme de contraste n'a été "
                        "identifié dans les échantillons. "
                        "L'extraction étant partielle, sa "
                        "présence ou son absence doit être vérifiée."
                    ),
                    tested_elements=0,
                    metadata={
                        "mechanisms": 0,
                        **_coverage_metadata(context),
                    },
                )

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
                            "background_color": sample.background_color,
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

        metadata: dict[str, Any] = {
            "mechanisms": len(mechanisms),
            "failed_elements": failures,
            "unknown_contrast": unknown,
        }

        if partial:
            metadata.update(_coverage_metadata(context))

        if failures:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                "Au moins un mécanisme de contraste n'est pas conforme.",
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

        if partial:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                (
                    "Les mécanismes identifiés présentent un "
                    "contraste suffisant, mais l'extraction "
                    "automatique ne couvre pas nécessairement "
                    "tous les mécanismes."
                ),
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

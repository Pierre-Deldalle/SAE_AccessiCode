"""Tests RGAA 3.3 : contrastes des composants et éléments graphiques."""

from __future__ import annotations

from typing import Any

from accessi_code.analysis.colors import contrast_ratio
from accessi_code.models.audit_context import (
    AuditContext,
    UnresolvedNonTextContrast,
)
from accessi_code.models.capabilities import Capability
from accessi_code.models.color_style import NonTextContrastSample
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

CONTRAST_THRESHOLD = 3.0


def _has_partial_non_text_coverage(context: AuditContext) -> bool:
    """
    Signale une incertitude connue sur les contrastes non textuels.

    Pour cette première intégration, la présence d'observations
    non résolues indique que l'analyse ne permet pas de
    conclure à une couverture complète.

    Cette fonction ne prétend pas détecter tous les autres
    cas de couverture partielle.
    """
    return bool(context.unresolved_non_text_contrasts)


def _unresolved_for_test(
    context: AuditContext,
    *,
    kind: str,
    comparison: str,
) -> list[UnresolvedNonTextContrast]:
    """
    Retourne les observations incertaines de la catégorie demandée.

    Chaque observation est associée à une seule combinaison
    kind/comparison et ne doit pas apparaître plusieurs fois.
    """
    return [
        observation
        for observation in context.unresolved_non_text_contrasts
        if observation.kind == kind and observation.comparison == comparison
    ]


def _unresolved_finding(
    observation: UnresolvedNonTextContrast,
) -> Finding:
    """
    Transforme une observation incertaine en demande de vérification.

    Un rapport candidat peut être calculé lorsque les deux
    couleurs CSS sont disponibles.

    Ce rapport ne constitue PAS une mesure RGAA validée.
    Il ne doit donc déclencher ni FAIL ni PASS.
    """
    candidate_ratio: float | None = None

    if observation.foreground_color is not None and observation.background_color is not None:
        candidate_ratio = contrast_ratio(
            observation.foreground_color,
            observation.background_color,
        )

    if candidate_ratio is None:
        message = f"Le contraste non textuel de cet élément reste indéterminé. Motif : {observation.reason}"
    else:
        message = (
            "Comparaison CSS candidate : "
            f"{candidate_ratio:.2f}:1. "
            "Ce rapport ne constitue pas un verdict RGAA. "
            f"Motif : {observation.reason}"
        )

    return Finding(
        element=observation.element,
        message=message,
        recommendation=(
            "Vérifier dans le rendu réel que les couleurs "
            "comparées correspondent bien aux surfaces adjacentes "
            "et que l'information visuelle concernée relève "
            "du critère RGAA 3.3. Contrôler également les "
            "états interactifs pertinents."
        ),
        evidence={
            "kind": observation.kind,
            "comparison": observation.comparison,
            "foreground_color": observation.foreground_color,
            "background_color": observation.background_color,
            "state": observation.state,
            "reason": observation.reason,
            "candidate_ratio": candidate_ratio,
            "required_ratio": CONTRAST_THRESHOLD,
            "requires_manual_review": True,
            "measurement_validated": False,
        },
    )


def _evaluate_non_text_samples(
    test: RGAATest,
    samples: list[NonTextContrastSample],
    *,
    kind: str,
    comparison: str,
    context: AuditContext,
) -> TestResult:
    """
    Évalue les contrastes non textuels du sous-test.

    Les échantillons exploitables et les observations incertaines
    sont traités séparément.

    Les seuls échantillons exploitables peuvent donner FAIL.

    Une observation incertaine produit un Finding de vérification
    humaine, même si son rapport CSS candidat est inférieur à 3:1.

    La priorité des résultats reste :
    FAIL > NEEDS_REVIEW > PASS / NOT_APPLICABLE.
    """

    applicable = [
        sample for sample in samples if sample.kind == kind and sample.comparison == comparison and not sample.exempt
    ]

    unresolved = _unresolved_for_test(
        context,
        kind=kind,
        comparison=comparison,
    )

    partial = _has_partial_non_text_coverage(context)

    findings: list[Finding] = [_unresolved_finding(observation) for observation in unresolved]

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
                        "foreground_color": sample.foreground_color,
                        "background_color": sample.background_color,
                        "state": sample.state,
                    },
                )
            )
            continue

        if ratio < CONTRAST_THRESHOLD:
            failures += 1

            findings.append(
                Finding(
                    element=sample.element,
                    message=(f"Le rapport de contraste est {ratio:.2f}:1 alors que {CONTRAST_THRESHOLD}:1 est requis."),
                    recommendation=("Modifier les couleurs afin d'obtenir un rapport de contraste d'au moins 3:1."),
                    evidence={
                        "ratio": ratio,
                        "required_ratio": CONTRAST_THRESHOLD,
                        "foreground_color": sample.foreground_color,
                        "background_color": sample.background_color,
                        "state": sample.state,
                    },
                )
            )

    metadata: dict[str, Any] = {
        "required_ratio": CONTRAST_THRESHOLD,
        "applicable_elements": len(applicable),
        "failed_elements": failures,
        "unknown_contrast": unknown,
        "unresolved_assigned_to_test": len(unresolved),
        "non_text_coverage_partial": partial,
    }

    # Un défaut mesuré et confirmé reste prioritaire.
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

    # Les échantillons dont le calcul échoue nécessitent une revue.
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

    # Les comparaisons CSS incertaines ne peuvent pas donner FAIL.
    if unresolved:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (f"{len(unresolved)} observation(s) non textuelle(s) nécessitent une vérification humaine."),
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    # Dans notre périmètre actuel, une observation incertaine
    # ailleurs dans la page empêche de démontrer que l'extraction
    # couvre exhaustivement les autres catégories.
    if partial:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (
                "Aucun défaut confirmé pour ce sous-test, "
                "mais la couverture automatique des contrastes "
                "non textuels n'est pas démontrée."
            ),
            findings=findings,
            tested_elements=len(applicable),
            metadata=metadata,
        )

    # Conserver le comportement historique pour les contextes
    # manuels, sans observation non résolue.
    if not applicable:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NOT_APPLICABLE,
            "Aucun élément concerné par ce test n'a été détecté.",
            tested_elements=0,
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
    """Test 3.3.1 : contraste des composants avec leur arrière-plan."""

    test_id = "3.3.1"
    criterion_id = "3.3"

    required_capabilities = frozenset({Capability.NON_TEXT_CONTRAST})

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
            context=context,
        )


class Test332(RGAATest):
    """Test 3.3.2 : contraste des éléments graphiques avec leur fond."""

    test_id = "3.3.2"
    criterion_id = "3.3"

    required_capabilities = frozenset({Capability.NON_TEXT_CONTRAST})

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
            context=context,
        )


class Test333(RGAATest):
    """Test 3.3.3 : contraste entre couleurs graphiques adjacentes."""

    test_id = "3.3.3"
    criterion_id = "3.3"

    required_capabilities = frozenset({Capability.NON_TEXT_CONTRAST})

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
            context=context,
        )


class Test334(RGAATest):
    """Test 3.3.4 : contraste d'un mécanisme explicitement identifié."""

    test_id = "3.3.4"
    criterion_id = "3.3"

    required_capabilities = frozenset({Capability.NON_TEXT_CONTRAST})

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
            context=context,
        )

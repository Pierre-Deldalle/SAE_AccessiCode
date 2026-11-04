from __future__ import annotations

from evals.optimization.models import (
    CandidateEvaluation,
    PromptOptimizationResult,
)
from evals.selection.models import (
    PromptSelectionResult,
    RankedPromptCandidate,
)


class PromptSelector:
    def select(
        self,
        result: PromptOptimizationResult,
    ) -> PromptSelectionResult:
        baseline_validation = (
            result.baseline_validation_report
        )

        ranked_data: list[
            tuple[
                CandidateEvaluation,
                bool,
                tuple[str, ...],
            ]
        ] = []

        for evaluation in result.candidates:
            eligible, reasons = (
                self._evaluate_eligibility(
                    evaluation=evaluation,
                    result=result,
                )
            )

            ranked_data.append(
                (
                    evaluation,
                    eligible,
                    reasons,
                )
            )

        #
        # Les candidats admissibles sont toujours
        # classés avant les candidats rejetés.
        #
        ranked_data.sort(
            key=lambda item: (
                not item[1],
                item[0]
                .validation_report
                .critical_errors,
                len(
                    item[0]
                    .validation_comparison
                    .regressions
                ),
                -item[0]
                .validation_comparison
                .accuracy_delta,
                -item[0]
                .validation_comparison
                .score_delta,
                len(
                    item[0]
                    .train_comparison
                    .regressions
                ),
                -item[0]
                .train_comparison
                .score_delta,
                item[0].candidate.name,
            )
        )

        ranking: list[
            RankedPromptCandidate
        ] = []

        for rank, (
            evaluation,
            eligible,
            reasons,
        ) in enumerate(
            ranked_data,
            start=1,
        ):
            ranking.append(
                RankedPromptCandidate(
                    rank=rank,
                    name=(
                        evaluation
                        .candidate
                        .name
                    ),
                    prompt_path=(
                        evaluation.prompt_path
                    ),
                    eligible=eligible,
                    reasons=reasons,
                    validation_accuracy=(
                        evaluation
                        .validation_report
                        .accuracy
                    ),
                    validation_accuracy_delta=(
                        evaluation
                        .validation_comparison
                        .accuracy_delta
                    ),
                    validation_score=(
                        evaluation
                        .validation_report
                        .average_decision_score
                    ),
                    validation_score_delta=(
                        evaluation
                        .validation_comparison
                        .score_delta
                    ),
                    validation_critical_errors=(
                        evaluation
                        .validation_report
                        .critical_errors
                    ),
                    validation_critical_errors_delta=(
                        evaluation
                        .validation_report
                        .critical_errors
                        - baseline_validation
                        .critical_errors
                    ),
                    validation_improvements=len(
                        evaluation
                        .validation_comparison
                        .improvements
                    ),
                    validation_regressions=len(
                        evaluation
                        .validation_comparison
                        .regressions
                    ),
                    train_accuracy=(
                        evaluation
                        .train_report
                        .accuracy
                    ),
                    train_accuracy_delta=(
                        evaluation
                        .train_comparison
                        .accuracy_delta
                    ),
                    train_score=(
                        evaluation
                        .train_report
                        .average_decision_score
                    ),
                    train_score_delta=(
                        evaluation
                        .train_comparison
                        .score_delta
                    ),
                    train_regressions=len(
                        evaluation
                        .train_comparison
                        .regressions
                    ),
                )
            )

        recommended_candidate = next(
            (
                candidate
                for candidate in ranking
                if candidate.eligible
            ),
            None,
        )

        if recommended_candidate is None:
            return PromptSelectionResult(
                recommended_candidate=None,
                keep_production=True,
                ranking=tuple(ranking),
                summary=(
                    "Aucun candidat ne satisfait "
                    "les critères de recommandation. "
                    "Le prompt de production doit "
                    "être conservé."
                ),
            )

        return PromptSelectionResult(
            recommended_candidate=(
                recommended_candidate
            ),
            keep_production=False,
            ranking=tuple(ranking),
            summary=(
                f"{recommended_candidate.name} "
                "est le meilleur candidat "
                "selon les résultats de VALIDATION. "
                "Une validation humaine reste "
                "obligatoire avant toute intégration."
            ),
        )

    @staticmethod
    def _evaluate_eligibility(
        *,
        evaluation: CandidateEvaluation,
        result: PromptOptimizationResult,
    ) -> tuple[
        bool,
        tuple[str, ...],
    ]:
        reasons: list[str] = []

        baseline_validation = (
            result.baseline_validation_report
        )

        validation_report = (
            evaluation.validation_report
        )

        validation_comparison = (
            evaluation.validation_comparison
        )

        #
        # 1. Pas d'erreur technique.
        #
        if validation_report.errors > 0:
            reasons.append(
                "Le candidat produit des erreurs "
                "techniques sur VALIDATION."
            )

        #
        # 2. Interdiction d'augmenter les
        # erreurs critiques.
        #
        if (
            validation_report.critical_errors
            >
            baseline_validation.critical_errors
        ):
            reasons.append(
                "Le candidat augmente le nombre "
                "de critical errors sur VALIDATION."
            )

        #
        # 3. Il doit apporter au moins
        # une amélioration mesurable.
        #
        has_improvement = (
            validation_comparison
            .accuracy_delta
            > 0
            or validation_comparison
            .score_delta
            > 0
            or (
                validation_report
                .critical_errors
                <
                baseline_validation
                .critical_errors
            )
        )

        if not has_improvement:
            reasons.append(
                "Le candidat n'apporte aucune "
                "amélioration mesurable sur VALIDATION."
            )

        return (
            not reasons,
            tuple(reasons),
        )
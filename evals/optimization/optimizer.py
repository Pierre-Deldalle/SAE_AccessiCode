from __future__ import annotations

from evals.comparison.comparator import (
    PromptComparator,
)
from evals.models.case import EvalCase
from evals.models.report import EvalReport
from evals.optimization.context import (
    OptimizationContextBuilder,
)
from evals.optimization.generator import (
    PromptCandidateGenerator,
    PromptGenerationError,
)
from evals.optimization.models import (
    CandidateEvaluation,
    CandidateRejection,
    GeneratedPromptCandidate,
    PromptOptimizationResult,
)
from evals.optimization.storage import (
    PromptCandidateStore,
)
from evals.runners.runner import EvalRunner
from evals.tasks.base import EvalTask


class PromptOptimizer:
    """
    Génère et évalue des candidats sans jamais modifier
    le prompt de production.
    """

    def __init__(
        self,
        *,
        runner: EvalRunner,
        comparator: PromptComparator,
        context_builder: OptimizationContextBuilder,
        generator: PromptCandidateGenerator,
        store: PromptCandidateStore,
    ):
        self.runner = runner
        self.comparator = comparator
        self.context_builder = (
            context_builder
        )
        self.generator = generator
        self.store = store

    async def optimize(
        self,
        *,
        task: EvalTask,
        train_cases: list[EvalCase],
        validation_cases: list[EvalCase],
        candidate_count: int = 3,
    ) -> PromptOptimizationResult:
        production_prompt = (
            task.get_production_prompt_template()
        )

        #
        # 1. Baseline TRAIN
        #
        print("[1/6] Évaluation baseline TRAIN...")
        
        baseline_train_results = (
            await self.runner.run(
                task=task,
                cases=train_cases,
            )
        )

        baseline_train_report = (
            EvalReport.from_results(
                task_name=task.name,
                dataset_name="train",
                results=baseline_train_results,
            )
        )

        #
        # 2. Construire le contexte TRAIN uniquement
        #
        optimization_context = (
            self.context_builder.build(
                task_name=task.name,
                production_prompt=production_prompt,
                cases=train_cases,
                results=baseline_train_results,
                report=baseline_train_report,
            )
        )

        #
        # 3. Gemma génère les candidats
        #
        run_id, output_directory = (
            self.store.create_run_directory(
                task_name=task.name
            )
        )
        
        self.store.save_optimization_context(
            directory=output_directory,
            context=optimization_context,
        )

        print(
            "[2/6] Génération des prompts candidats..."
        )

        try:
            generated_candidates = (
                await self.generator.generate(
                    optimization_context=(
                        optimization_context
                    ),
                    candidate_count=(
                        candidate_count
                    ),
                )
            )

        except PromptGenerationError as error:
            self.store.save_generation_failure(
                directory=output_directory,
                raw_response=error.raw_response,
                parsed_data=error.parsed_data,
                rejection_reasons=(
                    error.rejection_reasons
                ),
            )

            raise RuntimeError(
                "La génération des prompts candidats "
                "a échoué.\n"
                f"{error}\n\n"
                "La réponse brute de l'optimiseur "
                "a été conservée dans : "
                f"{output_directory}"
            ) from error

        self.store.save_raw_candidates(
            directory=output_directory,
            candidates=generated_candidates,
        )

        #
        # 4. Validation syntaxique des candidats
        #
        print("[3/6] Validation des prompts candidats...")
        
        candidates, rejections = (
            self._validate_candidates(
                task=task,
                candidates=generated_candidates,
                train_cases=train_cases,
            )
        )
        
        self.store.save_rejections(
            directory=output_directory,
            rejections=rejections,
        )

        if not candidates:
            details = "\n".join(
                (
                    f"- {rejection.candidate_name}: "
                    f"{rejection.reason}"
                )
                for rejection in rejections
            )

            raise RuntimeError(
                "Tous les prompts générés ont été rejetés.\n"
                f"{details}\n\n"
                "Les prompts bruts ont été conservés dans : "
                f"{output_directory / 'raw'}"
            )

        #
        # 5. Sauvegarde AVANT évaluation
        #
        candidate_paths = (
            self.store.save_candidates(
                directory=output_directory,
                task_name=task.name,
                candidates=candidates,
            )
        )

        #
        # 6. Baseline VALIDATION
        #
        # Important :
        # ces résultats n'ont jamais été fournis au générateur.
        #
        print("[4/6] Évaluation baseline VALIDATION...")
        
        baseline_validation_results = (
            await self.runner.run(
                task=task,
                cases=validation_cases,
            )
        )

        baseline_validation_report = (
            EvalReport.from_results(
                task_name=task.name,
                dataset_name="validation",
                results=(
                    baseline_validation_results
                ),
            )
        )

        evaluations: list[
            CandidateEvaluation
        ] = []

        #
        # 7. Réévaluer chaque candidat
        #
        for candidate in candidates:
            print(
                f"[5/6] Évaluation "
                f"{candidate.name} sur TRAIN..."
            )
            
            train_results = (
                await self.runner.run(
                    task=task,
                    cases=train_cases,
                    prompt_template=(
                        candidate.template
                    ),
                )
            )

            train_report = (
                EvalReport.from_results(
                    task_name=task.name,
                    dataset_name="train",
                    results=train_results,
                )
            )

            train_comparison = (
                self.comparator.compare(
                    baseline_name="production",
                    baseline_results=(
                        baseline_train_results
                    ),
                    baseline_report=(
                        baseline_train_report
                    ),
                    candidate_name=(
                        candidate.name
                    ),
                    candidate_results=(
                        train_results
                    ),
                    candidate_report=(
                        train_report
                    ),
                )
            )

            print(
                f"[6/6] Évaluation "
                f"{candidate.name} sur VALIDATION..."
            )

            validation_results = (
                await self.runner.run(
                    task=task,
                    cases=validation_cases,
                    prompt_template=(
                        candidate.template
                    ),
                )
            )

            validation_report = (
                EvalReport.from_results(
                    task_name=task.name,
                    dataset_name="validation",
                    results=(
                        validation_results
                    ),
                )
            )

            validation_comparison = (
                self.comparator.compare(
                    baseline_name="production",
                    baseline_results=(
                        baseline_validation_results
                    ),
                    baseline_report=(
                        baseline_validation_report
                    ),
                    candidate_name=(
                        candidate.name
                    ),
                    candidate_results=(
                        validation_results
                    ),
                    candidate_report=(
                        validation_report
                    ),
                )
            )

            evaluations.append(
                CandidateEvaluation(
                    candidate=candidate,
                    prompt_path=(
                        candidate_paths[
                            candidate.name
                        ]
                    ),
                    train_report=(
                        train_report
                    ),
                    train_comparison=(
                        train_comparison
                    ),
                    validation_report=(
                        validation_report
                    ),
                    validation_comparison=(
                        validation_comparison
                    ),
                )
            )

        #
        # 8. Sauvegarder les résultats
        #
        self.store.save_evaluations(
            directory=output_directory,
            evaluations=evaluations,
        )

        return PromptOptimizationResult(
            task_name=task.name,
            run_id=run_id,
            output_directory=(
                output_directory
            ),
            baseline_train_report=(
                baseline_train_report
            ),
            baseline_validation_report=(
                baseline_validation_report
            ),
            candidates=evaluations,
        )

    @staticmethod
    def _validate_candidates(
        *,
        task: EvalTask,
        candidates: list[
            GeneratedPromptCandidate
        ],
        train_cases: list[EvalCase],
    ) -> tuple[
        list[GeneratedPromptCandidate],
        list[CandidateRejection],
    ]:
        valid: list[
            GeneratedPromptCandidate
        ] = []

        rejected: list[
            CandidateRejection
        ] = []

        case_ids = {
            case.id
            for case in train_cases
        }

        for candidate in candidates:
            try:
                task.validate_prompt_template(
                    candidate.template
                )

            except ValueError as error:
                rejected.append(
                    CandidateRejection(
                        candidate_name=(
                            candidate.name
                        ),
                        reason=(
                            "Validation du prompt échouée : "
                            f"{error}"
                        ),
                    )
                )

                continue

            lowered = (
                candidate.template.casefold()
            )

            matching_case_id = next(
                (
                    case_id
                    for case_id in case_ids
                    if case_id.casefold()
                    in lowered
                ),
                None,
            )

            if matching_case_id is not None:
                rejected.append(
                    CandidateRejection(
                        candidate_name=(
                            candidate.name
                        ),
                        reason=(
                            "Le prompt contient directement "
                            "un identifiant du dataset TRAIN : "
                            f"{matching_case_id}"
                        ),
                    )
                )

                continue

            valid.append(
                candidate
            )

        return (
            valid,
            rejected,
        )
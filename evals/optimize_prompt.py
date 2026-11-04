from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from accessi_code.config import settings
from accessi_code.service.default_services import (
    build_default_audit_services,
)

from evals.comparison.comparator import (
    PromptComparator,
)
from evals.datasets.loader import (
    load_eval_cases,
)
from evals.optimization.context import (
    OptimizationContextBuilder,
)
from evals.optimization.generator import (
    PromptCandidateGenerator,
)
from evals.optimization.optimizer import (
    PromptOptimizer,
)
from evals.optimization.storage import (
    PromptCandidateStore,
)
from evals.runners.runner import EvalRunner
from evals.tasks.default_registry import (
    build_default_eval_registry,
)
from accessi_code.ai.clients.llm import OllamaLLM

from evals.selection.models import (
    PromptSelectionResult,
)
from evals.selection.selector import (
    PromptSelector,
)


EVALS_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Génère et évalue automatiquement "
            "des prompts candidats."
        )
    )

    parser.add_argument(
        "task",
        help="Tâche IA à optimiser, par exemple title.",
    )

    parser.add_argument(
        "--candidates",
        type=int,
        default=3,
        help="Nombre de candidats à demander à l'optimiseur.",
    )
    
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help=(
            "Nombre maximal d'appels IA "
            "exécutés simultanément."
        ),
    )

    return parser.parse_args()


def print_result(result) -> None:
    print()
    print("=" * 70)
    print("ACCESSICODE PROMPT OPTIMIZATION")
    print("=" * 70)

    print(
        f"Task              : {result.task_name}"
    )

    print(
        f"Run               : {result.run_id}"
    )

    print(
        f"Output            : {result.output_directory}"
    )

    print()

    print(
        "Production TRAIN  : "
        f"{result.baseline_train_report.accuracy * 100:.2f}% "
        f"| "
        f"{result.baseline_train_report.average_decision_score:.2f}/100"
    )

    print(
        "Production VALID. : "
        f"{result.baseline_validation_report.accuracy * 100:.2f}% "
        f"| "
        f"{result.baseline_validation_report.average_decision_score:.2f}/100"
    )

    for evaluation in result.candidates:
        candidate = evaluation.candidate

        train_comparison = (
            evaluation.train_comparison
        )

        validation_comparison = (
            evaluation.validation_comparison
        )

        print()
        print("-" * 70)

        print(
            f"{candidate.name}"
        )

        if candidate.rationale:
            print(
                f"Strategy          : {candidate.rationale}"
            )

        print(
            "TRAIN score       : "
            f"{evaluation.train_report.average_decision_score:.2f}/100 "
            f"({train_comparison.score_delta:+.2f})"
        )

        print(
            "TRAIN accuracy    : "
            f"{evaluation.train_report.accuracy * 100:.2f}% "
            f"({train_comparison.accuracy_delta * 100:+.2f})"
        )

        print(
            "TRAIN regressions : "
            f"{len(train_comparison.regressions)}"
        )

        print(
            "VALID score       : "
            f"{evaluation.validation_report.average_decision_score:.2f}/100 "
            f"({validation_comparison.score_delta:+.2f})"
        )

        print(
            "VALID accuracy    : "
            f"{evaluation.validation_report.accuracy * 100:.2f}% "
            f"({validation_comparison.accuracy_delta * 100:+.2f})"
        )

        print(
            "VALID regressions : "
            f"{len(validation_comparison.regressions)}"
        )

        print(
            "Critical errors   : "
            f"{evaluation.validation_report.critical_errors}"
        )

        if validation_comparison.improvements:
            print(
                "Validation improvements:"
            )

            for change in (
                validation_comparison.improvements
            ):
                print(
                    f"  + {change.case_id}: "
                    f"{change.baseline_status} "
                    f"→ {change.candidate_status}"
                )

        if validation_comparison.regressions:
            print(
                "Validation regressions:"
            )

            for change in (
                validation_comparison.regressions
            ):
                print(
                    f"  - {change.case_id}: "
                    f"{change.baseline_status} "
                    f"→ {change.candidate_status}"
                )

    print()
    print("=" * 70)


def print_selection(
    selection: PromptSelectionResult,
) -> None:
    print()
    print("=" * 70)
    print("PROMPT SELECTION")
    print("=" * 70)

    for candidate in selection.ranking:
        print()
        print(
            f"#{candidate.rank} "
            f"{candidate.name}"
        )

        print(
            "Eligible          : "
            f"{'YES' if candidate.eligible else 'NO'}"
        )

        print(
            "VALID accuracy    : "
            f"{candidate.validation_accuracy * 100:.2f}% "
            f"({candidate.validation_accuracy_delta * 100:+.2f})"
        )

        print(
            "VALID score       : "
            f"{candidate.validation_score:.2f}/100 "
            f"({candidate.validation_score_delta:+.2f})"
        )

        print(
            "VALID critical    : "
            f"{candidate.validation_critical_errors} "
            f"({candidate.validation_critical_errors_delta:+d})"
        )

        print(
            "VALID improvements: "
            f"{candidate.validation_improvements}"
        )

        print(
            "VALID regressions : "
            f"{candidate.validation_regressions}"
        )

        print(
            "TRAIN score       : "
            f"{candidate.train_score:.2f}/100 "
            f"({candidate.train_score_delta:+.2f})"
        )

        if candidate.reasons:
            print(
                "Reasons           :"
            )

            for reason in candidate.reasons:
                print(
                    f"  - {reason}"
                )

    print()
    print("-" * 70)

    if selection.keep_production:
        print(
            "RECOMMENDATION : "
            "KEEP PRODUCTION PROMPT"
        )

    else:
        assert (
            selection.recommended_candidate
            is not None
        )

        print(
            "RECOMMENDATION : "
            f"{selection.recommended_candidate.name}"
        )

        print(
            "Prompt file     : "
            f"{selection.recommended_candidate.prompt_path}"
        )

    print()
    print(
        selection.summary
    )

    print()
    print(
        "Aucune modification du prompt "
        "de production n'a été effectuée."
    )

    print("=" * 70)


async def main() -> None:
    args = parse_args()

    if args.candidates < 1:
        raise SystemExit(
            "--candidates doit être supérieur ou égal à 1."
        )
    
    if args.concurrency < 1:
        raise SystemExit(
            "--concurrency doit être supérieur ou égal à 1."
        )

    services = build_default_audit_services(
        ollama_host=settings.OLLAMA_HOST,
        llm_model=settings.LLM_MODEL,
        vlm_model=settings.VLM_MODEL,
    )

    registry = build_default_eval_registry(
        services
    )

    task = registry.get(
        args.task
    )

    train_cases = load_eval_cases(
        EVALS_ROOT
        / "datasets"
        / task.name
        / "train.json"
    )

    validation_cases = load_eval_cases(
        EVALS_ROOT
        / "datasets"
        / task.name
        / "validation.json"
    )

    #
    # Le modèle évalué reste Gemma via services.page_analyzer.
    #
    # En revanche, l'optimiseur de prompts utilise Qwen
    # comme modèle textuel indépendant.
    #
    optimizer_llm = OllamaLLM(
        model=settings.VLM_MODEL,
        host=settings.OLLAMA_HOST,
    )

    print(
        "Modèle utilisé pour l'optimisation : "
        f"{settings.VLM_MODEL}"
    )

    optimizer = PromptOptimizer(
        runner=EvalRunner(
            max_concurrency=args.concurrency
        ),
        comparator=PromptComparator(),
        context_builder=OptimizationContextBuilder(
            max_problem_cases=12,
            max_anchor_cases=3,
        ),
        generator=PromptCandidateGenerator(
            llm=optimizer_llm
        ),
        store=PromptCandidateStore(
            root_directory=(
                EVALS_ROOT
                / "prompts"
            )
        ),
    )

    result = await optimizer.optimize(
        task=task,
        train_cases=train_cases,
        validation_cases=validation_cases,
        candidate_count=args.candidates,
    )

    print_result(
        result
    )
    
    selector = PromptSelector()

    selection = selector.select(
        result
    )

    print_selection(
        selection
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
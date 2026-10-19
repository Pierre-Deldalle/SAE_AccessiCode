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
from evals.datasets.loader import load_eval_cases
from evals.models.comparison import (
    PromptComparison,
)
from evals.models.report import EvalReport
from evals.prompts.loader import (
    load_prompt_variants,
)
from evals.runners.runner import EvalRunner
from evals.tasks.default_registry import (
    build_default_eval_registry,
)

EVALS_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare plusieurs variantes d'un prompt AccessiCode."
        ),
    )

    parser.add_argument(
        "task",
        help="Tâche IA à comparer, par exemple title.",
    )

    parser.add_argument(
        "--dataset",
        default="train",
        help="Dataset utilisé pour la comparaison.",
    )

    return parser.parse_args()


def print_comparison(
    comparison: PromptComparison,
) -> None:
    print()
    print("=" * 70)

    print(
        f"{comparison.baseline_name} "
        f"VS {comparison.candidate_name}"
    )

    print("=" * 70)

    print(
        "Accuracy : "
        f"{comparison.baseline_accuracy * 100:.2f}% "
        "→ "
        f"{comparison.candidate_accuracy * 100:.2f}% "
        f"({comparison.accuracy_delta * 100:+.2f})"
    )

    print(
        "Decision score : "
        f"{comparison.baseline_score:.2f} "
        "→ "
        f"{comparison.candidate_score:.2f} "
        f"({comparison.score_delta:+.2f})"
    )

    print(
        "Critical errors : "
        f"{comparison.baseline_critical_errors} "
        "→ "
        f"{comparison.candidate_critical_errors}"
    )

    print()

    print(
        f"Improvements : {len(comparison.improvements)}"
    )

    for change in comparison.improvements:
        print(
            f"  + {change.case_id}: "
            f"{change.baseline_status} "
            f"→ {change.candidate_status} "
            f"({change.score_delta:+.0f})"
        )

    print()

    print(
        f"Regressions : {len(comparison.regressions)}"
    )

    for change in comparison.regressions:
        print(
            f"  - {change.case_id}: "
            f"{change.baseline_status} "
            f"→ {change.candidate_status} "
            f"({change.score_delta:+.0f})"
        )

    print()

    print(
        "Confidence / score improvements : "
        f"{len(comparison.score_improvements)}"
    )

    for change in comparison.score_improvements:
        print(
            f"  ↑ {change.case_id}: "
            f"{change.baseline_score:.0f} "
            f"→ {change.candidate_score:.0f}"
        )

    print()

    print(
        "Confidence / score regressions : "
        f"{len(comparison.score_regressions)}"
    )

    for change in comparison.score_regressions:
        print(
            f"  ↓ {change.case_id}: "
            f"{change.baseline_score:.0f} "
            f"→ {change.candidate_score:.0f}"
        )


async def main() -> None:
    args = parse_args()

    services = build_default_audit_services(
        ollama_host=settings.OLLAMA_HOST,
        llm_model=settings.LLM_MODEL,
        vlm_model=settings.VLM_MODEL,
    )

    registry = build_default_eval_registry(
        services,
    )

    task = registry.get(
        args.task
    )

    dataset_path = (
        EVALS_ROOT
        / "datasets"
        / task.name
        / f"{args.dataset}.json"
    )

    cases = load_eval_cases(
        dataset_path
    )

    prompts_directory = (
        EVALS_ROOT
        / "prompts"
        / task.name
    )

    candidates = load_prompt_variants(
        prompts_directory
    )

    for candidate in candidates:
        task.validate_prompt_template(
            candidate.template
        )

    runner = EvalRunner()

    print(
        "Exécution du prompt de référence..."
    )

    baseline_results = await runner.run(
        task=task,
        cases=cases,
    )

    baseline_report = EvalReport.from_results(
        task_name=task.name,
        dataset_name=args.dataset,
        results=baseline_results,
    )

    comparator = PromptComparator()

    for candidate in candidates:
        print()
        print(
            f"Exécution de {candidate.name}..."
        )

        candidate_results = await runner.run(
            task=task,
            cases=cases,
            prompt_template=candidate.template,
        )

        candidate_report = EvalReport.from_results(
            task_name=task.name,
            dataset_name=args.dataset,
            results=candidate_results,
        )

        comparison = comparator.compare(
            baseline_name="production",
            baseline_results=baseline_results,
            baseline_report=baseline_report,
            candidate_name=candidate.name,
            candidate_results=candidate_results,
            candidate_report=candidate_report,
        )

        print_comparison(
            comparison
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )

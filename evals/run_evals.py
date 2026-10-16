from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from accessi_code.config import settings
from accessi_code.service.default_services import (
    build_default_audit_services,
)

from evals.datasets.loader import load_eval_cases
from evals.models.report import EvalReport
from evals.models.result import EvalResult
from evals.runners.runner import EvalRunner
from evals.tasks.default_registry import (
    build_default_eval_registry,
)


EVALS_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exécute les évaluations IA d'AccessiCode.",
    )

    parser.add_argument(
        "task",
        help="Fonctionnalité IA à évaluer, par exemple : title.",
    )

    parser.add_argument(
        "--dataset",
        default="train",
        help="Dataset à utiliser : train, validation ou test.",
    )

    return parser.parse_args()


def get_dataset_path(
    task_name: str,
    dataset_name: str,
) -> Path:
    return (
        EVALS_ROOT
        / "datasets"
        / task_name
        / f"{dataset_name}.json"
    )


def print_result(
    result: EvalResult,
) -> None:
    print("-" * 60)

    print(
        f"Case             : {result.case_id}"
    )

    print(
        f"Status           : {result.status.value.upper()}"
    )

    print(
        f"Decision score   : {result.decision_score:.2f} / 100"
    )

    print(
        "Expected         :",
        json.dumps(
            result.expected,
            ensure_ascii=False,
        ),
    )

    if result.actual is not None:
        print(
            "Actual           :",
            json.dumps(
                result.actual,
                ensure_ascii=False,
            ),
        )

    if result.confidence is not None:
        print(
            f"Confidence       : {result.confidence}"
        )

    if result.decision_issues:
        print(
            "Decision issues  :",
            ", ".join(
                result.decision_issues
            ),
        )

    if result.integrity_score is not None:
        print(
            f"Integrity score  : {result.integrity_score:.2f} / 100"
        )

    if result.integrity_issues:
        print(
            "Integrity issues :",
            ", ".join(
                result.integrity_issues
            ),
        )

    if result.error_type is not None:
        print(
            f"Error type       : {result.error_type}"
        )

    if result.error_message is not None:
        print(
            f"Error            : {result.error_message}"
        )


def print_summary(
    report: EvalReport,
) -> None:
    print()
    print("=" * 60)
    print("ACCESSICODE AI EVALUATION")
    print("=" * 60)

    print(
        f"Task                    : {report.task_name}"
    )

    print(
        f"Dataset                 : {report.dataset_name}"
    )

    print(
        f"Cases                   : {report.total_cases}"
    )

    print()

    print(
        f"Correct                 : {report.correct}"
    )

    print(
        f"Incorrect               : {report.incorrect}"
    )

    print(
        f"Errors                  : {report.errors}"
    )

    print(
        f"Accuracy                : {report.accuracy * 100:.2f} %"
    )

    print(
        "Average decision score  : "
        f"{report.average_decision_score:.2f} / 100"
    )

    print()

    print(
        "TRUE accuracy           : "
        f"{report.true_correct}/{report.true_total} "
        f"({report.percentage(report.true_correct, report.true_total):.2f} %)"
    )

    print(
        "FALSE accuracy          : "
        f"{report.false_correct}/{report.false_total} "
        f"({report.percentage(report.false_correct, report.false_total):.2f} %)"
    )

    print(
        "NULL accuracy           : "
        f"{report.null_correct}/{report.null_total} "
        f"({report.percentage(report.null_correct, report.null_total):.2f} %)"
    )

    print()

    print(
        f"Critical errors         : {report.critical_errors}"
    )

    print(
        f"Forced verdicts         : {report.forced_verdicts}"
    )

    print(
        "Unnecessary abstentions : "
        f"{report.unnecessary_abstentions}"
    )

    print(
        "Correct but low conf.   : "
        f"{report.unnecessary_low_confidence}"
    )

    print()

    print(
        "Avg response integrity  : "
        f"{report.average_integrity_score:.2f} / 100"
    )

    print(
        "Integrity problems      : "
        f"{report.integrity_problems}"
    )

    if report.integrity_issue_counts:
        print()

        print(
            "Integrity issue details :"
        )

        for issue, count in sorted(
            report.integrity_issue_counts.items()
        ):
            print(
                f"  - {issue}: {count}"
            )

    print("=" * 60)


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

    try:
        task = registry.get(
            args.task
        )

    except KeyError as error:
        raise SystemExit(
            str(error)
        ) from error

    dataset_path = get_dataset_path(
        task_name=task.name,
        dataset_name=args.dataset,
    )

    try:
        cases = load_eval_cases(
            dataset_path,
        )

    except (
        FileNotFoundError,
        ValueError,
    ) as error:
        raise SystemExit(
            str(error)
        ) from error

    print()
    print("=" * 60)
    print("ACCESSICODE AI EVALUATION")
    print("=" * 60)

    print(
        f"Task       : {task.name}"
    )

    print(
        f"Dataset    : {args.dataset}"
    )

    print(
        f"File       : {dataset_path}"
    )

    print(
        f"Cases      : {len(cases)}"
    )

    print("=" * 60)
    print()

    runner = EvalRunner()

    results = await runner.run(
        task=task,
        cases=cases,
    )

    for result in results:
        print_result(
            result
        )

    report = EvalReport.from_results(
        task_name=task.name,
        dataset_name=args.dataset,
        results=results,
    )

    print_summary(
        report
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
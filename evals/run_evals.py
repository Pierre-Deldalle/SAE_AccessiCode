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
from evals.models.result import EvalResult, EvalStatus
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
    print(f"Case       : {result.case_id}")
    print(f"Status     : {result.status.value.upper()}")
    print(f"Score      : {result.score:.2f}")

    print(
        "Expected   :",
        json.dumps(
            result.expected,
            ensure_ascii=False,
        ),
    )

    if result.actual is not None:
        print(
            "Actual     :",
            json.dumps(
                result.actual,
                ensure_ascii=False,
            ),
        )

    if result.error_type is not None:
        print(f"Error type : {result.error_type}")

    if result.error_message is not None:
        print(f"Error      : {result.error_message}")


def print_summary(
    task_name: str,
    dataset_name: str,
    results: list[EvalResult],
) -> None:
    total = len(results)

    correct = sum(
        result.status == EvalStatus.CORRECT
        for result in results
    )

    incorrect = sum(
        result.status == EvalStatus.INCORRECT
        for result in results
    )

    errors = sum(
        result.status == EvalStatus.ERROR
        for result in results
    )

    score = (
        sum(result.score for result in results) / total
        if total
        else 0.0
    )

    print()
    print("=" * 60)
    print("ACCESSICODE AI EVALUATION")
    print("=" * 60)
    print(f"Task       : {task_name}")
    print(f"Dataset    : {dataset_name}")
    print(f"Cases      : {total}")
    print()
    print(f"Correct    : {correct}")
    print(f"Incorrect  : {incorrect}")
    print(f"Errors     : {errors}")
    print(f"Score      : {score * 100:.2f} %")
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
        task = registry.get(args.task)

    except KeyError as error:
        raise SystemExit(str(error)) from error

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
        raise SystemExit(str(error)) from error

    print()
    print("=" * 60)
    print("ACCESSICODE AI EVALUATION")
    print("=" * 60)
    print(f"Task       : {task.name}")
    print(f"Dataset    : {args.dataset}")
    print(f"File       : {dataset_path}")
    print(f"Cases      : {len(cases)}")
    print("=" * 60)
    print()

    runner = EvalRunner()

    results = await runner.run(
        task=task,
        cases=cases,
    )

    for result in results:
        print_result(result)

    print_summary(
        task_name=task.name,
        dataset_name=args.dataset,
        results=results,
    )


if __name__ == "__main__":
    asyncio.run(main())
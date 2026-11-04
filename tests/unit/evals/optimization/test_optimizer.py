from typing import Any

import pytest

from evals.comparison.comparator import (
    PromptComparator,
)
from evals.models.case import EvalCase
from evals.optimization.context import (
    OptimizationContextBuilder,
)
from evals.optimization.models import (
    GeneratedPromptCandidate,
)
from evals.optimization.optimizer import (
    PromptOptimizer,
)
from evals.optimization.storage import (
    PromptCandidateStore,
)
from evals.runners.runner import EvalRunner
from evals.tasks.base import EvalTask


class FakeOptimizationTask(EvalTask):
    name = "fake_optimization"

    production_prompt_template = (
        "PROMPT PRODUCTION"
    )

    async def execute(
        self,
        case: EvalCase,
        *,
        prompt_template: str | None = None,
    ) -> dict[str, Any]:
        if prompt_template is None:
            decision = case.input_data[
                "production_actual"
            ]

            confidence = case.input_data[
                "production_confidence"
            ]

        else:
            decision = case.input_data[
                "candidate_actual"
            ]

            confidence = case.input_data[
                "candidate_confidence"
            ]

        return {
            "relevant": decision,
            "confidence": confidence,
            "explanation": (
                "Explication correcte."
            ),
            "contradictions": [],
            "uncertainties": [],
        }


class FakeGenerator:
    def __init__(
        self,
        candidates: list[
            GeneratedPromptCandidate
        ],
    ):
        self.candidates = candidates
        self.received_context = None

    async def generate(
        self,
        *,
        optimization_context,
        candidate_count: int,
    ):
        self.received_context = (
            optimization_context
        )

        return self.candidates[
            :candidate_count
        ]


def create_case(
    case_id: str,
    *,
    expected: bool | None,
    production_actual: bool | None,
    candidate_actual: bool | None,
    production_confidence: str,
    candidate_confidence: str,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        input_data={
            "production_actual": (
                production_actual
            ),
            "candidate_actual": (
                candidate_actual
            ),
            "production_confidence": (
                production_confidence
            ),
            "candidate_confidence": (
                candidate_confidence
            ),
        },
        expected={
            "relevant": expected,
        },
    )


@pytest.mark.asyncio
async def test_optimizer_generates_saves_and_evaluates_candidate(
    tmp_path,
):
    train_cases = [
        create_case(
            "train_bad",
            expected=False,
            production_actual=True,
            candidate_actual=False,
            production_confidence="low",
            candidate_confidence="high",
        ),
        create_case(
            "train_good",
            expected=True,
            production_actual=True,
            candidate_actual=True,
            production_confidence="high",
            candidate_confidence="high",
        ),
    ]

    validation_cases = [
        create_case(
            "validation_bad",
            expected=False,
            production_actual=True,
            candidate_actual=False,
            production_confidence="low",
            candidate_confidence="high",
        ),
    ]

    generator = FakeGenerator(
        [
            GeneratedPromptCandidate(
                name="candidate_001",
                template=(
                    "PROMPT CANDIDAT GENERIQUE"
                ),
                rationale=(
                    "Corriger les erreurs."
                ),
            )
        ]
    )

    optimizer = PromptOptimizer(
        runner=EvalRunner(),
        comparator=PromptComparator(),
        context_builder=(
            OptimizationContextBuilder()
        ),
        generator=generator,
        store=PromptCandidateStore(
            root_directory=(
                tmp_path
                / "prompts"
            )
        ),
    )

    result = await optimizer.optimize(
        task=FakeOptimizationTask(),
        train_cases=train_cases,
        validation_cases=(
            validation_cases
        ),
        candidate_count=1,
    )

    assert (
        result.baseline_train_report.accuracy
        == 0.5
    )

    assert (
        result.candidates[0]
        .train_report.accuracy
        == 1.0
    )

    assert (
        result.baseline_validation_report.accuracy
        == 0.0
    )

    assert (
        result.candidates[0]
        .validation_report.accuracy
        == 1.0
    )

    assert (
        result.candidates[0]
        .prompt_path.exists()
    )

    assert (
        result.output_directory
        / "evaluation.json"
    ).exists()


@pytest.mark.asyncio
async def test_optimizer_never_exposes_validation_to_generator(
    tmp_path,
):
    train_cases = [
        create_case(
            "TRAIN_SECRET_CASE",
            expected=False,
            production_actual=True,
            candidate_actual=False,
            production_confidence="low",
            candidate_confidence="high",
        ),
    ]

    validation_cases = [
        create_case(
            "VALIDATION_MUST_NOT_BE_VISIBLE",
            expected=False,
            production_actual=True,
            candidate_actual=False,
            production_confidence="low",
            candidate_confidence="high",
        ),
    ]

    generator = FakeGenerator(
        [
            GeneratedPromptCandidate(
                name="candidate_001",
                template="PROMPT GENERIQUE",
                rationale="Test",
            )
        ]
    )

    optimizer = PromptOptimizer(
        runner=EvalRunner(),
        comparator=PromptComparator(),
        context_builder=(
            OptimizationContextBuilder()
        ),
        generator=generator,
        store=PromptCandidateStore(
            root_directory=(
                tmp_path
                / "prompts"
            )
        ),
    )

    await optimizer.optimize(
        task=FakeOptimizationTask(),
        train_cases=train_cases,
        validation_cases=(
            validation_cases
        ),
        candidate_count=1,
    )

    assert (
        generator.received_context
        is not None
    )

    context_as_text = str(
        generator.received_context
    )

    assert (
        "TRAIN_SECRET_CASE"
        in context_as_text
    )

    assert (
        "VALIDATION_MUST_NOT_BE_VISIBLE"
        not in context_as_text
    )


@pytest.mark.asyncio
async def test_optimizer_never_changes_production_prompt(
    tmp_path,
):
    original_prompt = (
        FakeOptimizationTask
        .production_prompt_template
    )

    generator = FakeGenerator(
        [
            GeneratedPromptCandidate(
                name="candidate_001",
                template=(
                    "AUTRE PROMPT"
                ),
                rationale="Test",
            )
        ]
    )

    optimizer = PromptOptimizer(
        runner=EvalRunner(),
        comparator=PromptComparator(),
        context_builder=(
            OptimizationContextBuilder()
        ),
        generator=generator,
        store=PromptCandidateStore(
            root_directory=(
                tmp_path
                / "prompts"
            )
        ),
    )

    case = create_case(
        "train_case",
        expected=True,
        production_actual=True,
        candidate_actual=True,
        production_confidence="high",
        candidate_confidence="high",
    )

    await optimizer.optimize(
        task=FakeOptimizationTask(),
        train_cases=[case],
        validation_cases=[case],
        candidate_count=1,
    )

    assert (
        FakeOptimizationTask
        .production_prompt_template
        == original_prompt
    )


@pytest.mark.asyncio
async def test_optimizer_rejects_candidate_containing_train_case_id(
    tmp_path,
):
    train_cases = [
        create_case(
            "train_case_123",
            expected=False,
            production_actual=True,
            candidate_actual=False,
            production_confidence="low",
            candidate_confidence="high",
        ),
    ]

    generator = FakeGenerator(
        [
            GeneratedPromptCandidate(
                name="candidate_001",
                template=(
                    "Si le cas est "
                    "train_case_123, "
                    "réponds false."
                ),
                rationale=(
                    "Overfitting volontaire."
                ),
            )
        ]
    )

    optimizer = PromptOptimizer(
        runner=EvalRunner(),
        comparator=PromptComparator(),
        context_builder=(
            OptimizationContextBuilder()
        ),
        generator=generator,
        store=PromptCandidateStore(
            root_directory=(
                tmp_path
                / "prompts"
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Tous les prompts générés "
            "ont été rejetés"
        ),
    ):
        await optimizer.optimize(
            task=FakeOptimizationTask(),
            train_cases=train_cases,
            validation_cases=[],
            candidate_count=1,
        )
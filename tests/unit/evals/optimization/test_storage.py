import json

import pytest

from evals.comparison.comparator import (
    PromptComparator,
)
from evals.models.report import EvalReport
from evals.models.result import (
    EvalResult,
    EvalStatus,
)
from evals.optimization.models import (
    CandidateEvaluation,
    GeneratedPromptCandidate,
)
from evals.optimization.storage import (
    PromptCandidateStore,
)


def create_result() -> EvalResult:
    return EvalResult(
        task_name="title",
        case_id="title_001",
        status=EvalStatus.CORRECT,
        expected={
            "relevant": True,
        },
        actual={
            "relevant": True,
            "confidence": "high",
            "explanation": "Correct.",
        },
        expected_decision=True,
        actual_decision=True,
        confidence="high",
        decision_score=100.0,
        decision_issues=(),
        integrity_score=100.0,
        integrity_issues=(),
    )


def test_store_creates_run_directory(
    tmp_path,
):
    store = PromptCandidateStore(
        root_directory=(
            tmp_path
            / "prompts"
        )
    )

    run_id, directory = (
        store.create_run_directory(
            task_name="title",
            run_id="run_001",
        )
    )

    assert run_id == "run_001"

    assert directory.exists()

    assert directory == (
        tmp_path
        / "prompts"
        / "title"
        / "generated"
        / "run_001"
    )


def test_store_refuses_existing_run_directory(
    tmp_path,
):
    store = PromptCandidateStore(
        root_directory=(
            tmp_path
            / "prompts"
        )
    )

    store.create_run_directory(
        task_name="title",
        run_id="run_001",
    )

    with pytest.raises(
        FileExistsError
    ):
        store.create_run_directory(
            task_name="title",
            run_id="run_001",
        )


def test_store_saves_candidates_and_manifest(
    tmp_path,
):
    store = PromptCandidateStore(
        root_directory=(
            tmp_path
            / "prompts"
        )
    )

    _, directory = (
        store.create_run_directory(
            task_name="title",
            run_id="run_001",
        )
    )

    candidates = [
        GeneratedPromptCandidate(
            name="candidate_001",
            template="Prompt candidat 1",
            rationale="Stratégie 1",
        ),
        GeneratedPromptCandidate(
            name="candidate_002",
            template="Prompt candidat 2",
            rationale="Stratégie 2",
        ),
    ]

    paths = store.save_candidates(
        directory=directory,
        task_name="title",
        candidates=candidates,
    )

    assert (
        paths["candidate_001"]
        .read_text(
            encoding="utf-8"
        )
        == "Prompt candidat 1"
    )

    metadata = json.loads(
        (
            directory
            / "candidate_001.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        metadata["rationale"]
        == "Stratégie 1"
    )

    manifest = json.loads(
        (
            directory
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest["task"] == "title"

    assert len(
        manifest["candidates"]
    ) == 2


def test_store_saves_evaluation_report(
    tmp_path,
):
    store = PromptCandidateStore(
        root_directory=(
            tmp_path
            / "prompts"
        )
    )

    _, directory = (
        store.create_run_directory(
            task_name="title",
            run_id="run_001",
        )
    )

    candidate = (
        GeneratedPromptCandidate(
            name="candidate_001",
            template="Prompt candidat",
            rationale="Stratégie",
        )
    )

    paths = store.save_candidates(
        directory=directory,
        task_name="title",
        candidates=[candidate],
    )

    baseline_results = [
        create_result()
    ]

    candidate_results = [
        create_result()
    ]

    baseline_report = (
        EvalReport.from_results(
            task_name="title",
            dataset_name="train",
            results=baseline_results,
        )
    )

    candidate_report = (
        EvalReport.from_results(
            task_name="title",
            dataset_name="train",
            results=candidate_results,
        )
    )

    comparison = (
        PromptComparator().compare(
            baseline_name="production",
            baseline_results=(
                baseline_results
            ),
            baseline_report=(
                baseline_report
            ),
            candidate_name=(
                "candidate_001"
            ),
            candidate_results=(
                candidate_results
            ),
            candidate_report=(
                candidate_report
            ),
        )
    )

    evaluation = CandidateEvaluation(
        candidate=candidate,
        prompt_path=paths[
            "candidate_001"
        ],
        train_report=(
            candidate_report
        ),
        train_comparison=(
            comparison
        ),
        validation_report=(
            candidate_report
        ),
        validation_comparison=(
            comparison
        ),
    )

    store.save_evaluations(
        directory=directory,
        evaluations=[
            evaluation
        ],
    )

    evaluation_path = (
        directory
        / "evaluation.json"
    )

    assert evaluation_path.exists()

    data = json.loads(
        evaluation_path.read_text(
            encoding="utf-8"
        )
    )

    assert len(data) == 1

    assert (
        data[0]["candidate"]
        == "candidate_001"
    )

    assert (
        data[0]["train"]["report"][
            "accuracy"
        ]
        == 1.0
    )
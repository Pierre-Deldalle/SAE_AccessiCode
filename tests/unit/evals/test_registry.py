from typing import Any

import pytest

from evals.models.case import EvalCase
from evals.tasks.base import EvalTask
from evals.tasks.registry import EvalTaskRegistry


class FakeEvalTask(EvalTask):
    name = "fake"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        return {
            "value": True,
        }

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        return 1.0


def test_registry_can_register_and_get_task():
    task = FakeEvalTask()

    registry = EvalTaskRegistry()

    registry.register(task)

    assert registry.get("fake") is task
    assert registry.names() == ["fake"]


def test_registry_accepts_tasks_during_initialization():
    task = FakeEvalTask()

    registry = EvalTaskRegistry(
        [
            task,
        ]
    )

    assert registry.get("fake") is task


def test_registry_rejects_duplicate_task():
    registry = EvalTaskRegistry(
        [
            FakeEvalTask(),
        ]
    )

    with pytest.raises(
        ValueError,
        match="déjà enregistrée",
    ):
        registry.register(
            FakeEvalTask(),
        )


def test_registry_rejects_unknown_task():
    registry = EvalTaskRegistry(
        [
            FakeEvalTask(),
        ]
    )

    with pytest.raises(
        KeyError,
        match="Tâche d'évaluation inconnue",
    ):
        registry.get("unknown")


def test_registry_lists_available_task_in_unknown_task_error():
    registry = EvalTaskRegistry(
        [
            FakeEvalTask(),
        ]
    )

    with pytest.raises(KeyError) as error:
        registry.get("unknown")

    assert "fake" in str(error.value)


def test_registry_rejects_object_that_is_not_eval_task():
    registry = EvalTaskRegistry()

    with pytest.raises(TypeError):
        registry.register(object())

from __future__ import annotations

from collections.abc import Iterable

from evals.tasks.base import EvalTask


class EvalTaskRegistry:
    """
    Registre des fonctionnalités IA disponibles pour l'évaluation.
    """

    def __init__(
        self,
        tasks: Iterable[EvalTask] | None = None,
    ):
        self._tasks: dict[str, EvalTask] = {}

        if tasks is not None:
            for task in tasks:
                self.register(task)

    def register(
        self,
        task: EvalTask,
    ) -> None:
        if not isinstance(task, EvalTask):
            raise TypeError("Seules des instances de EvalTask peuvent être enregistrées.")

        if not task.name:
            raise ValueError("Une EvalTask doit posséder un nom.")

        if task.name in self._tasks:
            raise ValueError(f"La tâche d'évaluation {task.name!r} est déjà enregistrée.")

        self._tasks[task.name] = task

    def get(
        self,
        name: str,
    ) -> EvalTask:
        try:
            return self._tasks[name]

        except KeyError as error:
            available = ", ".join(self.names())

            raise KeyError(
                f"Tâche d'évaluation inconnue : {name!r}. "
                f"Tâches disponibles : {available or 'aucune'}."
            ) from error

    def names(self) -> list[str]:
        return list(self._tasks.keys())
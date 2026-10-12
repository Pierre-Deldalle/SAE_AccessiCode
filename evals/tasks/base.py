from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from evals.models.case import EvalCase


class EvalTask(ABC):
    """
    Fonctionnalité IA pouvant être évaluée par le moteur.

    Une tâche sait :
    - comment appeler l'analyseur IA ;
    - comment comparer sa réponse à la vérité attendue.
    """

    name: ClassVar[str]

    @abstractmethod
    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        """
        Exécute l'analyse IA correspondant au cas.
        """
        raise NotImplementedError

    @abstractmethod
    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        """
        Compare la réponse obtenue au résultat attendu.

        Le score doit être compris entre 0 et 1.
        """
        raise NotImplementedError
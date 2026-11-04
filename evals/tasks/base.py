from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from accessi_code.ai.schemas import AIConfidence

from evals.models.case import EvalCase


class EvalTask(ABC):
    name: ClassVar[str]

    decision_key: ClassVar[str] = "relevant"
    confidence_key: ClassVar[str] = "confidence"

    production_prompt_template: ClassVar[str | None] = None

    @abstractmethod
    async def execute(
        self,
        case: EvalCase,
        *,
        prompt_template: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_production_prompt_template(self) -> str:
        prompt = self.production_prompt_template

        if prompt is None or not prompt.strip():
            raise RuntimeError(
                f"La tâche {self.name!r} ne déclare pas "
                "de prompt de production."
            )

        return prompt

    def validate_prompt_template(
        self,
        prompt_template: str,
    ) -> None:
        if not prompt_template.strip():
            raise ValueError(
                "Un prompt candidat ne peut pas être vide."
            )

    def get_expected_decision(
        self,
        case: EvalCase,
    ) -> bool | None:
        if self.decision_key not in case.expected:
            raise ValueError(
                f"Le cas {case.id!r} ne possède pas "
                f"de valeur attendue pour {self.decision_key!r}."
            )

        value = case.expected[self.decision_key]

        self._validate_decision(
            value,
            field_name=f"expected.{self.decision_key}",
        )

        return value

    def get_actual_decision(
        self,
        actual: dict[str, Any],
    ) -> bool | None:
        if self.decision_key not in actual:
            raise ValueError(
                f"La réponse IA ne possède pas "
                f"le champ {self.decision_key!r}."
            )

        value = actual[self.decision_key]

        self._validate_decision(
            value,
            field_name=self.decision_key,
        )

        return value

    def get_confidence(
        self,
        actual: dict[str, Any],
    ) -> AIConfidence:
        value = actual.get(self.confidence_key)

        if value not in {
            "low",
            "medium",
            "high",
        }:
            raise ValueError(
                "La réponse IA doit contenir une "
                "confidence 'low', 'medium' ou 'high'."
            )

        return value

    @staticmethod
    def _validate_decision(
        value: Any,
        *,
        field_name: str,
    ) -> None:
        if (
            value is not True
            and value is not False
            and value is not None
        ):
            raise ValueError(
                f"{field_name} doit être true, false ou null."
            )
"""Modèles simulés pour tester les analyseurs IA sans Ollama."""

from __future__ import annotations

import json
from typing import Any


class FakeModel:
    """
    Modèle qui renvoie des réponses prédéfinies, dans l'ordre.

    Une réponse peut être un dict (sérialisé en JSON), une chaîne brute
    ou une exception (levée lors de l'appel).
    """

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.calls: list[dict[str, Any]] = []

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        self.prompts.append(prompt)
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("Appel inattendu au modèle.")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, str):
            return response
        return json.dumps(response, ensure_ascii=False)

    @property
    def call_count(self) -> int:
        return len(self.prompts)


def batch(*results: dict[str, Any]) -> dict[str, Any]:
    """Réponse de lot : chaque résultat reçoit son id dans l'ordre."""
    return {"results": [{"id": index, **result} for index, result in enumerate(results)]}

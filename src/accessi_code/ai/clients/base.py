from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class BaseModelEndpoint(ABC):
    """
    Interface commune minimale des clients de modèles IA.

    Les implémentations concrètes peuvent représenter un LLM, un VLM
    ou tout autre modèle exposant des opérations de génération.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """
        Génère une réponse textuelle à partir d'un prompt.
        """
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        messages: Sequence[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Génère une réponse textuelle à partir d'une conversation.
        """
        raise NotImplementedError

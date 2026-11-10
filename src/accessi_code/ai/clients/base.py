from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

# Plafond optionnel du nombre de tokens générés (machines lentes, tests).
TOKEN_CAP_ENV = "ACCESSICODE_AI_TOKEN_CAP"


def cap_max_tokens(max_tokens: int) -> int:
    """
    Limite max_tokens à la valeur de ACCESSICODE_AI_TOKEN_CAP si elle est définie.

    Une valeur absente, invalide ou non positive est ignorée.
    """
    raw = os.environ.get(TOKEN_CAP_ENV, "").strip()
    try:
        cap = int(raw)
    except ValueError:
        return max_tokens
    return min(max_tokens, cap) if cap > 0 else max_tokens


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

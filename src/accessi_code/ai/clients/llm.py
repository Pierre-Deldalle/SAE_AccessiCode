from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import aiohttp

from accessi_code.ai.clients.base import BaseModelEndpoint


class OllamaLLM(BaseModelEndpoint):
    """
    Client asynchrone pour un modèle textuel exposé par Ollama.
    """

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
    ):
        self.model = model
        self.host = host.rstrip("/")

    async def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Envoie une requête POST à Ollama et retourne la réponse JSON.
        """
        url = f"{self.host}{endpoint}"

        timeout = aiohttp.ClientTimeout(total=180)

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:
            async with session.post(
                url,
                json=payload,
            ) as response:
                if response.status != 200:
                    text = await response.text()

                    raise RuntimeError(
                        "Erreur HTTP Ollama "
                        f"{response.status} sur {url}: {text}"
                    )

                data = await response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "La réponse Ollama n'est pas un objet JSON."
            )

        return data

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        max_tokens: int = 1500,
        temperature: float = 0.2,
        format: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Génère une réponse à partir d'un prompt utilisateur.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.25,
                "repeat_last_n": 64,
                "top_p": 0.85,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        if format is not None:
            payload["format"] = format

        payload.update(kwargs)

        response = await self._post(
            "/api/generate",
            payload,
        )

        text = response.get("response")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Ollama a renvoyé une réponse textuelle vide."
            )

        return text

    async def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        format: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Génère une réponse à partir d'une liste de messages.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.25,
                "repeat_last_n": 64,
                "top_p": 0.85,
            },
        }

        if format is not None:
            payload["format"] = format

        payload.update(kwargs)

        response = await self._post(
            "/api/chat",
            payload,
        )

        message = response.get("message")

        if not isinstance(message, dict):
            raise ValueError(
                "La réponse Ollama ne contient pas de message."
            )

        content = message.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                "Ollama a renvoyé une réponse textuelle vide."
            )

        return content
from __future__ import annotations

import base64
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import aiohttp

from accessi_code.ai.clients.base import BaseModelEndpoint


ImageInput = str | Path | bytes | bytearray


class OllamaVLM(BaseModelEndpoint):
    """
    Client asynchrone pour un modèle de vision exposé par Ollama.
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
        Envoie une requête POST à Ollama.
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

    @staticmethod
    def _image_to_base64(
        image: ImageInput,
    ) -> str:
        """
        Convertit un chemin ou des données binaires en base64.
        """
        if isinstance(image, (str, Path)):
            path = Path(image)

            if not path.is_file():
                raise FileNotFoundError(
                    f"Image introuvable : {path}"
                )

            image_bytes = path.read_bytes()

        elif isinstance(image, (bytes, bytearray)):
            image_bytes = bytes(image)

        else:
            raise TypeError(
                "L'image doit être un chemin ou des données binaires."
            )

        if not image_bytes:
            raise ValueError(
                "L'image fournie est vide."
            )

        return base64.b64encode(
            image_bytes
        ).decode("ascii")

    async def generate(
        self,
        prompt: str,
        *,
        image: ImageInput,
        system_prompt: str = "",
        max_tokens: int = 1500,
        temperature: float = 0.2,
        format: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Analyse une image avec un prompt.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "images": [
                self._image_to_base64(image)
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
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
                "Ollama a renvoyé une réponse VLM vide."
            )

        return text

    async def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        image: ImageInput,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        format: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Compatibilité avec l'interface commune BaseModelEndpoint.

        Les messages sont regroupés en prompt système et prompt utilisateur.
        """
        system_prompt = "\n".join(
            message["content"]
            for message in messages
            if message.get("role") == "system"
        )

        prompt = "\n".join(
            message["content"]
            for message in messages
            if message.get("role") == "user"
        )

        return await self.generate(
            prompt,
            image=image,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            format=format,
            **kwargs,
        )
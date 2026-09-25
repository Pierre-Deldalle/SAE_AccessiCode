import base64
from pathlib import Path
from typing import Any, Dict, List, Union

import aiohttp

from .base import BaseModelEndpoint


class OllamaVLM(BaseModelEndpoint):
    """Client minimal pour les modèles de vision Ollama."""

    def __init__(self, model: str = "qwen3-vl:instruct", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.host}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Erreur HTTP Ollama {response.status} sur {url}: {text}")
                return await response.json()

    @staticmethod
    def _image_to_base64(image: Union[str, Path, bytes, bytearray]) -> str:
        if isinstance(image, (str, Path)):
            image_bytes = Path(image).read_bytes()
        elif isinstance(image, (bytes, bytearray)):
            image_bytes = bytes(image)
        else:
            raise TypeError("image doit être un chemin (str/Path) ou des bytes.")

        if not image_bytes:
            raise ValueError("L'image fournie est vide.")
        return base64.b64encode(image_bytes).decode("ascii")

    async def generate(
        self,
        prompt: str,
        image: Union[str, Path, bytes, bytearray],
        system_prompt: str = "",
        max_tokens: int = 1500,
        temperature: float = 0.2,
        **kw: Any,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "images": [self._image_to_base64(image)],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        payload.update(kw)

        response = await self._post("/api/generate", payload)
        response_text = response.get("response", "")
        if not response_text:
            raise ValueError(f"Ollama a renvoyé un texte vide. Réponse brute : {response}")
        return response_text

    async def chat(
        self,
        messages: List[Dict[str, str]],
        image: Union[str, Path, bytes, bytearray],
        max_tokens: int = 1500,
        temperature: float = 0.2,
        **kw: Any,
    ) -> str:
        system_prompt = "\n".join(message["content"] for message in messages if message.get("role") == "system")
        user_messages = [message["content"] for message in messages if message.get("role") == "user"]
        prompt = "\n".join(user_messages)
        return await self.generate(
            prompt=prompt,
            image=image,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kw,
        )

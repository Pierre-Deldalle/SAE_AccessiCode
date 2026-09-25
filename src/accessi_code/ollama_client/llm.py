"""Client asynchrone minimal pour l'API textuelle d'Ollama.

Le client expose deux opérations : ``generate`` pour un prompt simple et
``chat`` pour une conversation composée de messages. Les réponses sont
désérialisées depuis l'API Ollama et le texte généré est retourné à la couche
de service d'audit.
"""

from typing import Any, Dict, List

import aiohttp

from .base import BaseModelEndpoint


class OllamaLLM(BaseModelEndpoint):
    """Envoie des requêtes de génération textuelle à un serveur Ollama."""

    def __init__(self, model: str = "gemma:26b", host: str = "http://localhost:11434"):
        """Configure le modèle et l'adresse du serveur Ollama."""
        self.model = model
        self.host = host.rstrip("/")

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POSTe une charge utile JSON et lève une erreur si Ollama échoue."""
        url = f"{self.host}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=180)) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Erreur HTTP Ollama {response.status} sur {url}: {text}")
                return await response.json()

    async def generate(
        self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2, **kw
    ) -> str:
        """Génère une réponse textuelle à partir d'un prompt utilisateur."""
        # Extraire format s'il est transmis dans kw
        format_param = kw.pop("format", None)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.25,
                "repeat_last_n": 64,
                "top_p": 0.85,
            },
            "stream": False,
        }

        if format_param:
            payload["format"] = format_param

        payload.update(kw)

        resp = await self._post("/api/generate", payload)

        response_text = resp.get("response", "")
        if not response_text:
            raise ValueError(f"Ollama a renvoyé un texte vide. Réponse brute : {resp}")

        return response_text

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1500, temperature: float = 0.2, **kw) -> str:
        """Génère une réponse à partir d'une liste de messages de conversation."""
        format_param = kw.pop("format", None)
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.25,
                "repeat_last_n": 64,
            },
            "stream": False,
        }
        if format_param:
            payload["format"] = format_param

        payload.update(kw)

        resp = await self._post("/api/chat", payload)
        return resp.get("message", {}).get("content", "")

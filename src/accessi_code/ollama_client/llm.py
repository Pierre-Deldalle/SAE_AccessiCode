# src/accessi_code/ollama_client/llm.py
import aiohttp
from typing import Any, Dict, List
from .base import BaseModelEndpoint

class OllamaLLM(BaseModelEndpoint):
    def __init__(self, model: str = "gemma:26b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip('/')

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.host}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=180)) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Erreur HTTP Ollama {response.status} sur {url}: {text}")
                return await response.json()

    async def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2, **kw) -> str:
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
                "top_p": 0.85
            },
            "stream": False
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
        format_param = kw.pop("format", None)
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.25,
                "repeat_last_n": 64
            },
            "stream": False
        }
        if format_param:
            payload["format"] = format_param
            
        payload.update(kw)
        
        resp = await self._post("/api/chat", payload)
        return resp.get("message", {}).get("content", "")
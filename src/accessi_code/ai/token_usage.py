"""
Comptage des tokens consommés par les appels à l'IA pendant un audit.

Chaque réponse d'Ollama indique le nombre de tokens lus (``prompt_eval_count`` :
la question, avec le HTML et le contexte envoyés) et générés (``eval_count`` :
la réponse). Les clients (ai/clients/llm.py, ai/clients/vlm.py) les ajoutent au
compteur de l'audit en cours, que l'orchestrateur active le temps de l'audit.

Le compteur suit le contexte asyncio : les appels lancés depuis l'audit, même
dans des tâches ou des threads enfants, sont comptés dans cet audit, et deux
audits simultanés ne se mélangent pas. Une réponse lue dans le cache ne coûte
aucun token et n'est donc pas comptée.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class TokenUsage:
    """Tokens consommés par un audit."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def __post_init__(self) -> None:
        self._lock = Lock()

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        with self._lock:
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.calls += 1


_CURRENT: ContextVar[TokenUsage | None] = ContextVar("accessicode_token_usage", default=None)


def _count(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def record_response(response: Mapping[str, Any]) -> None:
    """Ajoute les tokens d'une réponse Ollama au compteur de l'audit en cours (s'il y en a un)."""
    usage = _CURRENT.get()
    if usage is not None:
        usage.add(_count(response.get("prompt_eval_count")), _count(response.get("eval_count")))


@contextmanager
def track_tokens(usage: TokenUsage | None = None) -> Iterator[TokenUsage]:
    """Active un compteur pour le bloc : tous les appels à l'IA du bloc y sont ajoutés."""
    usage = usage if usage is not None else TokenUsage()
    token = _CURRENT.set(usage)
    try:
        yield usage
    finally:
        _CURRENT.reset(token)


def format_tokens(count: int) -> str:
    """« 12 345 tokens » (espace fine insécable entre les milliers, à la française)."""
    return f"{count:,}".replace(",", " ") + (" token" if count <= 1 else " tokens")

"""
Cache des analyses IA.

Une même image ou un même texte peut être examiné par plusieurs tests RGAA
(par exemple une image par les critères 1.1 à 1.8). Le cache évite de
reposer la même question au modèle.

La clé est construite à partir du contenu analysé : deux audits différents
partageant exactement le même contenu obtiennent la même réponse, ce qui
reste correct. La taille est bornée pour que l'application de bureau, qui
réutilise ses services d'un audit à l'autre, ne grossisse pas indéfiniment.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any, Generic, TypeVar

T = TypeVar("T")

DEFAULT_MAX_ENTRIES = 2048


def make_key(*parts: Any) -> str:
    """Construit une clé stable à partir de valeurs sérialisables en JSON."""
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AnalysisCache(Generic[T]):
    """Cache LRU borné."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries doit être strictement positif.")
        self.max_entries = max_entries
        self._entries: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> T | None:
        value = self._entries.get(key)
        if value is not None:
            self._entries.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

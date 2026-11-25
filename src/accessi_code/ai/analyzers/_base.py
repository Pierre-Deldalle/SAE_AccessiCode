"""
Socle commun des analyseurs IA textuels.

Regroupe ce que chaque analyseur réécrivait jusqu'ici :
- demande d'une réponse JSON, avec une seconde tentative plus stricte ;
- nouvelle tentative en cas d'erreur réseau transitoire ;
- lecture sûre des champs (booléen ou null, listes, confiance) ;
- nettoyage des explications dégénérées (voir ``text_safety``).

Les analyseurs n'émettent jamais de verdict RGAA : ils retournent des
observations que les tests RGAA convertissent en statut.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, TypeVar

import aiohttp

from accessi_code.ai.cache import AnalysisCache
from accessi_code.ai.json_utils import parse_ai_json
from accessi_code.ai.schemas import AIConfidence
from accessi_code.ai.text_safety import clean_explanation

T = TypeVar("T")

# Nombre d'éléments envoyés dans une même requête au modèle.
DEFAULT_BATCH_SIZE = 15

STRICT_JSON_SUFFIX = "IMPORTANT : retourne un unique objet JSON valide, sans Markdown ni texte supplémentaire."

NETWORK_ERRORS = (
    aiohttp.ClientError,
    OSError,
    asyncio.TimeoutError,
)


class JsonAnalyzer:
    """Analyseur qui interroge un modèle et attend un objet JSON."""

    max_tokens: int = 800

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    async def _generate_json(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Demande un objet JSON au modèle.

        Raises:
            ValueError: si aucune des deux tentatives ne produit un JSON exploitable.
            RuntimeError: si la connexion au modèle échoue deux fois.
        """
        last_error: Exception | None = None

        for candidate in (prompt, f"{prompt}\n\n{STRICT_JSON_SUFFIX}"):
            response = await self._generate_with_retry(candidate, max_tokens or self.max_tokens)
            try:
                return parse_ai_json(response)
            except ValueError as error:
                last_error = error

        raise ValueError(f"Réponse JSON inexploitable : {last_error}")

    async def _generate_with_retry(self, prompt: str, max_tokens: int) -> str:
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                return await self.llm.generate(
                    prompt,
                    format="json",
                    max_tokens=max_tokens,
                    temperature=0,
                )
            except NETWORK_ERRORS as error:
                last_error = error
                if attempt == 0:
                    await asyncio.sleep(0.5)

        raise RuntimeError(f"La connexion avec Ollama a été interrompue : {last_error}") from last_error

    async def _run_batched(
        self,
        *,
        keys: list[str],
        payloads: list[dict[str, Any]],
        build_prompt: Callable[[str], str],
        parse_item: Callable[[dict[str, Any]], T],
        missing_item: Callable[[str], T],
        cache: AnalysisCache[T],
        batch_size: int = DEFAULT_BATCH_SIZE,
        tokens_per_item: int = 160,
    ) -> list[T]:
        """
        Interroge le modèle par lots et retourne un résultat par élément, dans l'ordre.

        - Les éléments déjà analysés sont lus dans le cache.
        - Chaque élément reçoit un ``id`` local au lot ; la réponse est associée par id.
        - Un élément absent ou mal formé dans la réponse donne ``missing_item`` (jamais mis en cache).
        - Une réponse globalement inexploitable lève ``ValueError`` (le test produit alors ERROR).
        """
        if len(keys) != len(payloads):
            raise ValueError("keys et payloads doivent avoir la même longueur.")

        results: list[T | None] = [cache.get(key) for key in keys]
        pending = [index for index, value in enumerate(results) if value is None]

        for start in range(0, len(pending), batch_size):
            chunk = pending[start : start + batch_size]
            items = [{"id": local_id, **payloads[index]} for local_id, index in enumerate(chunk)]

            data = await self._generate_json(
                build_prompt(json.dumps(items, ensure_ascii=False, indent=1)),
                max_tokens=100 + tokens_per_item * len(chunk),
            )

            entries = data.get("results")
            if not isinstance(entries, list):
                raise ValueError("La réponse ne contient pas de liste « results ».")

            by_id: dict[int, dict[str, Any]] = {}
            for entry in entries:
                if isinstance(entry, dict):
                    entry_id = entry.get("id")
                    if isinstance(entry_id, int) and not isinstance(entry_id, bool):
                        by_id.setdefault(entry_id, entry)

            for local_id, index in enumerate(chunk):
                entry = by_id.get(local_id)
                if entry is None:
                    results[index] = missing_item("L'élément est absent de la réponse de l'IA.")
                    continue
                try:
                    parsed = parse_item(entry)
                except ValueError as error:
                    results[index] = missing_item(f"Réponse de l'IA mal formée : {error}")
                    continue
                results[index] = parsed
                cache.set(keys[index], parsed)

        return [value for value in results if value is not None]


def read_tristate(data: dict[str, Any], key: str) -> bool | None:
    """
    Lit un champ qui doit valoir true, false ou null.

    Raises:
        ValueError: si la valeur n'est pas un booléen ni null.
    """
    value = data.get(key)
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"Le champ {key} doit être true, false ou null.")


def read_strings(value: Any) -> list[str]:
    """Liste de chaînes ; toute autre valeur donne une liste vide."""
    if not isinstance(value, list):
        return []
    return [" ".join(str(item).split()) for item in value if str(item).strip()]


def read_confidence(value: Any) -> AIConfidence:
    """Confiance déclarée ; une valeur inconnue est ramenée à "low"."""
    if value in {"low", "medium", "high"}:
        return value
    return "low"


def read_explanation(data: dict[str, Any]) -> tuple[str, bool]:
    """
    Explication nettoyée et indicateur de réponse corrompue.

    Une réponse corrompue ne doit jamais conduire à une conclusion :
    l'appelant force alors la confiance à "low".
    """
    return clean_explanation(data.get("explanation"))


SUGGESTION_LIMIT = 200


def truncate(text: str, limit: int) -> str:
    """Texte normalisé et tronqué pour rester dans le contexte du modèle."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"

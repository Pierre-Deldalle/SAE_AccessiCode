"""
Analyse de la pertinence de textes : titres de cadres, titres de sections,
intitulés de liens, étiquettes, légendes, boutons, titres de tableaux…

Les éléments sont envoyés par lots pour limiter le nombre d'appels au modèle,
et chaque réponse est mise en cache.
"""

from __future__ import annotations

from typing import Any

from accessi_code.ai.analyzers._base import (
    DEFAULT_BATCH_SIZE,
    JsonAnalyzer,
    read_confidence,
    read_explanation,
    read_strings,
    read_tristate,
    truncate,
)
from accessi_code.ai.cache import AnalysisCache, make_key
from accessi_code.ai.prompts.relevance import RELEVANCE_BATCH_PROMPT, RELEVANCE_KINDS
from accessi_code.ai.schemas import RelevanceAnalysis, RelevanceItem

TEXT_LIMIT = 300
HTML_LIMIT = 400
CONTEXT_LIMIT = 600
DETAIL_LIMIT = 300
SUGGESTION_LIMIT = 200


class OllamaTextRelevanceAnalyzer(JsonAnalyzer):
    """Juge la pertinence de textes d'un même type, par lots."""

    def __init__(self, llm: Any, *, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        super().__init__(llm)
        self.batch_size = batch_size
        self.cache: AnalysisCache[RelevanceAnalysis] = AnalysisCache()

    async def analyze_relevance(
        self,
        kind: str,
        items: list[RelevanceItem],
    ) -> list[RelevanceAnalysis]:
        """
        Retourne un jugement par élément, dans l'ordre des éléments fournis.

        Raises:
            ValueError: type inconnu ou réponse globalement inexploitable.
            RuntimeError: connexion au modèle impossible.
        """
        spec = RELEVANCE_KINDS.get(kind)
        if spec is None:
            raise ValueError(f"Type de pertinence inconnu : {kind}")
        if not items:
            return []

        payloads = [_payload(item, spec.text_limit) for item in items]

        def build_prompt(items_json: str) -> str:
            return RELEVANCE_BATCH_PROMPT.format(
                subject=spec.subject,
                rule=spec.rule,
                relevant_when=spec.relevant_when,
                not_relevant_examples=spec.not_relevant_examples,
                items=items_json,
            )

        return await self._run_batched(
            keys=[make_key("relevance", kind, payload) for payload in payloads],
            payloads=payloads,
            build_prompt=build_prompt,
            parse_item=_parse_relevance,
            missing_item=_unknown,
            cache=self.cache,
            batch_size=self.batch_size,
        )


def _payload(item: RelevanceItem, text_limit: int = TEXT_LIMIT) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": truncate(item.text, text_limit)}
    if item.element_html:
        payload["html"] = truncate(item.element_html, HTML_LIMIT)
    if item.context:
        payload["context"] = truncate(item.context, CONTEXT_LIMIT)
    for key, value in item.details.items():
        if value:
            payload[key] = truncate(str(value), DETAIL_LIMIT)
    return payload


def _parse_relevance(entry: dict[str, Any]) -> RelevanceAnalysis:
    relevant = read_tristate(entry, "relevant")
    explanation, corrupted = read_explanation(entry)
    relevant = None if corrupted else relevant
    return RelevanceAnalysis(
        relevant=relevant,
        explanation=explanation,
        problems=read_strings(entry.get("problems")),
        uncertainties=read_strings(entry.get("uncertainties")),
        confidence="low" if corrupted else read_confidence(entry.get("confidence")),
        # Une proposition n'a de sens que pour un texte jugé non pertinent.
        suggestion=_read_suggestion(entry.get("suggestion")) if relevant is False else None,
    )


def _read_suggestion(value: Any) -> str | None:
    """Texte proposé par le modèle ; absent, vide ou d'un autre type que texte → None, jamais d'erreur."""
    if not isinstance(value, str):
        return None
    text = truncate(value, SUGGESTION_LIMIT)
    if not text or text.lower() in {"null", "none", "aucune", "n/a"}:
        return None
    return text


def _unknown(reason: str) -> RelevanceAnalysis:
    return RelevanceAnalysis(relevant=None, explanation=reason, confidence="low")

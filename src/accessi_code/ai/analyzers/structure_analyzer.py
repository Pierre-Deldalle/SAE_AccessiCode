"""
Analyse de la structuration de l'information (thème 9) :
- passages non balisés qui devraient être des titres, listes ou citations ;
- pertinence de la hiérarchie des titres.
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
from accessi_code.ai.prompts.structure import HEADING_HIERARCHY_PROMPT, STRUCTURE_BATCH_PROMPT, STRUCTURE_RULES
from accessi_code.ai.schemas import RelevanceAnalysis, StructureCandidate, StructureCandidateAnalysis
from accessi_code.ai.text_safety import read_suggestion

TEXT_LIMIT = 500
HTML_LIMIT = 500
CONTEXT_LIMIT = 500
HEADING_TEXT_LIMIT = 120
MAX_OUTLINE_ENTRIES = 150


class OllamaStructureAnalyzer(JsonAnalyzer):
    """Qualifie des passages de texte et juge la hiérarchie des titres."""

    def __init__(self, llm: Any, *, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        super().__init__(llm)
        self.batch_size = batch_size
        self.cache: AnalysisCache[StructureCandidateAnalysis] = AnalysisCache()
        self.hierarchy_cache: AnalysisCache[RelevanceAnalysis] = AnalysisCache()

    async def classify_candidates(
        self,
        kind: str,
        candidates: list[StructureCandidate],
    ) -> list[StructureCandidateAnalysis]:
        """Un résultat par candidat, dans l'ordre fourni."""
        rule = STRUCTURE_RULES.get(kind)
        if rule is None:
            raise ValueError(f"Type de structure inconnu : {kind}")
        if not candidates:
            return []

        suggest = kind == "presentation_quote"
        subject = (
            "Tu analyses des passages déjà balisés comme des citations."
            if suggest
            else "Tu analyses des passages d'une page web qui ne sont pas balisés sémantiquement."
        )
        payloads = [
            {
                "text": truncate(candidate.text, TEXT_LIMIT),
                "html": truncate(candidate.element_html, HTML_LIMIT),
                "context": truncate(candidate.context, CONTEXT_LIMIT),
            }
            for candidate in candidates
        ]

        return await self._run_batched(
            keys=[make_key("structure", kind, payload) for payload in payloads],
            payloads=payloads,
            build_prompt=lambda items_json: STRUCTURE_BATCH_PROMPT.format(subject=subject, rule=rule, items=items_json),
            parse_item=lambda entry: _parse_candidate(entry, suggest=suggest),
            missing_item=_unknown_candidate,
            cache=self.cache,
            batch_size=self.batch_size,
            tokens_per_item=120,
        )

    async def analyze_heading_hierarchy(
        self,
        outline: list[tuple[int, str]],
        suspicious: list[str],
    ) -> RelevanceAnalysis:
        """
        Juge la pertinence de la hiérarchie des titres.

        outline :
            (niveau, texte) de chaque titre, dans l'ordre du document.
        suspicious :
            passages repérés par le test (sauts de niveau, premier titre
            qui n'est pas un h1…), présentés au modèle comme points d'attention.
        """
        entries = outline[:MAX_OUTLINE_ENTRIES]
        outline_text = "\n".join(f"h{level} – {truncate(text, HEADING_TEXT_LIMIT)}" for level, text in entries)
        if len(outline) > MAX_OUTLINE_ENTRIES:
            outline_text += f"\n… ({len(outline) - MAX_OUTLINE_ENTRIES} titres supplémentaires non affichés)"
        suspicious_text = "\n".join(f"- {item}" for item in suspicious) or "- aucun"

        key = make_key("hierarchy", outline_text, suspicious_text)
        cached = self.hierarchy_cache.get(key)
        if cached is not None:
            return cached

        data = await self._generate_json(
            HEADING_HIERARCHY_PROMPT.format(outline=outline_text, suspicious=suspicious_text),
            max_tokens=700,
        )

        relevant = read_tristate(data, "relevant")
        explanation, corrupted = read_explanation(data)
        analysis = RelevanceAnalysis(
            relevant=None if corrupted else relevant,
            explanation=explanation,
            problems=read_strings(data.get("problems")),
            uncertainties=read_strings(data.get("uncertainties")),
            confidence="low" if corrupted else read_confidence(data.get("confidence")),
        )
        self.hierarchy_cache.set(key, analysis)
        return analysis


def _parse_candidate(entry: dict[str, Any], *, suggest: bool) -> StructureCandidateAnalysis:
    should_be_marked = read_tristate(entry, "should_be_marked")
    explanation, corrupted = read_explanation(entry)
    confidence = "low" if corrupted else read_confidence(entry.get("confidence"))
    return StructureCandidateAnalysis(
        should_be_marked=None if corrupted else should_be_marked,
        explanation=explanation,
        uncertainties=read_strings(entry.get("uncertainties")),
        confidence=confidence,
        suggestion=read_suggestion(entry.get("suggestion"))
        if suggest and should_be_marked is False and confidence != "low"
        else None,
    )


def _unknown_candidate(reason: str) -> StructureCandidateAnalysis:
    return StructureCandidateAnalysis(should_be_marked=None, explanation=reason, confidence="low")

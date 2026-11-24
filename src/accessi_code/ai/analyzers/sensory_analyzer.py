"""
Analyse des informations transmises par une caractéristique sensorielle :
couleur (RGAA 3.1), forme, taille ou position (RGAA 10.9 et 10.10).

Les textes sont envoyés par lots au LLM. Les images réutilisent
l'observation visuelle de l'analyseur d'images (un seul appel VLM par image).
"""

from __future__ import annotations

import json
from dataclasses import asdict
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
from accessi_code.ai.prompts.sensory import SENSORY_BATCH_PROMPT, SENSORY_IMAGE_PROMPT, SENSORY_RULES
from accessi_code.ai.schemas import SensoryAnalysis, SensoryCandidate
from accessi_code.ai.text_safety import read_suggestion
from accessi_code.analysis.images import ImageInfo

TEXT_LIMIT = 500
HTML_LIMIT = 400
CONTEXT_LIMIT = 600


class OllamaSensoryAnalyzer(JsonAnalyzer):
    """Juge si une information repose uniquement sur une caractéristique sensorielle."""

    def __init__(
        self,
        llm: Any,
        image_analyzer: Any | None = None,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        super().__init__(llm)
        self.image_analyzer = image_analyzer
        self.batch_size = batch_size
        self.cache: AnalysisCache[SensoryAnalysis] = AnalysisCache()

    async def analyze_texts(
        self,
        kind: str,
        candidates: list[SensoryCandidate],
    ) -> list[SensoryAnalysis]:
        """Un résultat par candidat, dans l'ordre fourni."""
        rule = _rule(kind)
        if not candidates:
            return []

        payloads = [
            {
                "text": truncate(candidate.text, TEXT_LIMIT),
                "html": truncate(candidate.element_html, HTML_LIMIT),
                "context": truncate(candidate.context, CONTEXT_LIMIT),
            }
            for candidate in candidates
        ]

        return await self._run_batched(
            keys=[make_key("sensory", kind, payload) for payload in payloads],
            payloads=payloads,
            build_prompt=lambda items_json: SENSORY_BATCH_PROMPT.format(rule=rule, items=items_json),
            parse_item=lambda entry: _parse_sensory(entry, suggest=kind == "shape_size_position"),
            missing_item=_unknown,
            cache=self.cache,
            batch_size=self.batch_size,
            tokens_per_item=200,
        )

    async def analyze_image(
        self,
        kind: str,
        image: ImageInfo,
    ) -> SensoryAnalysis:
        """
        Analyse une image à partir de son observation visuelle.

        Raises:
            RuntimeError: si aucun analyseur d'images n'est disponible.
        """
        rule = _rule(kind)
        if self.image_analyzer is None:
            raise RuntimeError("L'analyse sensorielle d'une image nécessite l'analyseur d'images.")

        key = make_key("sensory_image", kind, image.image_path or image.src, image.element_html, image.context_text)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        visual = await self.image_analyzer.observe(image)

        data = await self._generate_json(
            SENSORY_IMAGE_PROMPT.format(
                rule=rule,
                element_html=truncate(image.element_html, HTML_LIMIT),
                context=truncate(image.context_text, CONTEXT_LIMIT),
                visual_observations=json.dumps(asdict(visual), ensure_ascii=False),
            )
        )

        analysis = _parse_sensory(data, suggest=kind == "shape_size_position")
        self.cache.set(key, analysis)
        return analysis


def _rule(kind: str) -> str:
    rule = SENSORY_RULES.get(kind)
    if rule is None:
        raise ValueError(f"Type d'analyse sensorielle inconnu : {kind}")
    return rule


def _parse_sensory(entry: dict[str, Any], *, suggest: bool) -> SensoryAnalysis:
    flags = {
        name: read_tristate(entry, name)
        for name in ("conveys_information", "relies_only_on_sensory", "alternative_relevant")
    }
    explanation, corrupted = read_explanation(entry)
    confidence = "low" if corrupted else read_confidence(entry.get("confidence"))
    if corrupted:
        flags = dict.fromkeys(flags)
    relies_only = flags["relies_only_on_sensory"]
    needs_alternative = relies_only is True or (relies_only is False and flags["alternative_relevant"] is False)
    return SensoryAnalysis(
        **flags,
        explanation=explanation,
        characteristics=read_strings(entry.get("characteristics")),
        uncertainties=read_strings(entry.get("uncertainties")),
        confidence=confidence,
        suggestion=read_suggestion(entry.get("suggestion"))
        if suggest and confidence != "low" and flags["conveys_information"] is True and needs_alternative
        else None,
    )


def _unknown(reason: str) -> SensoryAnalysis:
    return SensoryAnalysis(
        conveys_information=None,
        relies_only_on_sensory=None,
        alternative_relevant=None,
        explanation=reason,
        confidence="low",
    )

"""Services IA simulés pour les tests unitaires du thème 1 (aucun appel Ollama)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from accessi_code.ai.schemas import (
    AlternativeAnalysis,
    DescriptionAnalysis,
    ImageProfile,
    RelevanceAnalysis,
    StructureCandidateAnalysis,
)
from accessi_code.service.audit_services import AuditServices


def profile(
    *,
    informative: bool | None = True,
    captcha: bool | None = False,
    text: bool | None = False,
    replaceable: bool | None = None,
    needs_description: bool | None = False,
    confidence: str = "high",
    text_content: str = "",
) -> ImageProfile:
    return ImageProfile(
        information_bearing=informative,
        is_captcha=captcha,
        contains_text=text,
        needs_detailed_description=needs_description,
        text_replaceable=replaceable,
        text_content=text_content,
        explanation="Profil simulé.",
        confidence=confidence,
    )


def alternative(relevant: bool | None = True, concise: bool | None = True, confidence: str = "high"):
    return AlternativeAnalysis(
        relevant=relevant, concise=concise, explanation="Analyse simulée.", confidence=confidence
    )


def description(relevant: bool | None = True, *, detailed: bool | None = True, confidence: str = "high"):
    return DescriptionAnalysis(
        relevant=relevant, explanation="Analyse simulée.", is_detailed_description=detailed, confidence=confidence
    )


def services(
    *,
    image_profile: ImageProfile | Exception | None = None,
    alternative_analysis: AlternativeAnalysis | Exception | None = None,
    description_analysis: DescriptionAnalysis | Exception | None = None,
    relevance: list[RelevanceAnalysis] | Exception | None = None,
    caption: StructureCandidateAnalysis | Exception | None = None,
) -> AuditServices:
    """AuditServices dont les analyseurs renvoient les valeurs fournies (ou lèvent l'exception)."""
    image = AsyncMock()
    _configure(image.profile, image_profile if image_profile is not None else profile())
    _configure(image.profile_element, image_profile if image_profile is not None else profile())
    _configure(image.analyze_alternative, alternative_analysis if alternative_analysis is not None else alternative())
    _configure(image.analyze, description_analysis if description_analysis is not None else description())

    text = AsyncMock()
    if isinstance(relevance, Exception):
        text.analyze_relevance.side_effect = relevance
    else:
        text.analyze_relevance.side_effect = lambda kind, items: (
            relevance if relevance is not None else [RelevanceAnalysis(True, "ok", confidence="high") for _ in items]
        )

    structure = AsyncMock()
    if isinstance(caption, Exception):
        structure.classify_candidates.side_effect = caption
    else:
        value = caption if caption is not None else StructureCandidateAnalysis(True, "Légende.", confidence="high")
        structure.classify_candidates.side_effect = lambda kind, items: [value for _ in items]

    return AuditServices(image_analyzer=image, text_relevance_analyzer=text, structure_analyzer=structure)


def _configure(mock: AsyncMock, value: Any) -> None:
    if isinstance(value, Exception):
        mock.side_effect = value
    else:
        mock.return_value = value

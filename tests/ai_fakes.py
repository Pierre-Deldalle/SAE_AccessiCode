"""
Services IA simulés pour les tests unitaires RGAA (aucun appel Ollama).

``text_services`` fournit des analyseurs de pertinence et de structuration dont
chaque élément soumis reçoit la même réponse (ou une liste de réponses dans
l'ordre), ou qui lèvent l'exception fournie.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from accessi_code.ai.schemas import RelevanceAnalysis, SensoryAnalysis, StructureCandidateAnalysis
from accessi_code.service.audit_services import AuditServices


def relevance(relevant: bool | None = True, confidence: str = "high", problems: list[str] | None = None):
    return RelevanceAnalysis(relevant, "Analyse simulée.", problems=problems or [], confidence=confidence)


def structure(marked: bool | None = True, confidence: str = "high"):
    return StructureCandidateAnalysis(marked, "Analyse simulée.", confidence=confidence)


def sensory(
    conveys: bool | None = True,
    relies_only: bool | None = False,
    alternative: bool | None = True,
    confidence: str = "high",
):
    return SensoryAnalysis(conveys, relies_only, alternative, "Analyse simulée.", confidence=confidence)


def _responder(value: Any):
    def respond(kind, items):
        if isinstance(value, list):
            return list(value[: len(items)])
        return [value for _ in items]

    return respond


def text_services(
    *,
    relevance_answer: Any = None,
    structure_answer: Any = None,
    hierarchy_answer: Any = None,
    sensory_answer: Any = None,
    sensory_image_answer: Any = None,
) -> AuditServices:
    text = AsyncMock()
    answer = relevance_answer if relevance_answer is not None else relevance()
    if isinstance(answer, Exception):
        text.analyze_relevance.side_effect = answer
    else:
        text.analyze_relevance.side_effect = _responder(answer)

    struct = AsyncMock()
    answer = structure_answer if structure_answer is not None else structure()
    if isinstance(answer, Exception):
        struct.classify_candidates.side_effect = answer
    else:
        struct.classify_candidates.side_effect = _responder(answer)

    hierarchy = hierarchy_answer if hierarchy_answer is not None else relevance()
    if isinstance(hierarchy, Exception):
        struct.analyze_heading_hierarchy.side_effect = hierarchy
    else:
        struct.analyze_heading_hierarchy.return_value = hierarchy

    senses = AsyncMock()
    answer = sensory_answer if sensory_answer is not None else sensory()
    if isinstance(answer, Exception):
        senses.analyze_texts.side_effect = answer
    else:
        senses.analyze_texts.side_effect = _responder(answer)
    answer = sensory_image_answer if sensory_image_answer is not None else sensory()
    if isinstance(answer, Exception):
        senses.analyze_image.side_effect = answer
    else:
        senses.analyze_image.return_value = answer

    return AuditServices(text_relevance_analyzer=text, structure_analyzer=struct, sensory_analyzer=senses)

"""
RGAA 4.1.2 — critère 8.7 : dans chaque page web, chaque changement de langue
est-il indiqué dans le code source ?

Test 8.7.1. Les blocs de texte visibles sont regroupés en segments de même
langue héritée (attribut lang de l'élément ou d'un parent) ; les passages
qui portent déjà leur propre lang sont masqués. L'IA juge si chaque segment
est entièrement dans la langue déclarée (noms propres et termes passés dans
l'usage exceptés) : oui → PASS, non → FAIL, incertain → NEEDS_REVIEW.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.language import language_segments
from accessi_code.analysis.sensory import identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

EMPTY_SUMMARY = "Aucun texte à analyser."
RECOMMENDATION = 'Placer le passage dans un élément portant l\'attribut lang de sa langue (par exemple lang="en").'


class Test871(RGAATest):
    """8.7.1 : chaque texte dans une autre langue est signalé par lang."""

    test_id = "8.7.1"
    criterion_id = "8.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 8.7.1 nécessite un DOM.")

        segments = language_segments(context.dom)
        if not segments:
            return not_applicable(self, EMPTY_SUMMARY)

        items = [
            RelevanceItem(
                text=segment.text,
                details={"declared_language": segment.lang or "non déclarée"},
            )
            for segment in segments
        ]
        verdicts = await judge_relevance(services, "text_language", items)

        outcomes = []
        for segment, verdict in zip(segments, verdicts, strict=True):
            first = identifier(segment.blocks[0], 0)
            element = first if len(segment.blocks) == 1 else f"{first} (+{len(segment.blocks) - 1} bloc(s))"
            problems = list(getattr(verdict.analysis, "problems", []) or [])
            passages = f" Passage(s) concerné(s) : {' ; '.join(problems)}." if problems else ""
            outcomes.append(
                make_outcome(
                    verdict.status,
                    element,
                    verdict.message(
                        f"Un changement de langue n'est pas indiqué dans ce texte (langue déclarée : "
                        f"{segment.lang or 'aucune'}).{passages}",
                        "La langue de ce texte reste à vérifier.",
                    ),
                    RECOMMENDATION,
                    declared_language=segment.lang,
                    text=segment.text[:300],
                    blocks=len(segment.blocks),
                    **verdict.evidence,
                )
            )

        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="segment(s) de texte")

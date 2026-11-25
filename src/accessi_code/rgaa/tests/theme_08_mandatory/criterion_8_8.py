"""
RGAA 4.1.2 — critère 8.8 : dans chaque page web, le code de langue de chaque
changement de langue est-il valide et pertinent ?

Test 8.8.1, pour chaque élément (hors html) qui porte lang ou xml:lang :

- code invalide (norme ISO 639) → FAIL, sans IA ;
- code valide : l'IA juge s'il correspond à la langue du texte → PASS / FAIL,
  incertain → NEEDS_REVIEW.

Un élément sans texte n'est pas un changement de langue d'un texte : ignoré.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.language import language_changes, own_lang, text_without_marked
from accessi_code.analysis.page import is_valid_language_code
from accessi_code.analysis.sensory import identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

EMPTY_SUMMARY = "Aucun changement de langue indiqué dans la page."
RECOMMENDATION = "Utiliser le code ISO 639 de la langue du texte (par exemple en, de, es)."


class Test881(RGAATest):
    """8.8.1 : code de langue valide et pertinent."""

    test_id = "8.8.1"
    criterion_id = "8.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 8.8.1 nécessite un DOM.")

        changes = [(tag, own_lang(tag) or "", text_without_marked(tag)) for tag in language_changes(context.dom)]
        changes = [(tag, code, text) for tag, code, text in changes if text]
        if not changes:
            return not_applicable(self, EMPTY_SUMMARY)

        outcomes: list[Outcome | None] = [None] * len(changes)
        to_judge: list[int] = []
        for index, (tag, code, _text) in enumerate(changes):
            if not code or not is_valid_language_code(code):
                outcomes[index] = make_outcome(
                    TestStatus.FAIL,
                    identifier(tag, index),
                    f"Le code de langue « {code} » n'est pas valide.",
                    RECOMMENDATION,
                    node=tag,
                    lang=code,
                )
            else:
                to_judge.append(index)

        items = [
            RelevanceItem(
                text=changes[index][2],
                element_html=str(changes[index][0])[:300],
                details={"declared_language": changes[index][1]},
            )
            for index in to_judge
        ]
        verdicts = await judge_relevance(services, "language_change", items)
        for index, verdict in zip(to_judge, verdicts, strict=True):
            tag, code, text = changes[index]
            outcomes[index] = make_outcome(
                verdict.status,
                identifier(tag, index),
                verdict.message(
                    f"Le code de langue « {code} » ne correspond pas à la langue du texte.",
                    f"La pertinence du code de langue « {code} » reste à vérifier.",
                ),
                verdict.recommendation(RECOMMENDATION),
                node=tag,
                lang=code,
                text=text[:300],
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=EMPTY_SUMMARY,
            noun="changement(s) de langue",
        )

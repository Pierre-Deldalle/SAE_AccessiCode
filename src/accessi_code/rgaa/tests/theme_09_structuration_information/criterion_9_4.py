"""
RGAA 4.1.2 — critère 9.4 : dans chaque page web, chaque citation est-elle
correctement indiquée ?

- 9.4.1 : chaque citation courte utilise une balise <q>.
- 9.4.2 : chaque bloc de citation utilise une balise <blockquote>.

Les balises présentes sont vérifiées dans le DOM (une balise vide n'indique
aucune citation). Les passages entre guillemets ou identifiés comme citation
sans être balisés sont soumis à l'IA, qui juge s'il s'agit réellement d'une
citation (et pas d'un simple usage de guillemets).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import StructureCandidate
from accessi_code.analysis.dom import get_element_identifier
from accessi_code.analysis.structure import block_quote_candidates, inline_quote_candidates, is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_structure
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable


async def _candidate_outcomes(
    services: Any | None,
    candidates: list[tuple[Tag, str]],
    *,
    fail: str,
    uncertain: str,
    recommendation: str,
) -> list[Outcome]:
    items = [
        StructureCandidate(text=text, element_html=str(tag)[:500], context=tag.get_text(" ", strip=True)[:500])
        for tag, text in candidates
    ]
    verdicts = await judge_structure(services, "quote", items)
    return [
        make_outcome(
            verdict.status,
            get_element_identifier(tag, index),
            verdict.message(fail.format(text=text[:100]), uncertain.format(text=text[:100])),
            recommendation,
            text=text[:200],
            **verdict.evidence,
        )
        for index, ((tag, text), verdict) in enumerate(zip(candidates, verdicts, strict=True))
    ]


def _existing_outcomes(tags: list[Tag], name: str) -> list[Outcome]:
    return [
        make_outcome(TestStatus.PASS)
        if tag.get_text(strip=True)
        else make_outcome(
            TestStatus.FAIL,
            get_element_identifier(tag, index),
            f"La balise <{name}> est vide : elle n'indique aucune citation.",
            f"Supprimer la balise <{name}> vide ou y placer la citation.",
        )
        for index, tag in enumerate(tags)
    ]


class Test941(RGAATest):
    """9.4.1 : chaque citation courte utilise-t-elle une balise <q> ?"""

    test_id = "9.4.1"
    criterion_id = "9.4"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 9.4.1 nécessite un DOM.")
        soup = context.dom
        quotes = [tag for tag in soup.find_all("q") if not is_hidden(tag)]
        candidates = inline_quote_candidates(soup)
        if not quotes and not candidates:
            return not_applicable(self, "Aucune citation courte dans la page.")

        outcomes = _existing_outcomes(quotes, "q")
        outcomes += await _candidate_outcomes(
            services,
            candidates,
            fail="La citation « {text} » n'est pas balisée avec <q>.",
            uncertain="Le passage « {text} » pourrait être une citation non balisée.",
            recommendation="Baliser chaque citation courte avec <q>.",
        )
        return build_result(self, outcomes, empty_summary="Aucune citation courte dans la page.", noun="citation(s)")


class Test942(RGAATest):
    """9.4.2 : chaque bloc de citation utilise-t-il une balise <blockquote> ?"""

    test_id = "9.4.2"
    criterion_id = "9.4"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 9.4.2 nécessite un DOM.")
        soup = context.dom
        blocks = [tag for tag in soup.find_all("blockquote") if not is_hidden(tag)]
        candidates = [(tag, tag.get_text(" ", strip=True)) for tag in block_quote_candidates(soup)]
        if not blocks and not candidates:
            return not_applicable(self, "Aucun bloc de citation dans la page.")

        outcomes = _existing_outcomes(blocks, "blockquote")
        outcomes += await _candidate_outcomes(
            services,
            candidates,
            fail="Le bloc de citation « {text} » n'est pas balisé avec <blockquote>.",
            uncertain="Le bloc « {text} » pourrait être une citation non balisée.",
            recommendation="Baliser chaque bloc de citation avec <blockquote>.",
        )
        return build_result(self, outcomes, empty_summary="Aucun bloc de citation dans la page.", noun="citation(s)")

"""
RGAA 4.1.2 — critère 5.2 : pour chaque tableau de données complexe ayant un
résumé, celui-ci est-il pertinent ?

Les résumés disponibles (caption, aria-describedby et, hors HTML5, summary)
sont soumis ensemble à l'IA avec les en-têtes et les premières lignes du
tableau : l'IA juge s'ils expliquent l'organisation du tableau.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.page import is_html5_doctype
from accessi_code.analysis.tables import (
    find_tables,
    has_complex_header_structure,
    table_identifier,
    table_preview,
    table_summaries,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

RECOMMENDATION = "Rédiger un résumé qui explique la structure du tableau (organisation des en-têtes, sens de lecture)."
EMPTY_SUMMARY = "Aucun tableau de données complexe avec résumé."


class Test521(RGAATest):
    """5.2.1 : pour chaque tableau de données complexe ayant un résumé, celui-ci est-il pertinent ?"""

    test_id = "5.2.1"
    criterion_id = "5.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 5.2.1 nécessite un DOM.")

        soup = context.dom
        allow_legacy = not is_html5_doctype(context.doctype)

        candidates = []
        for index, table in enumerate(find_tables(soup)):
            if not has_complex_header_structure(table):
                continue
            summaries = table_summaries(table, soup, allow_legacy_summary=allow_legacy)
            if summaries:
                candidates.append((index, table, summaries))

        if not candidates:
            return not_applicable(self, EMPTY_SUMMARY)

        items = [
            RelevanceItem(
                text=" / ".join(f"{source} : {text}" for source, text in summaries),
                element_html=str(table)[:400],
                context=table_preview(table),
            )
            for _, table, summaries in candidates
        ]
        verdicts = await judge_relevance(services, "table_summary", items)

        outcomes = [
            make_outcome(
                verdict.status,
                table_identifier(table, index),
                verdict.message(
                    "Le résumé du tableau de données complexe n'est pas pertinent.",
                    "La pertinence du résumé du tableau de données complexe reste à vérifier.",
                ),
                RECOMMENDATION,
                summaries=[{"source": source, "text": text} for source, text in summaries],
                **verdict.evidence,
            )
            for (index, table, summaries), verdict in zip(candidates, verdicts, strict=True)
        ]
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="tableau(x) complexe(s)")

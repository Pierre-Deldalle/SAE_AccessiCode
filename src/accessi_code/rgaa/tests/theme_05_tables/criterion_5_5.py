"""
RGAA 4.1.2 — critère 5.5 : pour chaque tableau de données ayant un titre, le
titre est-il pertinent ?

Tous les titres acceptés en 5.4 sont jugés (caption, title, aria-label,
aria-labelledby) : l'IA vérifie qu'ils identifient le contenu du tableau,
à partir de ses en-têtes et de ses premières lignes.
"""

from __future__ import annotations

from html import escape
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.tables import (
    find_tables,
    is_presentation_table,
    table_identifier,
    table_preview,
    table_titles,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

RECOMMENDATION = "Rédiger un titre qui identifie clairement et concisément le contenu du tableau."
EMPTY_SUMMARY = "Aucun tableau de données avec titre."
# Texte à remplacer dans l'exemple : le titre lui-même dépend du contenu du tableau.
TITLE_PLACEHOLDER = "[contenu du tableau]"
# Longueur du titre actuel recopié dans l'exemple, pour qu'il reste court.
EXAMPLE_TEXT_LIMIT = 80


def title_example(table: Tag, source: str, title: str, suggestion: str | None = None) -> str:
    """
    Correction « avant → après » du titre, à l'endroit où il est déclaré
    (``<caption>`` ou attribut title / aria-label du tableau). Vide pour
    aria-labelledby : le titre est alors le texte d'un autre élément de la page.
    """
    new_title = suggestion or TITLE_PLACEHOLDER
    if source == "caption":
        caption = table.find("caption", recursive=False)
        if not isinstance(caption, Tag):
            return ""
        before = title if len(title) <= EXAMPLE_TEXT_LIMIT else title[: EXAMPLE_TEXT_LIMIT - 1] + "…"
        tag = opening_tag(caption)
        return (
            f"Exemple : {tag}{escape(before, quote=False)}</caption> → {tag}{escape(new_title, quote=False)}</caption>"
        )
    if source in {"title", "aria-label"}:
        return f"Exemple : {opening_tag(table)} → {opening_tag(table, **{source: new_title})}"
    return ""


class Test551(RGAATest):
    """5.5.1 : pour chaque tableau de données ayant un titre, ce titre identifie-t-il son contenu ?"""

    test_id = "5.5.1"
    criterion_id = "5.5"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 5.5.1 nécessite un DOM.")

        soup = context.dom
        # Un titre par mécanisme : chacun est restitué et doit donc être pertinent.
        candidates = [
            (index, table, source, title)
            for index, table in enumerate(find_tables(soup))
            if not is_presentation_table(table)
            for source, title in table_titles(table, soup)
        ]
        if not candidates:
            return not_applicable(self, EMPTY_SUMMARY)

        items = [
            RelevanceItem(
                text=title,
                element_html=str(table)[:400],
                context=table_preview(table),
                details={"source": source},
            )
            for _, table, source, title in candidates
        ]
        verdicts = await judge_relevance(services, "table_title", items)

        outcomes = []
        for (index, table, source, title), verdict in zip(candidates, verdicts, strict=True):
            recommendation = verdict.recommendation(RECOMMENDATION)
            if verdict.status is TestStatus.FAIL:
                recommendation = " ".join(
                    part for part in (recommendation, title_example(table, source, title, verdict.suggestion)) if part
                )
            outcomes.append(
                make_outcome(
                    verdict.status,
                    table_identifier(table, index),
                    verdict.message(
                        f"Le titre du tableau « {title[:100]} » ({source}) n'est pas pertinent.",
                        f"La pertinence du titre du tableau « {title[:100]} » ({source}) reste à vérifier.",
                    ),
                    recommendation,
                    node=table,
                    title=title,
                    source=source,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="titre(s) de tableau")

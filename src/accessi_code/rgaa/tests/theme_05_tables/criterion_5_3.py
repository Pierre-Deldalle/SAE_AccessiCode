"""
RGAA 4.1.2 — critère 5.3 : pour chaque tableau de mise en forme, le contenu
linéarisé reste-t-il compréhensible ?

Test 5.3.1, deux conditions :
- l'élément table possède role="presentation" : vérifié sans IA, son absence
  est non conforme ;
- le contenu linéarisé reste compréhensible : l'IA lit les cellules dans
  l'ordre du code, comme un lecteur d'écran.

Un tableau sans aucune cellule d'en-tête ni titre est considéré comme un
tableau de mise en forme.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.tables import (
    find_tables,
    has_header_cells,
    is_presentation_table,
    linearized_table_text,
    table_identifier,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

EMPTY_SUMMARY = "Aucun tableau de mise en forme."
ROLE_RECOMMENDATION = 'Ajouter role="presentation" sur l\'élément table utilisé pour la mise en forme.'
ORDER_RECOMMENDATION = "Réorganiser le tableau pour que le contenu, lu cellule par cellule, garde son sens."


def is_layout_table(table: Tag) -> bool:
    """Tableau de mise en forme : déclaré comme tel, ou sans en-tête ni titre."""
    if is_presentation_table(table):
        return True
    if table.name != "table" or has_header_cells(table):
        return False
    caption = table.find("caption", recursive=False)
    has_caption = isinstance(caption, Tag) and bool(caption.get_text(strip=True))
    return not has_caption and not any(table.get(name) for name in ("aria-label", "aria-labelledby", "summary"))


class Test531(RGAATest):
    """5.3.1 : role="presentation" présent et contenu linéarisé compréhensible."""

    test_id = "5.3.1"
    criterion_id = "5.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 5.3.1 nécessite un DOM.")

        tables = [(index, table) for index, table in enumerate(find_tables(context.dom)) if is_layout_table(table)]
        if not tables:
            return not_applicable(self, EMPTY_SUMMARY)

        outcomes: list[Outcome | None] = [None] * len(tables)
        to_judge: list[tuple[int, str]] = []
        for position, (index, table) in enumerate(tables):
            identifier = table_identifier(table, index)
            if not is_presentation_table(table):
                outcomes[position] = make_outcome(
                    TestStatus.FAIL,
                    identifier,
                    "Le tableau de mise en forme n'a pas d'attribut role=\"presentation\".",
                    ROLE_RECOMMENDATION,
                )
                continue
            text = linearized_table_text(table)
            if not text:
                # Aucun contenu textuel : rien qui puisse devenir incompréhensible.
                outcomes[position] = make_outcome(TestStatus.PASS)
                continue
            to_judge.append((position, text))

        items = [RelevanceItem(text=text, element_html=str(tables[position][1])[:400]) for position, text in to_judge]
        verdicts = await judge_relevance(services, "layout_table_linearized", items)

        for (position, text), verdict in zip(to_judge, verdicts, strict=True):
            index, table = tables[position]
            outcomes[position] = make_outcome(
                verdict.status,
                table_identifier(table, index),
                verdict.message(
                    "Le contenu linéarisé du tableau de mise en forme n'est pas compréhensible.",
                    "La compréhension du contenu linéarisé du tableau de mise en forme reste à vérifier.",
                ),
                ORDER_RECOMMENDATION,
                linearized=text[:500],
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=EMPTY_SUMMARY,
            noun="tableau(x) de mise en forme",
        )

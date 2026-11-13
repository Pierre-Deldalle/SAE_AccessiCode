"""
RGAA 4.1.2 — critère 11.7 : dans chaque formulaire, chaque légende associée à
un regroupement de champs de même nature est-elle pertinente ?

11.7.1 : l'IA compare la légende aux étiquettes des champs du groupe.
Une légende absente relève de 11.6.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import fields, group_legend, group_tags, identifier, label_text
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable


class Test1171(RGAATest):
    """11.7.1 : chaque légende de regroupement est-elle pertinente ?"""

    test_id = "11.7.1"
    criterion_id = "11.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.7.1 nécessite un DOM.")

        all_fields = fields(soup)
        groups = []
        for tag in group_tags(soup):
            members = [field for field in all_fields if tag in field.parents]
            legend = group_legend(tag, soup)
            if len(members) >= 2 and legend:
                groups.append((tag, legend, members))
        if not groups:
            return not_applicable(self, "Aucun regroupement de champs avec une légende.")

        items = [
            RelevanceItem(
                text=legend,
                element_html=str(tag)[:300],
                context="Champs du groupe : "
                + ", ".join(label_text(field, soup) or "(sans étiquette)" for field in members),
            )
            for tag, legend, members in groups
        ]
        verdicts = await judge_relevance(services, "fieldset_legend", items)
        outcomes = [
            make_outcome(
                verdict.status,
                identifier(tag, soup),
                verdict.message(
                    f"La légende « {legend[:100]} » ne décrit pas la nature des champs du groupe.",
                    f"La pertinence de la légende « {legend[:100]} » reste à vérifier.",
                ),
                "Rédiger une légende qui décrit la nature commune des champs du groupe.",
                legend=legend,
                **verdict.evidence,
            )
            for (tag, legend, _), verdict in zip(groups, verdicts, strict=True)
        ]
        return build_result(self, outcomes, empty_summary="Aucune légende de regroupement.", noun="légende(s)")

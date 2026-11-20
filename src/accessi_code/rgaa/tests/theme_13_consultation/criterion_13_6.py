"""
RGAA 4.1.2 — critère 13.6 : dans chaque page web, pour chaque contenu
cryptique ayant une alternative, cette alternative est-elle pertinente ?

Concerne les contenus cryptiques (``analysis/cryptic.py``) qui ont un attribut
title (ou aria-label sur role="img"). La pertinence est une question de sens,
jugée par l'IA (``cryptic_alternative``) → PASS / FAIL, NEEDS_REVIEW si l'IA est
incertaine ou absente.

Une définition donnée par le contexte adjacent est jugée en 13.5 : l'IA y
vérifie déjà que le contexte donne le sens du contenu.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import component_identifier
from accessi_code.analysis.cryptic import find_cryptic_contents
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome

EMPTY_SUMMARY = "Aucun contenu cryptique accompagné d'un attribut title."
RECOMMENDATION = "Donner une alternative qui exprime le sens du contenu cryptique (« sourire », « à plus tard »…)."


class Test1361(RGAATest):
    test_id = "13.6.1"
    criterion_id = "13.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        contents = [content for content in find_cryptic_contents(soup) if content.alternative]
        items = [
            RelevanceItem(
                text=content.alternative,
                element_html=str(content.element)[:400],
                context=content.context,
                details={
                    "kind": content.kind,
                    "cryptic_content": content.text[:400],
                    "source": content.alternative_source,
                },
            )
            for content in contents
        ]
        verdicts = await judge_relevance(services, "cryptic_alternative", items)

        outcomes = [
            make_outcome(
                verdict.status,
                component_identifier(content.element, index),
                verdict.message(
                    f"L'alternative « {content.alternative} » ne donne pas le sens du contenu cryptique "
                    f"« {content.text[:80]} ».",
                    f"La pertinence de l'alternative « {content.alternative} » du contenu cryptique "
                    f"« {content.text[:80]} » reste à vérifier.",
                ),
                RECOMMENDATION,
                **item.details,
                alternative=content.alternative,
                **verdict.evidence,
            )
            for index, (content, item, verdict) in enumerate(zip(contents, items, verdicts, strict=True))
        ]
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="alternative(s)")

"""
RGAA 4.1.2 — critère 11.8 : dans chaque formulaire, les items de même nature
d'une liste de choix sont-ils regroupés de manière pertinente ?

- 11.8.1 : l'IA juge si les options d'un select sans optgroup forment des
  catégories qui devraient être regroupées. Une listbox ARIA qui aurait besoin
  de groupes est non conforme (role="listbox" ne permet pas de les créer).
- 11.8.2 : chaque optgroup a un attribut label (déterministe).
- 11.8.3 : le label de chaque optgroup est pertinent (IA, comparé à ses options).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import clean, identifier, label_text
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import optgroup_example

# En dessous, une liste ne peut pas raisonnablement contenir plusieurs catégories.
MIN_OPTIONS_FOR_GROUPING = 4
MAX_OPTIONS_SENT = 40


def _options_text(tag: Tag) -> str:
    names = [
        option.get_text(" ", strip=True) for option in tag.find_all(["option", lambda n: n.get("role") == "option"])
    ]
    names = [name for name in names if name]
    extra = f" … ({len(names) - MAX_OPTIONS_SENT} autres)" if len(names) > MAX_OPTIONS_SENT else ""
    return "\n".join(f"- {name}" for name in names[:MAX_OPTIONS_SENT]) + extra


class Test1181(RGAATest):
    """11.8.1 : les items de même nature d'une liste de choix sont-ils regroupés, si nécessaire ?"""

    test_id = "11.8.1"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.8.1 nécessite un DOM.")

        lists = [tag for tag in soup.find_all("select")] + soup.select('[role="listbox"]')
        if not lists:
            return not_applicable(self, "Aucune liste de choix.")

        outcomes = []
        pending: list[Tag] = []
        for tag in lists:
            options = tag.find_all("option") if tag.name == "select" else tag.select('[role="option"]')
            if tag.name == "select" and tag.find("optgroup"):
                outside = [
                    option
                    for option in options
                    if option.find_parent("optgroup") is None and option.get_text(strip=True)
                ]
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        identifier(tag, soup),
                        f"{len(outside)} option(s) restent hors des groupes : vérifier leur appartenance.",
                        "Placer chaque option dans le groupe correspondant à sa catégorie.",
                        node=tag,
                    )
                    if outside
                    else make_outcome(TestStatus.PASS)
                )
            elif len(options) < MIN_OPTIONS_FOR_GROUPING:
                outcomes.append(make_outcome(TestStatus.PASS))
            else:
                pending.append(tag)

        items = [
            RelevanceItem(
                text=_options_text(tag),
                element_html=str(tag)[:200],
                context=label_text(tag, soup),
                details={"type": "listbox ARIA" if tag.name != "select" else "select"},
            )
            for tag in pending
        ]
        verdicts = await judge_relevance(services, "option_grouping", items)
        for tag, verdict in zip(pending, verdicts, strict=True):
            fail = "Les options forment plusieurs catégories qui ne sont pas regroupées avec optgroup."
            if tag.name != "select":
                fail = "Les options forment plusieurs catégories, ce qu'une listbox ARIA ne permet pas de structurer."
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(tag, soup),
                    verdict.message(fail, "La nécessité de regrouper les options reste à vérifier."),
                    "Utiliser un select natif et regrouper les options de même nature avec optgroup.",
                    node=tag,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucune liste de choix.", noun="liste(s)")


class Test1182(RGAATest):
    """11.8.2 : chaque optgroup a-t-il un attribut label ?"""

    test_id = "11.8.2"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.8.2 nécessite un DOM.")
        groups = [tag for tag in soup.find_all("optgroup") if tag.find_parent("select") is not None]
        if not groups:
            return not_applicable(self, "Aucun optgroup.")
        outcomes = [
            make_outcome(TestStatus.PASS)
            if tag.has_attr("label")
            else make_outcome(
                TestStatus.FAIL,
                identifier(tag, soup),
                "L'élément optgroup ne possède pas d'attribut label.",
                "Ajouter un attribut label décrivant ce groupe d'options." + optgroup_example(tag),
                node=tag,
            )
            for tag in groups
        ]
        return build_result(self, outcomes, empty_summary="Aucun optgroup.", noun="groupe(s) d'options")


class Test1183(RGAATest):
    """11.8.3 : le label de chaque optgroup est-il pertinent ?"""

    test_id = "11.8.3"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.8.3 nécessite un DOM.")
        groups = [tag for tag in soup.find_all("optgroup") if tag.has_attr("label")]
        if not groups:
            return not_applicable(self, "Aucun optgroup avec un attribut label.")

        recommendation = "Rédiger un label qui décrit la catégorie commune des options du groupe."
        outcomes = [
            make_outcome(
                TestStatus.FAIL,
                identifier(tag, soup),
                "Le label de l'optgroup est vide.",
                recommendation + optgroup_example(tag),
                node=tag,
            )
            for tag in groups
            if not clean(tag.get("label"))
        ]
        pending = [tag for tag in groups if clean(tag.get("label"))]
        items = [RelevanceItem(text=clean(tag.get("label")), context=_options_text(tag)) for tag in pending]
        verdicts = await judge_relevance(services, "optgroup_label", items)
        for tag, item, verdict in zip(pending, items, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(tag, soup),
                    verdict.message(
                        f"Le label « {item.text[:100]} » ne décrit pas les options du groupe.",
                        f"La pertinence du label « {item.text[:100]} » reste à vérifier.",
                    ),
                    verdict.recommendation(recommendation)
                    + (optgroup_example(tag, verdict.suggestion) if verdict.suggestion else ""),
                    node=tag,
                    label=item.text,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun optgroup avec label.", noun="groupe(s) d'options")

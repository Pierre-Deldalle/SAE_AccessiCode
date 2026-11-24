"""
RGAA 4.1.2 — critère 11.5 : dans chaque formulaire, les champs de même nature
sont-ils regroupés, si nécessaire ?

11.5.1 :
- boutons radio d'une même question (même name) sans fieldset, role="group"
  ou role="radiogroup" commun : non conforme (déterministe) ;
- autres champs hors de tout regroupement : l'IA juge si certains forment un
  ensemble de même nature (adresse, identité, date en plusieurs champs…) qui
  devrait être regroupé.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import (
    common_group,
    field_description,
    fields,
    form_summary,
    group_candidates,
    identifier,
    label_text,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import fieldset_example

RECOMMENDATION = 'Regrouper les champs de même nature dans un fieldset avec legend (ou role="group" avec aria-label).'


def _grouped(field: Tag) -> bool:
    return (
        field.find_parent(lambda node: node.name == "fieldset" or node.get("role") in {"group", "radiogroup"})
        is not None
    )


class Test1151(RGAATest):
    """11.5.1 : les champs de même nature sont-ils regroupés, si nécessaire ?"""

    test_id = "11.5.1"
    criterion_id = "11.5"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.5.1 nécessite un DOM.")

        radio_groups = group_candidates(soup)
        radio_ids = {id(tag) for group in radio_groups for tag in group}
        outcomes = []
        for group in radio_groups:
            if common_group(group) is not None:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(group[0], soup),
                    f"Les {len(group)} boutons radio « {group[0].get('name')} » ne sont pas regroupés.",
                    RECOMMENDATION + fieldset_example(group[0]),
                    node=group[0],
                    name=group[0].get("name"),
                )
            )

        # Champs hors de tout regroupement, par formulaire (au moins deux).
        forms: dict[int, tuple[Tag, list[Tag]]] = {}
        for field in fields(soup):
            if id(field) in radio_ids or _grouped(field):
                continue
            form = field.find_parent("form") or soup
            forms.setdefault(id(form), (form, []))[1].append(field)
        pending = [(form, loose) for form, loose in forms.values() if len(loose) >= 2]

        if not outcomes and not pending:
            return not_applicable(self, "Aucun ensemble de champs susceptible d'être regroupé.")

        items = [
            RelevanceItem(
                text="\n".join(
                    f"- {label_text(field, soup) or field.get('name') or '(sans étiquette)'} "
                    f"[{field_description(field, soup).get('type')}]"
                    for field in loose
                ),
                context=form_summary(form, soup) if isinstance(form, Tag) and form.name == "form" else "",
            )
            for form, loose in pending
        ]
        verdicts = await judge_relevance(services, "field_grouping", items)
        for (form, loose), verdict in zip(pending, verdicts, strict=True):
            problems = getattr(verdict.analysis, "problems", []) if verdict.analysis is not None else []
            target = form if isinstance(form, Tag) and form.name == "form" else loose[0]
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(target, soup),
                    verdict.message(
                        "Des champs de même nature ne sont pas regroupés"
                        + (f" : {' ; '.join(problems)}." if problems else "."),
                        "Des champs de ce formulaire pourraient devoir être regroupés.",
                    ),
                    RECOMMENDATION,
                    node=target,
                    ungrouped_fields=len(loose),
                    **verdict.evidence,
                )
            )
        return build_result(
            self, outcomes, empty_summary="Aucun ensemble de champs à regrouper.", noun="ensemble(s) de champs"
        )

"""
RGAA 4.1.2 — critère 11.6 : dans chaque formulaire, chaque regroupement de
champs de même nature a-t-il une légende ?

11.6.1 (déterministe) :
- un fieldset contient une balise legend non vide ;
- un role="group" ou role="radiogroup" a un aria-label ou aria-labelledby ;
- sans regroupement structurel, chaque champ indique son appartenance au
  groupe par title, aria-label, aria-labelledby ou aria-describedby
  (une simple balise label ne suffit pas).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.forms import (
    clean,
    common_group,
    fields,
    group_candidates,
    group_legend,
    group_tags,
    identifier,
    referenced_text,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import fieldset_example, legend_example


def group_membership_text(field: Tag, soup: BeautifulSoup) -> str:
    """Indication d'appartenance à un groupe portée par le champ lui-même."""
    return clean(
        " ".join(
            [
                clean(field.get("title")),
                clean(field.get("aria-label")),
                referenced_text(field, soup, "aria-labelledby"),
                referenced_text(field, soup, "aria-describedby"),
            ]
        )
    )


class Test1161(RGAATest):
    """11.6.1 : chaque regroupement de champs a-t-il une légende ?"""

    test_id = "11.6.1"
    criterion_id = "11.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.6.1 nécessite un DOM.")

        all_fields = fields(soup)
        groups = [tag for tag in group_tags(soup) if sum(tag in field.parents for field in all_fields) >= 2]
        loose_radios = [group for group in group_candidates(soup) if common_group(group) is None]
        if not groups and not loose_radios:
            return not_applicable(self, "Aucun regroupement de champs.")

        outcomes = []
        for tag in groups:
            if group_legend(tag, soup):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(tag, soup),
                    "Le regroupement de champs n'a pas de légende.",
                    "Ajouter une balise legend au fieldset, ou aria-label / aria-labelledby au groupe ARIA."
                    + legend_example(tag),
                    node=tag,
                    role=tag.get("role") or tag.name,
                )
            )
        for group in loose_radios:
            missing = [field for field in group if not group_membership_text(field, soup)]
            if not missing:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(group[0], soup),
                    f"Les boutons radio « {group[0].get('name')} » ne sont pas regroupés et "
                    f"{len(missing)} n'indiquent pas leur appartenance au groupe.",
                    "Regrouper les champs dans un fieldset avec legend, ou ajouter sur chacun un title, "
                    "aria-label, aria-labelledby ou aria-describedby indiquant le groupe." + fieldset_example(group[0]),
                    node=group[0],
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun regroupement de champs.", noun="regroupement(s)")

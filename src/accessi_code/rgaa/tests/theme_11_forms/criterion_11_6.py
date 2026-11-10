"""RGAA 11.6.1 — présence d'une légende de groupe."""
from __future__ import annotations

from accessi_code.analysis.forms import (
    associated_text,
    common_group,
    fields,
    finding,
    group_candidates,
    group_legend,
    group_tags,
    result,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1161(RGAATest):
    test_id = "11.6.1"
    criterion_id = "11.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [group for group in group_tags(soup)
                      if sum(group in field.parents for field in fields(soup)) >= 2]
        failures, reviews = [], []
        for tag in candidates:
            if not group_legend(tag, soup):
                failures.append(finding(tag, soup, "Regroupement sans légende exploitable.",
                                        "Ajouter un legend au fieldset ou aria-label/aria-labelledby au groupe ARIA.",
                                        role=tag.get("role")))
        for group in group_candidates(soup):
            if common_group(group) is None:
                if not all(associated_text(tag, soup) for tag in group):
                    reviews.append(finding(group[0], soup,
                        "Un groupe radio non structuré n'a pas d'information de groupe démontrée pour chaque champ.",
                        "Fournir un regroupement légendé ou une indication d'appartenance sur chaque champ."))
                else:
                    reviews.append(finding(group[0], soup,
                        "Vérifier que les indications propres à chaque bouton décrivent bien le groupe.",
                        "Contrôler la pertinence des attributs title, aria-label, aria-labelledby ou aria-describedby."))
        return result(self, len(candidates) + len(group_candidates(soup)), failures, reviews)

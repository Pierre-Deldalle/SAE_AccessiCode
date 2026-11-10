"""RGAA 11.7.1 — pertinence des légendes de groupe."""
from __future__ import annotations

from accessi_code.analysis.forms import fields, finding, group_legend, group_tags, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1171(RGAATest):
    test_id = "11.7.1"
    criterion_id = "11.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        tags = [group for group in group_tags(soup)
                if sum(group in field.parents for field in fields(soup)) >= 2]
        failures, reviews = [], []
        for tag in tags:
            label = group_legend(tag, soup)
            if not label:
                # Absence de légende traitée par 11.6 ; pas de pertinence à évaluer ici.
                continue
            reviews.append(finding(tag, soup,
                f"La pertinence sémantique de la légende « {label[:100]} » n'est pas établie par sa seule présence.",
                "Vérifier que la légende décrit la nature des champs du groupe.", legend=label))
        return result(self, len(reviews), failures, reviews)

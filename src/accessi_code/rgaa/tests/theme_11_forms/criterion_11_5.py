"""RGAA 11.5.1 — regroupement des champs de même nature."""
from __future__ import annotations

from accessi_code.analysis.forms import common_group, fields, finding, group_candidates, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1151(RGAATest):
    test_id = "11.5.1"
    criterion_id = "11.5"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        groups = group_candidates(soup)
        failures = []
        for group in groups:
            if common_group(group) is None:
                failures.append(finding(
                    group[0], soup,
                    "Plusieurs boutons radio portant le même nom ne partagent aucun fieldset, role=group ou radiogroup.",
                    "Regrouper les choix de cette question dans un fieldset ou un groupe ARIA.",
                    name=group[0].get("name"), group_size=len(group),
                ))
        # D'autres groupes (identité, adresse, date segmentée...) sont sémantiques.
        # Ne pas conclure PASS pour une page comportant des champs non couverts.
        known = {id(tag) for group in groups for tag in group}
        others = [tag for tag in fields(soup) if id(tag) not in known]
        # Un champ isolé dans son formulaire ne constitue pas un groupe.
        # Plusieurs champs d'un même formulaire peuvent en revanche former
        # un regroupement sémantique non déductible du DOM.
        form_counts = {}
        for tag in others:
            owner = tag.find_parent("form")
            form_counts[id(owner)] = form_counts.get(id(owner), 0) + 1
        ambiguous = [tag for tag in others if form_counts[id(tag.find_parent("form"))] > 1]
        reviews = [finding(
            ambiguous[0], soup,
            "D'autres champs peuvent former des groupes de même nature non identifiables avec certitude par le DOM.",
            "Vérifier les groupes d'identité, d'adresse, de dates segmentées et de cases à cocher.",
            other_fields=len(ambiguous),
        )] if ambiguous else []
        return result(self, len(groups) + len(ambiguous), failures, reviews,
                      metadata={"radio_groups": len(groups), "other_fields": len(others)})

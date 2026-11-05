"""RGAA 11.8 — regroupement et pertinence des groupes d'options."""
from __future__ import annotations

from accessi_code.analysis.forms import clean, finding, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1181(RGAATest):
    test_id = "11.8.1"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        selects = soup.find_all("select")
        listboxes = soup.select('[role="listbox"]')
        failures, reviews = [], []
        for tag in selects:
            groups = tag.find_all("optgroup")
            options = tag.find_all("option")
            if not groups and len(options) >= 2:
                reviews.append(finding(tag, soup,
                    "Vérifier si les options présentent des catégories de même nature nécessitant des optgroup.",
                    "Regrouper les options par optgroup si plusieurs catégories existent."))
            elif groups and any(option.find_parent("optgroup") is None for option in options):
                reviews.append(finding(tag, soup,
                    "Certaines options restent hors des optgroup ; leur appartenance doit être vérifiée.",
                    "Vérifier la structure des catégories et regrouper les options concernées."))
        for tag in listboxes:
            reviews.append(finding(tag, soup,
                "Une listbox ARIA peut nécessiter des groupes d'options impossibles à structurer avec optgroup.",
                "Si les options doivent être regroupées, utiliser un select natif avec optgroup."))
        return result(self, len(selects) + len(listboxes), failures, reviews)


class Test1182(RGAATest):
    test_id = "11.8.2"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        groups = soup.find_all("optgroup")
        failures = [finding(tag, soup,
            "L'élément optgroup ne possède pas d'attribut label.",
            "Ajouter un attribut label décrivant ce groupe d'options.")
            for tag in groups if not tag.has_attr("label")]
        return result(self, len(groups), failures)


class Test1183(RGAATest):
    test_id = "11.8.3"
    criterion_id = "11.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        groups = [tag for tag in soup.find_all("optgroup") if tag.has_attr("label")]
        failures, reviews = [], []
        for tag in groups:
            label = clean(tag.get("label"))
            if not label:
                failures.append(finding(tag, soup, "Le label de l'optgroup est vide.",
                                        "Renseigner une étiquette de catégorie explicite."))
            else:
                reviews.append(finding(tag, soup,
                    f"La pertinence du groupe « {label[:100]} » doit être comparée à ses options.",
                    "Vérifier que le label décrit précisément la catégorie d'options.", label=label))
        return result(self, len(groups), failures, reviews)

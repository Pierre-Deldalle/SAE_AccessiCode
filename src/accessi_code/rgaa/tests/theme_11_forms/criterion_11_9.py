"""RGAA 11.9 — intitulés et nom accessible des boutons de formulaire."""
from __future__ import annotations

from accessi_code.analysis.forms import (button_name, button_visible, buttons, finding,
                                         normalize, result)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1191(RGAATest):
    test_id = "11.9.1"
    criterion_id = "11.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = buttons(soup)
        failures, reviews = [], []
        standard = {"envoyer", "valider", "rechercher", "chercher", "annuler", "retour",
                    "suivant", "continuer", "enregistrer", "supprimer", "ajouter", "submit", "search", "save",
                    "envoyer le message", "envoyer la demande", "envoyer le formulaire"}
        for tag in candidates:
            name = button_name(tag, soup)
            if not name:
                failures.append(finding(tag, soup, "Bouton sans nom accessible exploitable.",
                                        "Fournir un intitulé accessible décrivant l'action du bouton."))
            elif normalize(name) not in standard:
                reviews.append(finding(tag, soup,
                    f"Vérifier que l'intitulé « {name[:100]} » correspond à l'action réelle du bouton.",
                    "Comparer l'intitulé et l'action déclenchée.", accessible_name=name))
        return result(self, len(candidates), failures, reviews)


class Test1192(RGAATest):
    test_id = "11.9.2"
    criterion_id = "11.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = buttons(soup)
        failures, reviews = [], []
        checked = 0
        for tag in candidates:
            visible = button_visible(tag)
            if not visible:
                # Les boutons image nécessitent une preuve du texte visuellement affiché.
                if tag.get("type") == "image":
                    reviews.append(finding(tag, soup,
                        "Le bouton image nécessite une vérification de l'intitulé visuellement affiché.",
                        "Comparer le texte visible de l'image et son nom accessible."))
                    checked += 1
                continue
            checked += 1
            name = button_name(tag, soup)
            if normalize(visible) not in normalize(name):
                # Un CSS externe peut modifier la visibilité ; éviter un faux FAIL.
                reviews.append(finding(tag, soup,
                    f"Le nom accessible « {name} » ne contient pas l'intitulé DOM « {visible} ».",
                    "Confirmer l'intitulé réellement visible, puis l'inclure dans le nom accessible.",
                    visible_text=visible, accessible_name=name))
        return result(self, checked, failures, reviews)

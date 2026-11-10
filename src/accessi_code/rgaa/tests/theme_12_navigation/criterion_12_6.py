"""12.6.1 — zones repérables / évitables, notamment par landmarks."""
from accessi_code.analysis.navigation import finding, result, searches
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest

LANDMARKS = {"header": "banner", "nav": "navigation", "main": "main", "footer": "contentinfo"}


class Test1261(RGAATest):
    test_id = "12.6.1"
    criterion_id = "12.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        zones = [tag for tag in soup.find_all(True) if tag.name in LANDMARKS or
                 tag.get("role") in {"banner", "navigation", "main", "contentinfo", "search"}]
        zones += [tag for tag in searches(soup) if tag not in zones]
        failures, reviews = [], []
        for tag in zones:
            expected = LANDMARKS.get(tag.name)
            role = tag.get("role")
            if expected and role not in (None, expected):
                reviews.append(finding(tag, soup, "Rôle explicite différent du rôle attendu.",
                                       "Vérifier la sémantique et le repérage de cette zone."))
            elif role in {"banner", "navigation", "main", "contentinfo", "search"} or (expected and role is None):
                # Les éléments natifs ont un landmark implicite sous réserve du contexte.
                if tag.name in {"header", "footer"} and tag.find_parent(["article", "section", "aside", "nav", "main"]):
                    reviews.append(finding(tag, soup, "Landmark implicite potentiellement supprimé par l'imbrication.",
                                           "Vérifier le rôle exposé et l'alternative d'évitement."))
            elif tag.find(["h1", "h2", "h3", "h4", "h5", "h6"]):
                continue
            else:
                reviews.append(finding(tag, soup, "Repérage ou évitement de la zone non démontré.",
                                       "Ajouter un landmark adapté, un titre ou un lien d'accès rapide."))
        return result(self, len(zones), failures, reviews)

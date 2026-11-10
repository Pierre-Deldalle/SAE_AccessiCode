"""12.11.1 — accès clavier aux éléments interactifs des contenus additionnels."""
from accessi_code.analysis.navigation import evidence, finding, result
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test12111(RGAATest):
    test_id = "12.11.1"
    criterion_id = "12.11"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        proof = evidence(context, self.test_id)
        panels = proof.get("interactive_additional_contents")
        if panels is None:
            if soup.find_all("script") or soup.find_all("style") or soup.select("[aria-haspopup], [popover], [onmouseover]"):
                return result(self, 1, reviews=[finding(soup.html or soup, soup,
                              "Les contenus révélés au survol/focus ne sont pas inventoriés.",
                              "Tester les composants interactifs révélés et documenter leur accès clavier.")])
            return result(self, 0, empty="Aucun contenu additionnel interactif détecté dans le HTML statique.")
        if not isinstance(panels, list):
            return result(self, 1, reviews=[finding(soup.html or soup, soup,
                          "Preuve non exploitable.", "Fournir une liste de panneaux vérifiés.")])
        failures, reviews = [], []
        for panel in panels:
            value = panel.get("keyboard_reachable") if isinstance(panel, dict) else None
            if value is True:
                continue
            note = finding(soup.html or soup, soup,
                           "Contenu additionnel : accès clavier " + ("impossible." if value is False else "non vérifié."),
                           "Rendre les contrôles internes accessibles avec le clavier.")
            (failures if value is False else reviews).append(note)
        return result(self, len(panels), failures, reviews)

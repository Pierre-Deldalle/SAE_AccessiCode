"""12.10.1 — raccourcis à touche unique : désactivation, modification ou focus."""
from accessi_code.analysis.navigation import evidence, finding, result
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test12101(RGAATest):
    test_id = "12.10.1"
    criterion_id = "12.10"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        proof = evidence(context, self.test_id)
        shortcuts = proof.get("single_key_shortcuts")
        if shortcuts is None:
            if soup.find_all("script") or soup.select("[onkeydown], [onkeypress], [onkeyup]"):
                return result(self, 1, reviews=[finding(soup.html or soup, soup,
                              "Présence de raccourcis à touche unique non déterminée.",
                              "Inspecter les écouteurs clavier et renseigner single_key_shortcuts.")])
            return result(self, 0, empty="Aucun raccourci à touche unique détecté dans le contenu statique.")
        if not isinstance(shortcuts, list):
            return result(self, 1, reviews=[finding(soup.html or soup, soup,
                          "Format de preuve invalide.", "Fournir une liste de raccourcis observés.")])
        failures, reviews = [], []
        for item in shortcuts:
            if not isinstance(item, dict):
                reviews.append(finding(soup.html or soup, soup, "Raccourci non documenté.",
                                       "Fournir les propriétés de contrôle du raccourci."))
                continue
            mechanisms = [item.get(key) for key in ("disable", "remap_with_modifier", "focus_only")]
            if any(value is True for value in mechanisms):
                continue
            note = finding(soup.html or soup, soup, "Raccourci à touche unique sans mécanisme de contrôle prouvé.",
                           "Ajouter désactivation, combinaison modifiée ou activation limitée au focus.",
                           key=item.get("key"))
            (failures if all(value is False for value in mechanisms) else reviews).append(note)
        return result(self, len(shortcuts), failures, reviews)

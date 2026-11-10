"""12.8 — ordre de tabulation et mises à jour dynamiques."""
from accessi_code.analysis.navigation import evidence, finding, proof_check, result
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1281(RGAATest):
    test_id = "12.8.1"
    criterion_id = "12.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        focusable = soup.select("a[href], button, input:not([type=hidden]), select, textarea, [tabindex], [contenteditable]")
        if not focusable:
            return result(self, 0, empty="Aucun élément susceptible de recevoir le focus.")
        failures, reviews = [], []
        for tag in focusable:
            value = tag.get("tabindex")
            if value is not None and value.lstrip("+").isdigit() and int(value) > 0:
                reviews.append(finding(tag, soup, "tabindex positif : ordre de focus à vérifier.",
                                       "Contrôler Tab et Maj+Tab et privilégier l'ordre DOM."))
        f, r = proof_check(context, self, "tab_order_coherent", focusable[0], soup,
                           "Ordre Tab/Maj+Tab")
        return result(self, len(focusable), failures + f, reviews + r)


class Test1282(RGAATest):
    test_id = "12.8.2"
    criterion_id = "12.8"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        scripts = soup.find_all("script")
        triggers = soup.select("[aria-expanded], [aria-controls], [onclick], [popover], dialog")
        if not scripts and not triggers:
            return result(self, 0, empty="Aucun mécanisme de mise à jour dynamique détecté.")
        if evidence(context, self.test_id).get("has_dynamic_focus_changes") is False:
            return result(self, 0, empty="Absence de modification dynamique du focus vérifiée.")
        f, r = proof_check(context, self, "dynamic_tab_order_coherent", triggers[0] if triggers else scripts[0],
                           soup, "Ordre de focus après mise à jour")
        return result(self, max(len(triggers), 1), f, r)

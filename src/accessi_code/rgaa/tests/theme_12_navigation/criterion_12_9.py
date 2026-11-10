"""12.9.1 — absence de piège au clavier."""
from accessi_code.analysis.navigation import proof_check, result
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1291(RGAATest):
    test_id = "12.9.1"
    criterion_id = "12.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        focusable = soup.select("a[href], button, input:not([type=hidden]), select, textarea, [tabindex], [contenteditable]")
        if not focusable:
            return result(self, 0, empty="Aucun élément susceptible de recevoir le focus.")
        f, r = proof_check(context, self, "no_keyboard_trap", focusable[0], soup,
                           "Sortie de chaque composant avec Tab/Maj+Tab ou mécanisme annoncé")
        return result(self, len(focusable), f, r)

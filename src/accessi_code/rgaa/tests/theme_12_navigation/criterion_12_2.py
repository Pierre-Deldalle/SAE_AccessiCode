"""12.2.1 — constance du menu : ordre DOM et position visuelle."""
from accessi_code.analysis.navigation import evidence, finding, navs, pages, proof_check, relative_order, result
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1221(RGAATest):
    test_id = "12.2.1"
    criterion_id = "12.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        all_pages = pages(context)
        if len(all_pages) < 2 or evidence(context, self.test_id).get("home_or_process_or_user_change") is True:
            return result(self, 0, empty="Page unique, accueil ou exception documentée.")
        snapshots = [(soup, navs(soup)) for soup in all_pages.values()]
        if not any(items for _, items in snapshots):
            return result(self, 0, empty="Aucun menu de navigation.")
        failures, reviews = [], []
        if any(len(items) != len(snapshots[0][1]) for _, items in snapshots):
            reviews.append(finding(context.dom.html, context.dom,
                                   "Le nombre de menus varie entre les pages.",
                                   "Vérifier la constance des menus et les exceptions de processus."))
        elif all(items for _, items in snapshots):
            signatures = [tuple(relative_order(soup, tag) for tag in items) for soup, items in snapshots]
            if any(signature != signatures[0] for signature in signatures[1:]):
                failures.append(finding(context.dom.html, context.dom,
                                        "L'ordre relatif des menus varie dans le DOM.",
                                        "Conserver l'ordre relatif des barres de navigation."))
        f, r = proof_check(context, self, "same_visual_position", context.dom.html,
                           context.dom, "Position visuelle des menus")
        return result(self, len(all_pages), failures + f, reviews + r)

"""12.5 — constance de la fonctionnalité de recherche."""
from accessi_code.analysis.navigation import (finding, kind, pages, proof_check,
                                             relative_order, result, search_access)
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class _SearchAccess(RGAATest):
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        all_pages = pages(context)
        if len(all_pages) < 2:
            return result(self, 0, empty="Comparaison entre pages non applicable : page unique.")
        snapshots = [(soup, search_access(soup)) for soup in all_pages.values()]
        if all(tag is None for _, tag in snapshots):
            if context.site_inventory_complete:
                return result(self, 0, empty="Aucun moteur de recherche dans l'ensemble inventorié.")
            return result(self, len(snapshots), reviews=[finding(context.dom.html, context.dom,
                          "Moteur de recherche non identifié.", "Importer l'ensemble des pages.")])
        failures, reviews = [], []
        if any(tag is None for _, tag in snapshots):
            failures.append(finding(context.dom.html, context.dom,
                                    "Moteur de recherche absent sur certaines pages.",
                                    "Conserver le même accès à la recherche."))
        elif self.test_id == "12.5.1":
            if len({kind(tag) for _, tag in snapshots}) != 1:
                failures.append(finding(context.dom.html, context.dom,
                                        "Le type de contrôle d'accès à la recherche varie.",
                                        "Utiliser la même fonctionnalité de recherche."))
        elif self.test_id == "12.5.2":
            f, r = proof_check(context, self, "same_visual_position", context.dom.html,
                               context.dom, "Position visuelle de la recherche")
            failures.extend(f)
            reviews.extend(r)
        else:
            signatures = [relative_order(soup, tag) for soup, tag in snapshots]
            if len(set(signatures)) != 1:
                failures.append(finding(context.dom.html, context.dom,
                                        "L'ordre relatif de la recherche varie dans le DOM.",
                                        "Conserver l'ordre relatif de la recherche."))
        return result(self, len(snapshots), failures, reviews)


class Test1251(_SearchAccess):
    test_id = "12.5.1"
    criterion_id = "12.5"


class Test1252(_SearchAccess):
    test_id = "12.5.2"
    criterion_id = "12.5"


class Test1253(_SearchAccess):
    test_id = "12.5.3"
    criterion_id = "12.5"

"""12.4 — fonctionnalité d'accès au plan du site, identique entre pages."""
from accessi_code.analysis.navigation import (finding, kind, pages, proof_check,
                                             relative_order, result, sitemap_access)
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class _SitemapAccess(RGAATest):
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        all_pages = pages(context)
        if len(all_pages) < 2:
            return result(self, 0, empty="Comparaison entre pages non applicable : page unique.")
        snapshots = [(soup, sitemap_access(soup)) for soup in all_pages.values()]
        if all(tag is None for _, tag in snapshots):
            if context.site_inventory_complete:
                return result(self, 0, empty="Aucun accès au plan du site dans l'ensemble inventorié.")
            return result(self, len(snapshots), reviews=[finding(context.dom.html, context.dom,
                          "Accès au plan du site non identifié.", "Fournir les pages du même ensemble.")])
        failures, reviews = [], []
        if any(tag is None for _, tag in snapshots):
            failures.append(finding(context.dom.html, context.dom,
                                    "Accès au plan du site absent sur certaines pages.",
                                    "Rendre l'accès disponible dans l'ensemble de pages."))
        elif self.test_id == "12.4.1":
            if len({kind(tag) for _, tag in snapshots}) != 1:
                failures.append(finding(context.dom.html, context.dom,
                                        "La nature de la fonctionnalité d'accès varie.",
                                        "Employer le même mécanisme d'accès au plan du site."))
        elif self.test_id == "12.4.2":
            f, r = proof_check(context, self, "same_visual_position", context.dom.html,
                               context.dom, "Position visuelle de l'accès au plan")
            failures.extend(f)
            reviews.extend(r)
        else:
            signatures = [relative_order(soup, tag) for soup, tag in snapshots]
            if len(set(signatures)) != 1:
                failures.append(finding(context.dom.html, context.dom,
                                        "L'ordre relatif de l'accès au plan varie dans le DOM.",
                                        "Conserver le même ordre relatif dans la structure."))
        return result(self, len(snapshots), failures, reviews)


class Test1241(_SitemapAccess):
    test_id = "12.4.1"
    criterion_id = "12.4"


class Test1242(_SitemapAccess):
    test_id = "12.4.2"
    criterion_id = "12.4"


class Test1243(_SitemapAccess):
    test_id = "12.4.3"
    criterion_id = "12.4"

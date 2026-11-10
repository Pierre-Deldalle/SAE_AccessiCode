"""12.1.1 — deux moyens de navigation dans un ensemble de pages."""
from accessi_code.analysis.navigation import (
    evidence,
    finding,
    is_sitemap,
    navs,
    pages,
    result,
    search_access,
    sitemap_access,
)
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class Test1211(RGAATest):
    test_id = "12.1.1"
    criterion_id = "12.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        all_pages = pages(context)
        if len(all_pages) == 1 and context.site_inventory_complete:
            return result(self, 0, empty="Site constitué d'une seule page : non applicable.")
        if evidence(context, self.test_id).get("limited_site") is True or evidence(context, self.test_id).get("process") is True:
            return result(self, 0, empty="Exception documentée : site limité ou processus.")
        soup = context.dom
        menu = any(navs(page) for page in all_pages.values())
        search = any(search_access(page) for page in all_pages.values())
        sitemap = any(is_sitemap(page, key) for key, page in all_pages.items()) or any(
            sitemap_access(page) for page in all_pages.values())
        found = sum([bool(menu), bool(search), bool(sitemap)])
        if found >= 2:
            return result(self, 1, metadata={"menu": menu, "search": search, "sitemap": sitemap})
        note = finding(soup.html or soup, soup, "Deux systèmes de navigation distincts ne sont pas établis.",
                       "Prévoir menu + plan, menu + recherche ou recherche + plan ; inventorier les pages.",
                       menu=menu, search=search, sitemap=sitemap)
        if context.site_inventory_complete:
            return result(self, 1, [note])
        return result(self, 1, reviews=[note])

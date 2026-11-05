"""12.3 — représentativité, fonctionnement et pertinence des liens du plan du site."""
from accessi_code.analysis.navigation import (evidence, finding, is_sitemap,
                                             local_target, pages, result)
from accessi_code.models.capabilities import Capability
from urllib.parse import urlsplit, unquote
from accessi_code.analysis.forms import normalize
from accessi_code.rgaa.base import RGAATest


def sitemap_page(context):
    for key, soup in pages(context).items():
        if is_sitemap(soup, key):
            return key, soup
    return None, None


class _SitemapTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        key, soup = sitemap_page(context)
        if soup is None:
            if context.site_inventory_complete:
                return result(self, 0, empty="Aucune page plan du site dans l'ensemble inventorié.")
            return result(self, 1, reviews=[finding(context.dom.html, context.dom,
                          "La page plan du site n'a pas été fournie.",
                          "Importer le plan du site et les pages associées.")])
        links = soup.find_all("a", href=True)
        failures, reviews = [], []
        if self.test_id == "12.3.1":
            known = pages(context)
            destinations = {link.get("href", "").split("#")[0].split("?")[0].split("/")[-1]
                            for link in links}
            missing = set(known) - {key} - destinations
            if missing and context.site_inventory_complete:
                reviews.append(finding(soup.html or soup, soup,
                                       "Certaines pages ne figurent pas directement au plan ; la couverture indirecte reste à évaluer.",
                                       "Vérifier que le plan représente l'architecture et donne accès aux rubriques.",
                                       missing=sorted(missing)))
            if not context.site_inventory_complete:
                reviews.append(finding(soup.html or soup, soup,
                                       "L'inventaire complet de l'architecture du site est inconnu.",
                                       "Comparer le plan du site à l'architecture réelle."))
            if not links:
                failures.append(finding(soup.html or soup, soup, "Plan du site sans lien.",
                                        "Ajouter des liens vers les rubriques du site."))
            return result(self, 1, failures, reviews)
        for link in links:
            valid = local_target(link.get("href"), key, pages(context), soup)
            if valid is False:
                failures.append(finding(link, soup, "Lien local ou ancre introuvable.",
                                        "Corriger la cible du lien.", href=link.get("href")))
            elif valid is None:
                reviews.append(finding(link, soup, "Destination non vérifiable hors de l'échantillon local.",
                                       "Tester l'URL dans le navigateur ou importer sa cible.", href=link.get("href")))
            if self.test_id == "12.3.3":
                # Une URL existante ne prouve jamais la pertinence de son intitulé.
                verdicts = evidence(context, self.test_id).get("labels_match_destinations", {})
                value = verdicts.get(link.get("href")) if isinstance(verdicts, dict) else None
                if value is False:
                    failures.append(finding(link, soup, "L'intitulé ne décrit pas la destination.",
                                            "Corriger l'intitulé ou la cible du lien."))
                elif value is not True:
                    # Preuve positive seulement si l'intitulé reproduit
                    # exactement un titre ou l'en-tête de la cible locale.
                    parsed = urlsplit(link.get("href", ""))
                    destination = parsed.path.rsplit("/", 1)[-1] or key
                    target = pages(context).get(destination)
                    if target is not None and parsed.fragment:
                        matches = target.find_all(id=unquote(parsed.fragment))
                        target = matches[0] if len(matches) == 1 else None
                    title = normalize(link.get_text(" ", strip=True))
                    if target is not None and title and any(
                        normalize(node.get_text(" ", strip=True)) == title
                        for node in ([target] if getattr(target, "name", None) in
                                     {"h1", "h2", "h3", "h4", "h5", "h6", "title"} else [])
                        + target.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "title"])
                    ):
                        continue
                    reviews.append(finding(link, soup, "Pertinence de l'intitulé non vérifiée.",
                                           "Comparer le lien à la page réellement atteinte."))
        return result(self, len(links), failures, reviews)


class Test1231(_SitemapTest):
    test_id = "12.3.1"
    criterion_id = "12.3"


class Test1232(_SitemapTest):
    test_id = "12.3.2"
    criterion_id = "12.3"


class Test1233(_SitemapTest):
    test_id = "12.3.3"
    criterion_id = "12.3"

"""12.7 — lien d'évitement / accès rapide au contenu principal."""
from accessi_code.analysis.navigation import (evidence, finding, local_target, pages,
                                             proof_check, relative_order, result)
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


def skip_links(soup):
    mains = soup.find_all("main") + soup.find_all(attrs={"role": "main"})
    valid = []
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not href.startswith("#") or len(href) < 2:
            continue
        targets = soup.find_all(id=href[1:])
        if len(targets) == 1 and any(targets[0] is main or targets[0] in main.descendants for main in mains):
            valid.append(link)
    return mains, valid


class Test1271(RGAATest):
    test_id = "12.7.1"
    criterion_id = "12.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        soup = context.dom
        mains, links = skip_links(soup)
        if not mains:
            return result(self, 1, reviews=[finding(soup.html or soup, soup,
                          "Zone main absente ou non identifiée.", "Définir un contenu principal visible et un lien d'accès.")])
        if not links:
            if evidence(context, self.test_id).get("single_page_no_need") is True:
                return result(self, 0, empty="Lien non nécessaire : exception page unique documentée.")
            return result(self, 1, [finding(mains[0], soup, "Aucun lien d'accès rapide local vers main.",
                                            "Ajouter un lien href='#id-du-main' avant la navigation.")])
        all_tags = soup.find_all(True)
        if all_tags.index(links[0]) > all_tags.index(mains[0]):
            return result(self, 1, [finding(links[0], soup, "Le lien est placé après la zone main.",
                                            "Placer le lien d’accès rapide avant le contenu principal.")])
        return result(self, len(links), reviews=[finding(links[0], soup,
                      "Visibilité à la prise de focus non vérifiée.",
                      "Contrôler le lien avec Tab dans un navigateur.")] if
                      evidence(context, self.test_id).get("visible_on_focus") is not True else [])


class Test1272(RGAATest):
    test_id = "12.7.2"
    criterion_id = "12.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context, services=None):
        all_pages = pages(context)
        if len(all_pages) == 1 and evidence(context, self.test_id).get("single_page_no_need") is True:
            return result(self, 0, empty="Exception page unique documentée.")
        failures, reviews = [], []
        signatures = []
        for key, soup in all_pages.items():
            _, links = skip_links(soup)
            if not links:
                failures.append(finding(soup.html or soup, soup,
                                        "Lien d'accès rapide au main manquant.",
                                        "Ajouter un lien d'évitement valide.", page=key))
                continue
            link = links[0]
            signatures.append(relative_order(soup, link))
            if local_target(link.get("href"), key, all_pages, soup) is not True:
                failures.append(finding(link, soup, "Cible du lien invalide.", "Corriger href et id."))
        if len(set(signatures)) > 1:
            failures.append(finding(context.dom.html, context.dom,
                                    "Ordre relatif du lien d'évitement incohérent entre pages.",
                                    "Conserver le même emplacement dans le DOM."))
        for key, label in (("same_visual_position", "Position visuelle"),
                           ("visible_on_focus", "Visibilité au focus"),
                           ("functional", "Fonctionnement clavier")):
            f, r = proof_check(context, self, key, context.dom.html, context.dom, label)
            failures.extend(f)
            reviews.extend(r)
        return result(self, len(all_pages), failures, reviews)

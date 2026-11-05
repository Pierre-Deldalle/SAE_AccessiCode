"""Observations DOM du thème RGAA 12 ; aucune décision RGAA ici.

Les preuves de navigateur / revue fonctionnelle sont explicitement injectées
par l'appelant. Aucune position CSS ni interaction clavier n'est inférée du DOM.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from bs4 import Tag

from accessi_code.analysis.dom import get_element_identifier
from accessi_code.models.result import Finding, TestResult, TestStatus


def pages(context):
    data = dict(getattr(context, "page_doms", None) or {})
    key = context.html_path.name if context.html_path else "index.html"
    if context.dom is not None:
        data[key] = context.dom
    return data


def current_key(context):
    return context.html_path.name if context.html_path else "index.html"


def evidence(context, test_id):
    value = (getattr(context, "navigation_evidence", None) or {}).get(test_id, {})
    return value if isinstance(value, Mapping) else {}


def text(tag):
    return " ".join(tag.get_text(" ", strip=True).split()).casefold()


def navs(soup):
    return [tag for tag in soup.find_all(True) if tag.name == "nav" or tag.get("role") == "navigation"]


def sitemap_links(soup):
    return [tag for tag in soup.find_all("a", href=True) if
            "plan du site" in text(tag) or "sitemap" in tag.get("href", "").casefold() or
            "plan-du-site" in tag.get("href", "").casefold()]


def is_sitemap(soup, key=""):
    title = " ".join(text(tag) for tag in soup.find_all(["title", "h1"]))
    return "plan du site" in title or "sitemap" in key.casefold() or "plan-du-site" in key.casefold()


def searches(soup):
    return [tag for tag in soup.find_all(True) if
            (tag.name == "form" and tag.get("role") == "search") or
            (tag.get("role") == "search" and tag.name != "form") or
            (tag.name == "input" and tag.get("type", "").lower() == "search")]


def search_access(soup):
    found = searches(soup)
    if found:
        return found[0]
    for tag in soup.find_all("a", href=True):
        if "recherche" in text(tag) or "search" in tag.get("href", "").casefold():
            return tag
    return None


def sitemap_access(soup):
    found = sitemap_links(soup)
    return found[0] if found else None


def kind(tag):
    if tag is None:
        return None
    if tag.name == "input":
        return "input:" + str(tag.get("type", "text")).lower()
    return tag.name + (":" + str(tag.get("role")) if tag.get("role") else "")


def structural_position(tag):
    """Signature de position dans la structure, sans déduire la géométrie."""
    if tag is None:
        return None
    parent = tag.parent
    while isinstance(parent, Tag) and parent.name not in {"header", "nav", "main", "footer", "aside", "body"}:
        parent = parent.parent
    region = parent.name if isinstance(parent, Tag) else "document"
    if isinstance(parent, Tag) and parent.get("role"):
        region += ":" + str(parent.get("role"))
    return region


def relative_order(soup, target):
    """Ordre relatif aux grands repères (DOM, non visuel)."""
    if target is None:
        return None
    landmarks = [t for t in soup.find_all(True) if t.name in {"header", "main", "footer", "nav"} or
                 t.get("role") in {"banner", "main", "contentinfo", "navigation"}]
    all_tags = soup.find_all(True)
    target_idx = all_tags.index(target)
    return tuple((t.name, t.get("role"), "before" if all_tags.index(t) < target_idx else
                  "contains" if t is target or target in t.descendants else "after")
                 for t in landmarks if t is not target)


def local_target(href, source_key, known_pages, source_soup):
    """Retourne True/False/None pour un lien local vérifiable / externe inconnu."""
    value = (href or "").strip()
    if not value:
        return False
    if value.startswith(("mailto:", "tel:", "javascript:")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if path:
        # Les fichiers importés sont indexés par nom ; les chemins traversants
        # ou dossiers externes ne sont pas considérés comme des preuves.
        if ".." in PurePosixPath(path).parts:
            return None
        name = PurePosixPath(path).name
        if name not in known_pages:
            return None
        target_soup = known_pages[name]
    else:
        target_soup = source_soup
    if parsed.fragment:
        return len(target_soup.find_all(id=unquote(parsed.fragment))) == 1
    return True


def finding(tag, soup, message, recommendation, **extra):
    try:
        element = get_element_identifier(tag, list(soup.find_all(True)).index(tag))
    except (ValueError, AttributeError):
        element = "document"
    return Finding(element, message, recommendation, evidence=extra)


def result(test, count, failures=None, reviews=None, *, empty="Aucun élément concerné.", metadata=None):
    failures = failures or []
    reviews = reviews or []
    status = (TestStatus.FAIL if failures else TestStatus.NEEDS_REVIEW if reviews else
              TestStatus.PASS if count else TestStatus.NOT_APPLICABLE)
    summary = (f"{count} élément(s) examinés ; {len(failures)} échec(s) démontré(s), "
               f"{len(reviews)} point(s) à vérifier." if count else empty)
    return TestResult(test.test_id, test.criterion_id, status, summary,
                      findings=[*failures, *reviews], tested_elements=count, metadata=metadata or {})


def proof_check(context, test, key, tag, soup, label):
    """Une preuve booléenne documentée : True / False / absence.

    Les booléens doivent venir d'une observation de navigateur ou revue réelle,
    jamais d'une heuristique d'inférence à partir du seul HTML.
    """
    value = evidence(context, test.test_id).get(key)
    if value is True:
        return [], []
    message = f"{label} : " + ("non conforme selon la preuve fournie." if value is False else
                               "preuve de vérification absente.")
    item = finding(tag, soup, message,
                   "Effectuer la vérification réelle et renseigner navigation_evidence.", proof_key=key)
    return ([item], []) if value is False else ([], [item])

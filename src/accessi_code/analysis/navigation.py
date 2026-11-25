"""Observations DOM du thème RGAA 12 ; aucune décision RGAA ici.

Les preuves de navigateur / revue fonctionnelle sont explicitement injectées
par l'appelant. Aucune position CSS ni interaction clavier n'est inférée du DOM.
"""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import get_element_identifier
from accessi_code.analysis.fix_examples import attribute_fix_example
from accessi_code.analysis.location import locate, opening_tag, source_file_name
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
    return [
        tag
        for tag in soup.find_all("a", href=True)
        if "plan du site" in text(tag)
        or "sitemap" in tag.get("href", "").casefold()
        or "plan-du-site" in tag.get("href", "").casefold()
    ]


def is_sitemap(soup, key=""):
    title = " ".join(text(tag) for tag in soup.find_all(["title", "h1"]))
    return "plan du site" in title or "sitemap" in key.casefold() or "plan-du-site" in key.casefold()


def searches(soup):
    return [
        tag
        for tag in soup.find_all(True)
        if (tag.name == "form" and tag.get("role") == "search")
        or (tag.get("role") == "search" and tag.name != "form")
        or (tag.name == "input" and tag.get("type", "").lower() == "search")
    ]


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
    landmarks = [
        t
        for t in soup.find_all(True)
        if t.name in {"header", "main", "footer", "nav"}
        or t.get("role") in {"banner", "main", "contentinfo", "navigation"}
    ]
    all_tags = soup.find_all(True)
    target_idx = all_tags.index(target)
    return tuple(
        (
            t.name,
            t.get("role"),
            "before"
            if all_tags.index(t) < target_idx
            else "contains"
            if t is target or target in t.descendants
            else "after",
        )
        for t in landmarks
        if t is not target
    )


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


def page_file(context, soup):
    """
    Fichier, tel que l'utilisateur l'a fourni, de la page ``soup`` de ``page_doms``.

    None pour la page auditée : le runner la renseigne lui-même.
    """
    if soup is None or soup is context.dom:
        return None
    source = context.workspace_path / "source"
    for key, page in (getattr(context, "page_doms", None) or {}).items():
        if page is not soup:
            continue
        for item in context.files:
            path = Path(item.path)
            try:
                relative = path.relative_to(source).as_posix()
            except ValueError:
                relative = path.name
            if relative == key:
                return source_file_name(context, path)
        return key
    return None


def finding(tag, soup, message, recommendation, *, file=None, **extra):
    """
    Observation sur ``tag`` (élément de ``soup``), avec sa ligne et son extrait HTML.

    ``file`` : fichier de ``soup`` lorsqu'il ne s'agit pas de la page auditée (voir ``page_file``).
    """
    try:
        element = get_element_identifier(tag, list(soup.find_all(True)).index(tag))
    except ValueError, AttributeError:
        element = "document"
    # Le document entier n'a pas de ligne : seul un élément est situé.
    line, snippet = (None, None) if isinstance(tag, BeautifulSoup) else locate(tag)
    return Finding(element, message, recommendation, evidence=extra, line=line, snippet=snippet, file=file)


SKIP_LINK_TEXT = "Aller au contenu principal"

# Éléments qui reçoivent le focus sans tabindex (un lien seulement avec href).
_NATIVELY_FOCUSABLE = frozenset({"area", "button", "input", "select", "summary", "textarea"})

# Champs de formulaire qui ne sont pas des zones de saisie.
_NOT_ENTRIES = frozenset({"hidden", "submit", "button", "reset", "image"})


def _free_id(soup, base):
    """``base``, ou ``base-2``, ``base-3``… si cet id est déjà pris dans la page."""
    candidate, number = base, 1
    while soup.find(id=candidate) is not None:
        number += 1
        candidate = f"{base}-{number}"
    return candidate


def body_start_example(soup, html):
    """Exemple « <body> → <body>html » : ``html`` placé au tout début du corps de la page."""
    body = soup.find("body")
    if body is None:
        return f"placer {html} au tout début de la page"
    return f"{opening_tag(body)} → {opening_tag(body)}{html}"


def skip_link_example(soup, main):
    """
    Exemple d'ajout d'un lien d'évitement vers ``main`` en début de page, avec les vraies valeurs.

    Si ``main`` n'a pas d'id, l'exemple lui en donne un (« contenu », ou une variante libre).
    """
    if not isinstance(main, Tag):
        return None
    target = str(main.get("id") or "").strip()
    parts = []
    if not target:
        target = _free_id(soup, "contenu")
        parts.append(attribute_fix_example(main, set_attributes={"id": target}))
    parts.append(body_start_example(soup, f'<a href="#{escape(target)}">{SKIP_LINK_TEXT}</a>'))
    return " ; ".join(parts)


def search_zone_example(field):
    """
    Exemple pour signaler un champ de recherche comme zone de recherche : ``role="search"``
    sur son formulaire, ou un conteneur ``<div role="search">`` s'il n'en a pas.

    None si le champ est déjà dans une zone de recherche, ou si son formulaire contient
    d'autres champs (formulaire de contact…) : en faire une zone de recherche serait faux.
    """
    if not isinstance(field, Tag) or field.find_parent(attrs={"role": "search"}) or field.find_parent("search"):
        return None
    form = field.find_parent("form")
    if form is None:
        return f'{opening_tag(field)} → <div role="search">{opening_tag(field)}</div>'
    entries = [
        tag
        for tag in form.find_all(["input", "select", "textarea"])
        if str(tag.get("type", "")).lower() not in _NOT_ENTRIES
    ]
    if entries != [field]:
        return None
    return attribute_fix_example(form, set_attributes={"role": "search"})


def positive_tabindex_example(tag):
    """
    Exemple pour rendre à un élément sa place dans l'ordre du code : ``tabindex`` retiré
    s'il reçoit le focus sans lui, sinon ramené à ``0``.
    """
    if not isinstance(tag, Tag):
        return None
    native = tag.name in _NATIVELY_FOCUSABLE or (tag.name == "a" and tag.get("href") is not None)
    if native:
        return attribute_fix_example(tag, remove_attributes=["tabindex"])
    return attribute_fix_example(tag, set_attributes={"tabindex": "0"})


def result(test, count, failures=None, reviews=None, *, empty="Aucun élément concerné.", metadata=None):
    failures = failures or []
    reviews = reviews or []
    status = (
        TestStatus.FAIL
        if failures
        else TestStatus.NEEDS_REVIEW
        if reviews
        else TestStatus.PASS
        if count
        else TestStatus.NOT_APPLICABLE
    )
    summary = (
        f"{count} élément(s) examinés ; {len(failures)} échec(s) démontré(s), {len(reviews)} point(s) à vérifier."
        if count
        else empty
    )
    return TestResult(
        test.test_id,
        test.criterion_id,
        status,
        summary,
        findings=[*failures, *reviews],
        tested_elements=count,
        metadata=metadata or {},
    )


def proof_check(context, test, key, tag, soup, label):
    """Une preuve booléenne documentée : True / False / absence.

    Les booléens doivent venir d'une observation de navigateur ou revue réelle,
    jamais d'une heuristique d'inférence à partir du seul HTML.
    """
    value = evidence(context, test.test_id).get(key)
    if value is True:
        return [], []
    message = f"{label} : " + (
        "non conforme selon la preuve fournie." if value is False else "preuve de vérification absente."
    )
    item = finding(
        tag, soup, message, "Effectuer la vérification réelle et renseigner navigation_evidence.", proof_key=key
    )
    return ([item], []) if value is False else ([], [item])


# Extensions considérées comme des pages du site (les autres liens visent des ressources).
_PAGE_SUFFIXES = {"", ".html", ".htm"}


def linked_page_keys(source_key, soup):
    """
    Chemins (relatifs à la racine de l'audit) des pages HTML internes liées depuis ``soup``.

    Les liens externes, mailto:, tel:, javascript: et les ancres de la page
    elle-même sont ignorés. Un lien qui sort de la racine donne ``None`` :
    l'inventaire ne peut alors pas être prouvé complet.
    """
    base = PurePosixPath(source_key).parent
    targets = []
    for tag in soup.find_all(["a", "area"], href=True):
        value = (tag.get("href") or "").strip()
        if not value or value.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        path = PurePosixPath(unquote(parsed.path))
        if path.suffix.lower() not in _PAGE_SUFFIXES:
            continue
        parts = [] if path.is_absolute() else list(base.parts)
        for part in path.parts:
            if part in {"/", "."}:
                continue
            if part == "..":
                if not parts:
                    targets.append(None)
                    break
                parts.pop()
            else:
                parts.append(part)
        else:
            resolved = "/".join(parts)
            if value.endswith("/") or not path.suffix:
                resolved = f"{resolved}/index.html" if resolved else "index.html"
            targets.append(resolved)
    return targets


def is_site_inventory_complete(page_doms):
    """
    True si chaque page HTML interne liée depuis les pages importées a elle-même été importée.

    Ne regarde que les liens présents dans le HTML : c'est une preuve
    d'inventaire de l'ensemble fourni, pas d'un site distant.
    """
    if not page_doms:
        return False
    known = set(page_doms)
    for key, soup in page_doms.items():
        if soup is None:
            return False
        for target in linked_page_keys(key, soup):
            if target is None or target not in known:
                return False
    return True

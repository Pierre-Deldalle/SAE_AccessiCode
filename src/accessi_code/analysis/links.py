"""
Observations DOM sur les liens (thème RGAA 6).

Repère les liens (HTML, role="link", zones de carte, liens SVG), les classe
selon le test du critère 6.1 qui les concerne, calcule une approximation de
leur nom accessible et extrait leur contexte au sens du RGAA. Aucune décision
RGAA n'est prise ici.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.dom import get_labelledby_text
from accessi_code.analysis.structure import HEADING_TAGS, is_hidden
from accessi_code.analysis.tables import associated_headers

IMAGE_TAGS = frozenset({"img", "svg", "object", "canvas"})
SVG_HREF_ATTRIBUTES = (
    "href",
    "xlink:href",
    "xlink-href",
    "xlink_href",
    "{http://www.w3.org/1999/xlink}href",
)
_SKIPPED_TAGS = frozenset({"script", "style", "template"})

# Types de liens, un par test du critère 6.1.
TEXT_LINK = "text"
IMAGE_LINK = "image"
COMPOSITE_LINK = "composite"
SVG_LINK = "svg"


def normalize(value: str) -> str:
    return " ".join(value.split())


def _is_aria_hidden(element: Tag) -> bool:
    return str(element.get("aria-hidden", "")).strip().lower() == "true"


# ----------------------------------------------------------------------
# Repérage
# ----------------------------------------------------------------------


def is_svg_link(element: Tag) -> bool:
    """Élément <a> interne à un SVG portant un href (ou xlink:href)."""
    return (
        element.name == "a"
        and element.find_parent("svg") is not None
        and any(element.has_attr(attribute) for attribute in SVG_HREF_ATTRIBUTES)
    )


def is_html_link(element: Tag) -> bool:
    """Lien HTML (a[href] sans autre rôle) ou élément role="link", hors SVG."""
    role = str(element.get("role", "")).strip().lower()
    if role == "link":
        return element.find_parent("svg") is None or element.name != "a"
    return element.name == "a" and element.has_attr("href") and role == "" and element.find_parent("svg") is None


def is_image_element(element: Tag) -> bool:
    return element.name in IMAGE_TAGS or str(element.get("role", "")).strip().lower() == "img"


def link_href(link: Tag) -> str | None:
    """Destination du lien (href ou xlink:href pour SVG 1.1)."""
    for attribute in SVG_HREF_ATTRIBUTES:
        if link.has_attr(attribute):
            value = link.get(attribute)
            return "" if value is None else str(value)
    return None


def link_images(link: Tag) -> list[Tag]:
    """Images de premier niveau contenues dans le lien (le contenu d'un SVG n'est pas recompté)."""
    images = []
    for node in link.descendants:
        if not isinstance(node, Tag) or not is_image_element(node):
            continue
        if any(isinstance(parent, Tag) and is_image_element(parent) for parent in node.parents if parent is not link):
            continue
        images.append(node)
    return images


def text_outside_images(link: Tag) -> str:
    """Texte du lien hors images, hors contenus masqués."""
    parts: list[str] = []
    for node in link.descendants:
        if not isinstance(node, NavigableString) or not isinstance(node.parent, Tag):
            continue
        ignored = False
        for ancestor in [node.parent, *node.parent.parents]:
            if ancestor is link.parent:
                break
            if not isinstance(ancestor, Tag):
                continue
            if (
                is_image_element(ancestor)
                or ancestor.name in _SKIPPED_TAGS
                or ancestor.has_attr("hidden")
                or _is_aria_hidden(ancestor)
            ):
                ignored = True
                break
        if not ignored:
            parts.append(str(node))
    return normalize(" ".join(parts))


def visible_text(link: Tag) -> str:
    """Texte du lien, textes de SVG compris, hors contenus masqués (intitulé visible)."""
    parts: list[str] = []
    for node in link.descendants:
        if not isinstance(node, NavigableString) or not isinstance(node.parent, Tag):
            continue
        ignored = False
        for ancestor in [node.parent, *node.parent.parents]:
            if ancestor is link.parent:
                break
            if not isinstance(ancestor, Tag):
                continue
            if ancestor.name in _SKIPPED_TAGS or ancestor.has_attr("hidden") or _is_aria_hidden(ancestor):
                ignored = True
                break
        if not ignored:
            parts.append(str(node))
    return normalize(" ".join(parts))


def svg_text(link: Tag) -> str:
    """Textes SVG (<text>, et <tspan> hors <text>) d'un lien SVG."""
    parts = [
        normalize(item.get_text(" ", strip=True))
        for item in link.find_all("text")
        if not item.has_attr("hidden") and not _is_aria_hidden(item)
    ]
    parts += [
        normalize(item.get_text(" ", strip=True)) for item in link.find_all("tspan") if item.find_parent("text") is None
    ]
    return normalize(" ".join(part for part in parts if part))


def link_kind(link: Tag) -> str | None:
    """
    Test du critère 6.1 dont relève le lien :
    texte seul (6.1.1), image seule (6.1.2), texte et image (6.1.3), lien SVG (6.1.4).
    """
    if is_svg_link(link):
        return SVG_LINK
    if link.name == "area":
        return IMAGE_LINK if link.has_attr("href") else None
    if not is_html_link(link):
        return None
    if not link_images(link):
        return TEXT_LINK
    return COMPOSITE_LINK if text_outside_images(link) else IMAGE_LINK


def page_links(soup: BeautifulSoup) -> list[Tag]:
    """Tous les liens de la page, exposés aux technologies d'assistance, dans l'ordre du DOM."""
    return [node for node in soup.find_all(True) if link_kind(node) is not None and not is_hidden(node)]


# ----------------------------------------------------------------------
# Intitulé (approximation du nom accessible)
# ----------------------------------------------------------------------


def image_alternative(image: Tag, soup: BeautifulSoup) -> str:
    """Alternative textuelle d'une image (aria-labelledby, aria-label, alt, title SVG, contenu de repli, title)."""
    valid, text = get_labelledby_text(image, soup)
    if valid:
        return normalize(text)
    for attribute in ("aria-label", "alt"):
        value = normalize(str(image.get(attribute, "")))
        if value:
            return value
    if image.name == "svg":
        title = image.find("title", recursive=False)
        if isinstance(title, Tag) and normalize(title.get_text(" ", strip=True)):
            return normalize(title.get_text(" ", strip=True))
    if image.name in {"object", "canvas"}:
        fallback = normalize(image.get_text(" ", strip=True))
        if fallback:
            return fallback
    return normalize(str(image.get("title", "")))


def link_content(link: Tag, soup: BeautifulSoup) -> str:
    """Contenu du lien dans l'ordre du DOM : textes et alternatives des images."""
    parts: list[str] = []

    def visit(node: Tag) -> None:
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag):
                if child.name in _SKIPPED_TAGS or child.has_attr("hidden") or _is_aria_hidden(child):
                    continue
                if is_image_element(child):
                    parts.append(f" {image_alternative(child, soup)} ")
                    continue
                visit(child)

    visit(link)
    return normalize(" ".join(parts))


def _svg_link_name(link: Tag) -> tuple[str, str]:
    text = svg_text(link)
    if text:
        return text, "svg_text"
    title = link.find("title", recursive=False)
    if isinstance(title, Tag) and normalize(title.get_text(" ", strip=True)):
        return normalize(title.get_text(" ", strip=True)), "svg_title"
    xlink_title = normalize(str(link.get("xlink:title", link.get("xlink-title", ""))))
    if xlink_title:
        return xlink_title, "xlink_title"
    return "", "none"


def accessible_name(link: Tag, soup: BeautifulSoup) -> tuple[str, str]:
    """
    Intitulé du lien et son origine : aria-labelledby, aria-label, contenu
    (textes et alternatives des images), puis title. Une référence
    aria-labelledby invalide est ignorée, comme le fait le navigateur.
    """
    valid, text = get_labelledby_text(link, soup)
    if valid and normalize(text):
        return normalize(text), "aria-labelledby"
    aria_label = normalize(str(link.get("aria-label", "")))
    if aria_label:
        return aria_label, "aria-label"
    if is_svg_link(link):
        name, source = _svg_link_name(link)
    elif link.name == "area":
        name, source = normalize(str(link.get("alt", ""))), "alt"
    else:
        name, source = link_content(link, soup), "content"
    if name:
        return name, source
    title = normalize(str(link.get("title", "")))
    if title:
        return title, "title"
    return "", "none"


# ----------------------------------------------------------------------
# Contexte du lien (glossaire RGAA)
# ----------------------------------------------------------------------


def link_context(link: Tag, limit: int = 600) -> str:
    """
    Contexte du lien au sens du RGAA : paragraphe, item de liste (et item
    parent), cellule de tableau et ses en-têtes, titre de la section.
    """
    anchor = link.find_parent("svg") if is_svg_link(link) else link
    anchor = anchor if isinstance(anchor, Tag) else link
    parts: list[str] = []

    paragraph = anchor.find_parent("p")
    if isinstance(paragraph, Tag):
        parts.append(f"Paragraphe : {normalize(paragraph.get_text(' ', strip=True))}")

    item = anchor.find_parent("li")
    if isinstance(item, Tag):
        parts.append(f"Élément de liste : {normalize(item.get_text(' ', strip=True))}")
        parent_item = item.find_parent("li")
        if isinstance(parent_item, Tag):
            own = parent_item.find(string=True, recursive=False)
            label = normalize(str(own or "")) or normalize(parent_item.get_text(" ", strip=True))[:100]
            parts.append(f"Élément de liste parent : {label}")

    cell = anchor.find_parent(["td", "th"])
    if isinstance(cell, Tag):
        table = cell.find_parent("table")
        headers = associated_headers(table, cell) if isinstance(table, Tag) else []
        header_text = ", ".join(normalize(header.get_text(" ", strip=True)) for header in headers)
        parts.append(
            f"Cellule : {normalize(cell.get_text(' ', strip=True))}"
            + (f" (en-têtes : {header_text})" if header_text else "")
        )

    heading = anchor.find_previous(list(HEADING_TAGS))
    if isinstance(heading, Tag):
        parts.append(f"Titre de la section : {normalize(heading.get_text(' ', strip=True))}")

    return " — ".join(part for part in parts if not part.endswith(": "))[:limit]


def link_identifier(link: Tag, index: int) -> str:
    """Identifiant lisible d'un lien dans les observations."""
    element_id = link.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return f"{link.name}#{element_id.strip()}"
    if is_svg_link(link):
        return f"svg a[index={index}]"
    return f"{link.name}[index={index}]"

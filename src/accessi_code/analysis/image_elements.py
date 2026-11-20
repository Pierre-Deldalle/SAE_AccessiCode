"""
Inventaire des éléments graphiques d'une page pour le thème RGAA 1.

Chaque élément concerné par le thème 1 (img, role="img", area, input image,
object, embed, svg, canvas) est décrit une seule fois : alternatives textuelles,
marquage décoratif, légende, descriptions détaillées, fichier image exploitable.

Ce module est déterministe et ne décide d'aucun statut RGAA.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.images import (
    DetailedDescription,
    ImageInfo,
    ResourceLoader,
    get_adjacent_description,
    get_referenced_descriptions,
    resolve_image_source,
)

ImageKind = Literal["img", "role_img", "area", "input", "object", "embed", "svg", "canvas"]

ALL_KINDS: tuple[ImageKind, ...] = ("img", "role_img", "area", "input", "object", "embed", "svg", "canvas")

# Éléments natifs qui ne relèvent pas de la catégorie role="img" générique.
_NATIVE_TAGS = {"img", "area", "input", "object", "embed", "svg", "canvas"}

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif", ".ico")

_CONTEXT_CONTAINERS = ("figure", "p", "li", "td", "th", "dd", "section", "article", "aside", "header", "footer")
_CONTEXT_LIMIT = 600

# Alternative qui annonce une description détaillée placée à côté de l'image.
_DESCRIPTION_REFERENCE = re.compile(
    r"ci-dessous|ci-après|ci-contre|ci-dessus|description détaillée|décrit(e)? (plus bas|ci)|détail(s)? (plus bas|ci)",
    re.IGNORECASE,
)

_CAPTCHA_MARKER = re.compile(r"captcha|image[- ]?test|code de sécurité|code de securite", re.IGNORECASE)

_LOGO_MARKER = re.compile(r"\blogo", re.IGNORECASE)


@dataclass
class ImageElement:
    """Élément graphique de la page, avec ses informations utiles au thème 1."""

    tag: Tag
    kind: ImageKind
    # Identifiant stable dans le document (clé de context.image_evidence).
    key: str

    # Alternatives non vides, par source : alt, title, aria-label,
    # aria-labelledby, svg-title, content (contenu entre les balises).
    alternatives: dict[str, str] = field(default_factory=dict)
    # Référence aria-labelledby présente mais vide ou cassée.
    broken_labelledby: bool = False

    has_empty_alt: bool = False
    aria_hidden: bool = False
    presentation_role: bool = False
    has_role_img: bool = False

    # Image contenue dans un lien ou un bouton, ou bouton image.
    functional: bool = False
    captcha_marker: bool = False
    logo_marker: bool = False

    figure: Tag | None = None
    figcaption: Tag | None = None

    descriptions: list[DetailedDescription] = field(default_factory=list)
    # L'alternative annonce une description adjacente (« voir ci-dessous »…).
    alternative_references_description: bool = False

    context_text: str = ""
    image_info: ImageInfo | None = None

    @property
    def html(self) -> str:
        return str(self.tag)[:1500]

    @property
    def marked_decorative(self) -> bool:
        """Le code déclare l'image décorative (alt vide seul, aria-hidden ou role=presentation)."""
        if self.aria_hidden or self.presentation_role:
            return True
        return self.has_empty_alt and not self.alternatives

    @property
    def has_caption(self) -> bool:
        return self.figcaption is not None and bool(self.figcaption.get_text(" ", strip=True))

    @property
    def available_descriptions(self) -> list[DetailedDescription]:
        return [description for description in self.descriptions if description.available and description.content]

    def alternatives_text(self) -> str:
        """Alternatives présentées sous la forme « source : texte », une par ligne."""
        return "\n".join(f"{source} : {text}" for source, text in self.alternatives.items())


def find_image_elements(
    soup: BeautifulSoup,
    *,
    base_dir: str | Path | None = None,
    resource_loader: ResourceLoader | None = None,
) -> list[ImageElement]:
    """Tous les éléments graphiques du document, dans l'ordre du document."""
    elements: list[ImageElement] = []
    counters: dict[str, int] = {}
    ids = _id_counts(soup)

    for tag in soup.find_all(True):
        kind = image_kind(tag)
        if kind is None:
            continue
        element = _build_element(tag, kind, soup, base_dir, resource_loader)
        element.key = _stable_key(tag, counters, ids)
        elements.append(element)

    return elements


def image_kind(tag: Tag) -> ImageKind | None:
    """Catégorie RGAA de l'élément, ou None s'il n'est pas concerné par le thème 1."""
    name = tag.name
    if name == "img":
        return "img"
    if name == "area":
        return "area"
    if name == "input":
        return "input" if _attr(tag, "type").lower() == "image" else None
    if name == "object":
        return "object" if _is_image_resource(tag, "data") else None
    if name == "embed":
        return "embed" if _is_image_resource(tag, "src") else None
    if name == "svg":
        # Les svg imbriqués font partie de l'image parente.
        return None if tag.find_parent("svg") else "svg"
    if name == "canvas":
        return "canvas"
    if name not in _NATIVE_TAGS and _attr(tag, "role").lower() == "img":
        return "role_img"
    return None


def referenced_text(tag: Tag, soup: BeautifulSoup, attribute: str) -> tuple[str, bool]:
    """
    Texte des éléments référencés par un attribut d'identifiants (aria-labelledby…).

    Retourne (texte, valide) : valide est faux si une référence est absente,
    dupliquée ou vide.
    """
    value = _attr(tag, attribute)
    if not value:
        return "", True
    texts: list[str] = []
    valid = True
    for identifier in value.split():
        matches = soup.find_all(id=identifier)
        if len(matches) != 1:
            valid = False
            continue
        text = _text(matches[0])
        if not text:
            valid = False
            continue
        texts.append(text)
    return " ".join(texts), valid and bool(texts)


def is_alternative_reference(text: str) -> bool:
    """L'alternative annonce-t-elle une description détaillée adjacente ?"""
    return bool(_DESCRIPTION_REFERENCE.search(text or ""))


def svg_has_only_real_text(tag: Tag) -> bool:
    """Un svg dont le texte est entièrement composé d'éléments <text> (sans tracés ni images)."""
    return bool(tag.find("text")) and not tag.find(["path", "image", "use", "polygon"])


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------


def _build_element(
    tag: Tag,
    kind: ImageKind,
    soup: BeautifulSoup,
    base_dir: str | Path | None,
    resource_loader: ResourceLoader | None,
) -> ImageElement:
    element = ImageElement(tag=tag, kind=kind, key="")

    alt_attr = tag.get("alt")
    element.has_empty_alt = isinstance(alt_attr, str) and not alt_attr.strip()

    for source in ("alt", "title", "aria-label"):
        value = _attr(tag, source)
        if value:
            element.alternatives[source] = value

    labelledby, valid = referenced_text(tag, soup, "aria-labelledby")
    if labelledby:
        element.alternatives["aria-labelledby"] = labelledby
    element.broken_labelledby = bool(_attr(tag, "aria-labelledby")) and not valid

    if kind == "svg":
        title = tag.find("title", recursive=False)
        if isinstance(title, Tag) and _text(title):
            element.alternatives["svg-title"] = _text(title)
    if kind in {"object", "canvas"}:
        content = _text(tag)
        if content:
            element.alternatives["content"] = content

    element.aria_hidden = _attr(tag, "aria-hidden").lower() == "true"
    element.presentation_role = _attr(tag, "role").lower() in {"presentation", "none"}
    element.has_role_img = _attr(tag, "role").lower() == "img"

    element.functional = kind == "input" or (kind != "area" and tag.find_parent(["a", "button"]) is not None)
    if kind == "area":
        element.functional = bool(_attr(tag, "href"))

    markers = " ".join(
        _attr(tag, name) for name in ("id", "class", "src", "data", "name", "alt", "title", "aria-label")
    )
    element.captcha_marker = bool(_CAPTCHA_MARKER.search(markers))
    element.logo_marker = bool(_LOGO_MARKER.search(markers)) or _is_home_link_in_header(tag)

    figure = tag.find_parent("figure")
    if isinstance(figure, Tag):
        element.figure = figure
        caption = figure.find("figcaption", recursive=False)
        element.figcaption = caption if isinstance(caption, Tag) else None

    element.context_text = _context(tag)
    element.image_info = _image_info(tag, kind, base_dir, element.context_text)
    element.descriptions = _descriptions(tag, kind, soup, resource_loader)
    element.alternative_references_description = any(
        is_alternative_reference(text) for text in element.alternatives.values()
    )

    return element


def _descriptions(
    tag: Tag,
    kind: ImageKind,
    soup: BeautifulSoup,
    resource_loader: ResourceLoader | None,
) -> list[DetailedDescription]:
    """
    Descriptions détaillées associées à l'élément (RGAA 1.6 / 1.7).

    La légende (figcaption) n'est pas une description détaillée : elle relève de 1.9.
    """
    descriptions: list[DetailedDescription] = []

    longdesc = _attr(tag, "longdesc")
    if kind == "img" and longdesc:
        descriptions.append(_load_longdesc(longdesc, resource_loader))

    adjacent = get_adjacent_description(tag, soup, page_url=None, resource_loader=resource_loader)
    if adjacent is not None:
        descriptions.append(adjacent)

    descriptions.extend(get_referenced_descriptions(tag, soup))

    if kind == "svg":
        desc = tag.find("desc", recursive=False)
        if isinstance(desc, Tag) and _text(desc):
            descriptions.append(DetailedDescription(source="svg-desc", content=_text(desc), reference="desc"))

    if kind in {"svg", "canvas", "role_img"}:
        ids = _attr(tag, "aria-labelledby").split()
        if len(ids) >= 2:
            texts = [_text(soup.find(id=identifier)) for identifier in ids[1:] if soup.find(id=identifier)]
            content = " ".join(text for text in texts if text)
            descriptions.append(
                DetailedDescription(
                    source="aria-labelledby",
                    content=content,
                    reference=" ".join(ids[1:]),
                    available=bool(content),
                    error=None if content else "Le second passage référencé par aria-labelledby est vide.",
                )
            )

    if kind == "canvas":
        content = _text(tag)
        # Un contenu long entre les balises fait office de description détaillée (1.6.7).
        if len(content) > 150:
            descriptions.append(DetailedDescription(source="canvas-content", content=content, reference="canvas"))

    return descriptions


def _load_longdesc(reference: str, resource_loader: ResourceLoader | None) -> DetailedDescription:
    if reference.startswith("#"):
        return DetailedDescription(
            source="longdesc", content="", reference=reference, available=False, error="Ancre longdesc non résolue."
        )
    if resource_loader is None:
        return DetailedDescription(
            source="longdesc", content="", reference=reference, available=False, error="Ressource longdesc non chargée."
        )
    try:
        content = resource_loader(reference).strip()
    except Exception as error:
        return DetailedDescription(
            source="longdesc", content="", reference=reference, available=False, error=str(error)
        )
    return DetailedDescription(
        source="longdesc",
        content=content,
        reference=reference,
        available=bool(content),
        error=None if content else "Ressource longdesc vide.",
    )


def _image_info(tag: Tag, kind: ImageKind, base_dir: str | Path | None, context: str) -> ImageInfo | None:
    """ImageInfo si un fichier image est référencé (img, input, object, embed)."""
    attribute = {"img": "src", "input": "src", "object": "data", "embed": "src"}.get(kind)
    if attribute is None:
        return None
    src = _attr(tag, attribute)
    if not src:
        return None
    image_path, image_data = resolve_image_source(src, base_dir)
    alt = tag.get("alt")
    return ImageInfo(
        src=src,
        alt=alt if isinstance(alt, str) else None,
        element_html=str(tag)[:1500],
        context_text=context,
        image_path=image_path,
        image_data=image_data,
    )


def has_image_file(element: ImageElement) -> bool:
    """L'image peut-elle être transmise au VLM (fichier local existant ou données intégrées) ?"""
    info = element.image_info
    if info is None:
        return False
    if info.image_data:
        return True
    return bool(info.image_path) and Path(info.image_path).is_file()


def _is_image_resource(tag: Tag, attribute: str) -> bool:
    mime = _attr(tag, "type").lower()
    if mime:
        return mime.startswith("image/")
    return _attr(tag, attribute).lower().split("?")[0].endswith(_IMAGE_EXTENSIONS)


def _is_home_link_in_header(tag: Tag) -> bool:
    link = tag.find_parent("a")
    if not isinstance(link, Tag):
        return False
    in_header = link.find_parent("header") is not None or link.find_parent(attrs={"role": "banner"}) is not None
    if not in_header:
        return False
    return _attr(link, "href").strip() in {"/", "./", "index.html", "/index.html", "./index.html"}


def _context(tag: Tag) -> str:
    container = tag.find_parent(_CONTEXT_CONTAINERS) or tag.parent
    text = _text(container) if isinstance(container, Tag) else ""
    return text[:_CONTEXT_LIMIT]


def _stable_key(tag: Tag, counters: dict[str, int], ids: dict[str, int]) -> str:
    """« img#logo » si l'id est unique, sinon « img[n] » (rang parmi les balises de même nom)."""
    index = counters.get(tag.name, 0)
    counters[tag.name] = index + 1
    identifier = _attr(tag, "id")
    if identifier and ids.get(identifier) == 1:
        return f"{tag.name}#{identifier}"
    return f"{tag.name}[{index}]"


def _id_counts(soup: BeautifulSoup) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tag in soup.find_all(id=True):
        value = _attr(tag, "id")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _attr(tag: Tag, name: str) -> str:
    value = tag.get(name)
    if isinstance(value, list):
        value = " ".join(value)
    return " ".join(str(value).split()) if value is not None else ""


def _text(tag: Tag | None) -> str:
    if not isinstance(tag, Tag):
        return ""
    return " ".join(tag.get_text(" ", strip=True).split())

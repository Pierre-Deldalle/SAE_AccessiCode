"""
Contenus cryptiques (RGAA 13.5, 13.6) : art ASCII, émoticônes et syntaxe cryptique.

Seules les formes reconnaissables sans ambiguïté sont repérées :
- émoticônes textuelles isolées (« :-) », « ;) », « <3 », « ^^ », « xD »…) ;
- art ASCII : bloc de plusieurs lignes composé surtout de symboles ;
- syntaxe cryptique de type SMS (« @+ », « 2m1 », « tkt »…).

Les sigles et abréviations (PDF, TTC, SNCF…) ne sont pas des contenus
cryptiques au sens du RGAA 4.1 et ne sont pas repérés.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.components import normalize

_SKIPPED = frozenset({"script", "style", "template", "noscript", "code", "kbd", "samp", "var", "title", "head"})
_INLINE = frozenset({"span", "abbr", "acronym", "em", "strong", "b", "i", "small", "mark", "a", "q", "cite", "bdi"})
_BLOCKS = (
    "p",
    "li",
    "td",
    "th",
    "dd",
    "dt",
    "figcaption",
    "caption",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "label",
    "legend",
    "button",
    "div",
    "section",
    "article",
    "body",
)

_BOUNDARY_BEFORE = r"(?:(?<=^)|(?<=[\s(«\"]))"
_BOUNDARY_AFTER = r"(?=$|[\s.,!?;…)»\"])"
EMOTICON = re.compile(
    _BOUNDARY_BEFORE
    + r"(?:[:;=][-'^o]?[)(\]\[DPpOo|/\\*$@3]+|:'[-]?\(|<3+|\^\^|\^_\^|-_-|o_O|O_o|T_T|x[D]+|X[D]+)"
    + _BOUNDARY_AFTER
)
CRYPTIC_SYNTAX = re.compile(
    _BOUNDARY_BEFORE + r"(?:@\+|a2m1|2m1|tkt|mdr|ptdr|jtm|bjr|slt|dsl|k7|g\s+fr[eé])" + _BOUNDARY_AFTER,
    re.IGNORECASE,
)
_SYMBOLS = re.compile(r"[^\w\s]")

EMOTICON_KIND = "émoticône"
ASCII_ART_KIND = "art ASCII"
SYNTAX_KIND = "syntaxe cryptique"


@dataclass
class CrypticContent:
    """Contenu cryptique repéré, avec son alternative éventuelle."""

    element: Tag
    text: str
    kind: str
    # Alternative portée par l'élément (title, ou aria-label sur role=img) et sa source.
    alternative: str
    alternative_source: str
    context: str
    # Élément qui porte l'alternative (l'élément lui-même ou un parent en ligne), None sans alternative.
    alternative_element: Tag | None = None


def _skipped(node: NavigableString) -> bool:
    return any(isinstance(parent, Tag) and parent.name in _SKIPPED for parent in node.parents)


def _is_ascii_art(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    visible = "".join(text.split())
    return len(visible) >= 20 and len(_SYMBOLS.findall(visible)) / len(visible) >= 0.5


def _alternative(element: Tag) -> tuple[str, str, Tag | None]:
    """title de l'élément ou d'un parent en ligne, ou aria-label d'un role=img ; avec l'élément qui le porte."""
    current: Tag | None = element
    while isinstance(current, Tag):
        if str(current.get("role") or "").strip().lower() == "img":
            label = normalize(str(current.get("aria-label") or ""))
            if label:
                return label, "aria-label", current
        title = normalize(str(current.get("title") or ""))
        if title:
            return title, "title", current
        if current.name not in _INLINE:
            break
        current = current.parent if isinstance(current.parent, Tag) else None
    return "", "", None


def _context(element: Tag, limit: int = 300) -> str:
    block = element if element.name in _BLOCKS else element.find_parent(_BLOCKS)
    target = block if isinstance(block, Tag) else element
    return normalize(target.get_text(" ", strip=True))[:limit]


def find_cryptic_contents(soup: BeautifulSoup) -> list[CrypticContent]:
    """Contenus cryptiques de la page, dans l'ordre du document."""
    contents: list[CrypticContent] = []
    seen_ascii: set[int] = set()
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString) or _skipped(node):
            continue
        element = node.parent
        if not isinstance(element, Tag) or not str(node).strip():
            continue
        text = str(node)

        pre = element if element.name == "pre" else element.find_parent("pre")
        block = pre if isinstance(pre, Tag) else element
        if id(block) in seen_ascii:
            continue
        if _is_ascii_art(block.get_text()):
            seen_ascii.add(id(block))
            alternative, source, carrier = _alternative(block)
            contents.append(
                CrypticContent(
                    block,
                    block.get_text().strip("\n"),
                    ASCII_ART_KIND,
                    alternative,
                    source,
                    _surrounding(block),
                    carrier,
                )
            )
            continue

        for pattern, kind in ((EMOTICON, EMOTICON_KIND), (CRYPTIC_SYNTAX, SYNTAX_KIND)):
            for match in pattern.finditer(text):
                alternative, source, carrier = _alternative(element)
                contents.append(
                    CrypticContent(element, match.group(0), kind, alternative, source, _context(element), carrier)
                )
    return contents


def _surrounding(element: Tag, limit: int = 300) -> str:
    """Texte placé juste avant et juste après un bloc (légende, explication)."""
    parts: list[str] = []
    for sibling in (element.find_previous_sibling(), element.find_next_sibling()):
        if isinstance(sibling, Tag):
            parts.append(normalize(sibling.get_text(" ", strip=True))[: limit // 2])
    caption = element.find_parent("figure")
    if isinstance(caption, Tag) and caption.figcaption:
        parts.append(normalize(caption.figcaption.get_text(" ", strip=True)))
    return " | ".join(part for part in parts if part)

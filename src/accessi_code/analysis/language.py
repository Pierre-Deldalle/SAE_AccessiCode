"""
Observations DOM sur la langue et le sens de lecture (thème RGAA 8).

- segments de texte regroupés par langue héritée (8.7) ;
- changements de langue déclarés par ``lang`` / ``xml:lang`` (8.8) ;
- sens de lecture d'un texte d'après ses lettres, et sens effectif d'un
  élément d'après ``dir`` (8.10).

Aucune décision RGAA n'est prise ici.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.sensory import SKIPPED_TAGS, text_blocks
from accessi_code.analysis.structure import is_hidden

MARKED_PASSAGE = "[passage balisé]"
SEGMENT_LIMIT = 1200
LANG_ATTRIBUTES = ("lang", "xml:lang")
DIRECTIONS = frozenset({"ltr", "rtl"})

_RTL_RANGES = (
    (0x0590, 0x08FF),  # hébreu, arabe, syriaque, thaana, n'ko, samaritain, mandéen, arabe étendu
    (0xFB1D, 0xFDFF),  # formes de présentation hébraïques et arabes A
    (0xFE70, 0xFEFF),  # formes de présentation arabes B
)


def normalize(value: str) -> str:
    return " ".join(value.split())


def own_lang(tag: Tag) -> str | None:
    for attribute in LANG_ATTRIBUTES:
        value = tag.get(attribute)
        if isinstance(value, str):
            return value.strip()
    return None


def inherited_lang(tag: Tag) -> str:
    """Langue de l'élément : son attribut lang ou celui de l'ancêtre le plus proche."""
    node: Tag | None = tag
    while isinstance(node, Tag) and node.name != "[document]":
        value = own_lang(node)
        if value is not None:
            return value
        node = node.parent
    return ""


def text_without_marked(
    tag: Tag, *, skip: set[int] | None = None, attributes: tuple[str, ...] = LANG_ATTRIBUTES
) -> str:
    """
    Texte de l'élément où les descendants portant leur propre attribut
    (lang, ou dir pour 8.10) sont remplacés par [passage balisé].
    ``skip`` : descendants traités à part (autres blocs de texte), ignorés.
    """
    parts: list[str] = []

    def collect(node: Tag) -> None:
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag):
                if child.name in SKIPPED_TAGS or (skip and id(child) in skip):
                    continue
                if any(child.has_attr(name) for name in attributes):
                    parts.append(f" {MARKED_PASSAGE} ")
                    continue
                if child.name in {"img", "area"} and isinstance(child.get("alt"), str):
                    parts.append(f" {child['alt']} ")
                collect(child)

    collect(tag)
    return normalize("".join(parts))


def has_words(text: str) -> bool:
    return any(len(word) > 1 and any(character.isalpha() for character in word) for word in text.split())


@dataclass
class Segment:
    """Blocs consécutifs de même langue héritée, soumis ensemble à l'IA."""

    lang: str
    blocks: list[Tag] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " / ".join(self.texts)


def language_segments(soup: BeautifulSoup, limit: int = SEGMENT_LIMIT) -> list[Segment]:
    blocks = text_blocks(soup)
    block_ids = {id(block) for block in blocks}
    segments: list[Segment] = []
    for block in blocks:
        text = text_without_marked(block, skip=block_ids - {id(block)})
        if not has_words(text.replace(MARKED_PASSAGE, "")):
            continue
        lang = inherited_lang(block)
        current = segments[-1] if segments else None
        if current is None or current.lang != lang or len(current.text) + len(text) > limit:
            current = Segment(lang)
            segments.append(current)
        current.blocks.append(block)
        current.texts.append(text[:limit])
    return segments


def language_changes(soup: BeautifulSoup) -> list[Tag]:
    """Éléments (hors html) qui déclarent une langue, visibles, dans l'ordre du document."""
    return [
        tag
        for tag in soup.find_all(True)
        if tag.name != "html"
        and own_lang(tag) is not None
        and tag.find_parent(["head", "script", "template"]) is None
        and not is_hidden(tag)
    ]


# ----------------------------------------------------------------------
# Sens de lecture
# ----------------------------------------------------------------------


def is_rtl_character(character: str) -> bool:
    code = ord(character)
    return any(start <= code <= end for start, end in _RTL_RANGES)


def letter_counts(text: str) -> tuple[int, int]:
    """(lettres de droite à gauche, lettres de gauche à droite)."""
    rtl = sum(1 for character in text if character.isalpha() and is_rtl_character(character))
    ltr = sum(1 for character in text if character.isalpha() and not is_rtl_character(character))
    return rtl, ltr


def text_direction(text: str) -> str | None:
    """Sens dominant d'un texte ; None s'il ne contient aucune lettre."""
    rtl, ltr = letter_counts(text)
    if not rtl and not ltr:
        return None
    return "rtl" if rtl > ltr else "ltr"


def default_direction(soup: BeautifulSoup) -> str:
    html = soup.find("html")
    value = str(html.get("dir") or "").strip().lower() if isinstance(html, Tag) else ""
    return value if value in DIRECTIONS else "ltr"


def effective_direction(tag: Tag, default: str) -> str:
    """Sens donné par l'attribut dir (ltr ou rtl) de l'élément ou d'un parent ; sinon sens par défaut."""
    node: Tag | None = tag
    while isinstance(node, Tag) and node.name not in {"[document]", "html"}:
        value = str(node.get("dir") or "").strip().lower()
        if value in DIRECTIONS:
            return value
        node = node.parent
    return default


def opposite_direction_elements(soup: BeautifulSoup) -> list[tuple[Tag, str]]:
    """
    Éléments dont le texte propre est écrit dans le sens opposé au sens par
    défaut de la page : (élément, texte). Sur une page de gauche à droite, un
    texte qui contient au moins deux lettres de droite à gauche est retenu.
    """
    default = default_direction(soup)
    found: list[tuple[Tag, str]] = []
    seen: set[int] = set()
    for node in soup.find_all(string=True):
        parent = node.parent
        if not isinstance(parent, Tag) or parent.name in SKIPPED_TAGS or id(parent) in seen:
            continue
        if parent.find_parent(list(SKIPPED_TAGS)) is not None or is_hidden(parent):
            continue
        text = normalize(" ".join(str(part) for part in parent.children if isinstance(part, NavigableString)))
        rtl, ltr = letter_counts(text)
        opposite = rtl >= 2 if default == "ltr" else ltr >= 3 and ltr > rtl
        if opposite:
            seen.add(id(parent))
            found.append((parent, text))
    return found

"""
Observations DOM de structuration de l'information (thème RGAA 9).

Repère les titres, listes et citations balisés, ainsi que les passages
qui pourraient en être sans être balisés (candidats soumis ensuite à l'IA).
Aucune décision RGAA n'est prise ici.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_VALID_LEVELS = {"1", "2", "3", "4", "5", "6"}

_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)
_TITLE_CLASS = re.compile(r"\b(title|titre|heading|headline|intertitre)\b", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^\s*([-–—•●▪◦*✓✔→>])\s+\S")
_NUMBERED_LINE = re.compile(r"^\s*(\d{1,2}|[a-z])[.)]\s+\S", re.IGNORECASE)
_INLINE_QUOTE = re.compile(r"«\s*([^«»]{15,400}?)\s*»|“([^“”]{15,400}?)”|\"([^\"]{15,400}?)\"")
_QUOTE_CLASS = re.compile(r"\b(quote|citation|cite|temoignage|témoignage)\b", re.IGNORECASE)
_SKIPPED_TAGS = {"script", "style", "template", "noscript"}


# ----------------------------------------------------------------------
# Visibilité et texte
# ----------------------------------------------------------------------


def is_hidden(tag: Tag) -> bool:
    """Élément masqué par hidden, aria-hidden="true" ou un style en ligne, sur lui ou un ancêtre."""
    node: Tag | None = tag
    while isinstance(node, Tag) and node.name != "[document]":
        if node.has_attr("hidden") or str(node.get("aria-hidden") or "").lower() == "true":
            return True
        if _HIDDEN_STYLE.search(str(node.get("style") or "")):
            return True
        node = node.parent
    return False


def accessible_text(tag: Tag) -> str:
    """Texte d'un élément, alternatives des images comprises (logo dans un titre, etc.)."""
    parts: list[str] = []
    for node in tag.descendants:
        if isinstance(node, NavigableString):
            if not isinstance(node.parent, Tag) or node.parent.name not in _SKIPPED_TAGS:
                parts.append(str(node))
        elif isinstance(node, Tag) and node.name in {"img", "area", "input"}:
            alt = node.get("alt")
            if isinstance(alt, str):
                parts.append(f" {alt} ")
    label = str(tag.get("aria-label") or "").strip()
    text = " ".join("".join(parts).split())
    return label or text


# ----------------------------------------------------------------------
# Titres
# ----------------------------------------------------------------------


@dataclass
class Heading:
    tag: Tag
    level: int
    text: str


def heading_level(tag: Tag) -> int | None:
    """Niveau d'un titre (h1-h6 ou role="heading" avec aria-level valide)."""
    if tag.name in HEADING_TAGS:
        return int(tag.name[1])
    if str(tag.get("role") or "").strip().lower() == "heading":
        level = str(tag.get("aria-level") or "").strip()
        if level in _VALID_LEVELS:
            return int(level)
    return None


def headings(soup: BeautifulSoup) -> list[Heading]:
    """Titres visibles, dans l'ordre du document."""
    found: list[Heading] = []
    for tag in soup.find_all(True):
        level = heading_level(tag)
        if level is not None and not is_hidden(tag):
            found.append(Heading(tag, level, accessible_text(tag)))
    return found


def invalid_aria_headings(soup: BeautifulSoup) -> list[Tag]:
    """Éléments role="heading" sans aria-level valide (RGAA 9.1.3)."""
    return [
        tag
        for tag in soup.find_all(attrs={"role": True})
        if str(tag.get("role")).strip().lower() == "heading"
        and tag.name not in HEADING_TAGS
        and str(tag.get("aria-level") or "").strip() not in _VALID_LEVELS
        and not is_hidden(tag)
    ]


def section_text(heading: Heading, all_headings: list[Heading], limit: int = 500) -> str:
    """Début du contenu introduit par un titre (jusqu'au titre suivant de niveau égal ou supérieur)."""
    following = {id(item.tag) for item in all_headings if item.level <= heading.level and item is not heading}
    parts: list[str] = []
    length = 0
    for node in heading.tag.next_elements:
        if isinstance(node, Tag) and id(node) in following:
            break
        if isinstance(node, NavigableString) and not (isinstance(node.parent, Tag) and heading.tag in node.parents):
            if isinstance(node.parent, Tag) and node.parent.name in _SKIPPED_TAGS:
                continue
            text = " ".join(str(node).split())
            if text:
                parts.append(text)
                length += len(text)
                if length >= limit:
                    break
    return " ".join(parts)[:limit]


def heading_candidates(soup: BeautifulSoup) -> list[Tag]:
    """
    Passages courts mis en forme comme des titres sans être balisés comme tels :
    paragraphe composé uniquement d'un texte en gras, ou élément dont la classe
    évoque un titre.
    """
    candidates: list[Tag] = []
    for tag in soup.find_all(["p", "div", "span", "strong", "b"]):
        if heading_level(tag) is not None or tag.find_parent([*HEADING_TAGS, "a", "button", "label", "th"]):
            continue
        if is_hidden(tag):
            continue
        text = " ".join(tag.get_text(" ", strip=True).split())
        if not 2 <= len(text) <= 120 or text.endswith((".", ",", ";")):
            continue
        children = [child for child in tag.children if not (isinstance(child, NavigableString) and not child.strip())]
        bold_only = (
            tag.name in {"p", "div"}
            and len(children) == 1
            and isinstance(children[0], Tag)
            and children[0].name in {"strong", "b"}
        )
        titled_class = tag.name in {"p", "div", "span"} and bool(_TITLE_CLASS.search(" ".join(tag.get("class") or [])))
        if (bold_only or titled_class) and not tag.find(["p", "div", "ul", "ol", "table"]):
            candidates.append(tag)
    return candidates


# ----------------------------------------------------------------------
# Listes
# ----------------------------------------------------------------------


def text_lines(tag: Tag) -> list[str]:
    """Lignes de texte d'un bloc, séparées par <br> ou par des retours à la ligne."""
    chunks: list[str] = []
    current: list[str] = []
    for node in tag.descendants:
        if isinstance(node, Tag) and node.name == "br":
            chunks.append("".join(current))
            current = []
        elif isinstance(node, NavigableString):
            current.append(str(node))
    chunks.append("".join(current))
    lines: list[str] = []
    for chunk in chunks:
        lines.extend(line.strip() for line in chunk.splitlines() if line.strip())
    return lines


def list_candidates(soup: BeautifulSoup, *, ordered: bool) -> list[Tag]:
    """
    Blocs présentant visuellement une liste sans balisage de liste :
    au moins deux lignes commençant par une puce (ou un numéro si ``ordered``),
    dans un même bloc ou dans des paragraphes consécutifs.
    """
    pattern = _NUMBERED_LINE if ordered else _BULLET_LINE
    candidates: list[Tag] = []
    seen: set[int] = set()

    for tag in soup.find_all(["p", "div", "td", "dd"]):
        if is_hidden(tag) or tag.find_parent(["ul", "ol", "dl", "pre", "code"]) or tag.find(["ul", "ol", "p", "div"]):
            continue
        lines = text_lines(tag)
        if len(lines) >= 2 and sum(1 for line in lines if pattern.match(line)) >= 2:
            candidates.append(tag)
            seen.add(id(tag))

    # Paragraphes consécutifs commençant chacun par une puce ou un numéro.
    for paragraph in soup.find_all("p"):
        if id(paragraph) in seen or is_hidden(paragraph):
            continue
        if not pattern.match(paragraph.get_text(" ", strip=True)):
            continue
        sibling = paragraph.find_next_sibling()
        previous = paragraph.find_previous_sibling()
        if previous is not None and previous.name == "p" and pattern.match(previous.get_text(" ", strip=True)):
            continue  # Déjà compté depuis le premier paragraphe de la série.
        if sibling is not None and sibling.name == "p" and pattern.match(sibling.get_text(" ", strip=True)):
            candidates.append(paragraph)
            seen.add(id(paragraph))
    return candidates


def list_structure_problems(tag: Tag) -> list[str]:
    """Défauts de balisage d'une liste ul / ol / dl / role="list"."""
    if tag.name in {"ul", "ol"}:
        children = [child for child in tag.find_all(True, recursive=False) if child.name not in _SKIPPED_TAGS]
        problems = []
        if not children:
            problems.append(f"la liste <{tag.name}> ne contient aucun élément <li>")
        elif any(child.name != "li" for child in children):
            problems.append(f"la liste <{tag.name}> contient des éléments enfants autres que <li>")
        return problems
    if tag.name == "dl":
        children = [child for child in tag.find_all(True, recursive=False) if child.name not in _SKIPPED_TAGS]
        # Les groupes <div> sont autorisés en HTML5 dans une liste de description.
        items = [grand for child in children for grand in ([child] if child.name != "div" else child.find_all(True))]
        names = {item.name for item in items}
        problems = []
        if "dt" not in names:
            problems.append("la liste <dl> ne contient aucun terme <dt>")
        if "dd" not in names:
            problems.append("la liste <dl> ne contient aucune définition <dd>")
        if any(child.name not in {"dt", "dd", "div"} for child in children):
            problems.append("la liste <dl> contient des éléments enfants autres que <dt>, <dd> ou <div>")
        return problems
    if str(tag.get("role") or "").lower() == "list":
        items = [child for child in tag.find_all(True, recursive=False) if child.name not in _SKIPPED_TAGS]
        if not items or any(str(child.get("role") or "").lower() != "listitem" for child in items):
            return ['les éléments de la liste role="list" n\'ont pas tous role="listitem"']
    return []


# ----------------------------------------------------------------------
# Citations
# ----------------------------------------------------------------------


def inline_quote_candidates(soup: BeautifulSoup) -> list[tuple[Tag, str]]:
    """Citations entre guillemets au sein d'un paragraphe, hors <q> et <blockquote>."""
    candidates: list[tuple[Tag, str]] = []
    for tag in soup.find_all(["p", "li", "td", "dd", "span", "div"]):
        if is_hidden(tag) or tag.find_parent(["q", "blockquote", "code", "pre"]) or tag.find(["p", "div", "li"]):
            continue
        text = " ".join(tag.get_text(" ", strip=True).split())
        for match in _INLINE_QUOTE.finditer(text):
            quoted = next(group for group in match.groups() if group)
            # Un bloc entièrement entre guillemets relève de 9.4.2.
            if len(quoted) < len(text) * 0.8:
                candidates.append((tag, quoted))
    return candidates


def block_quote_candidates(soup: BeautifulSoup) -> list[Tag]:
    """Blocs de texte entièrement cités ou identifiés comme citation, hors <blockquote>."""
    candidates: list[Tag] = []
    for tag in soup.find_all(["p", "div"]):
        if is_hidden(tag) or tag.find_parent(["blockquote", "q"]) or tag.find(["p", "div", "blockquote"]):
            continue
        text = " ".join(tag.get_text(" ", strip=True).split())
        if len(text) < 60:
            continue
        quoted_block = text.startswith(("«", "“", '"')) and text.rstrip(" .").endswith(("»", "”", '"'))
        quote_class = bool(_QUOTE_CLASS.search(" ".join(tag.get("class") or [])))
        if quoted_block or quote_class:
            candidates.append(tag)
    return candidates

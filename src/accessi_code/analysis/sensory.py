"""
Candidats des critères sensoriels : couleur (RGAA 3.1), forme, taille et
position (RGAA 10.9 et 10.10).

Ce module ne prend aucune décision RGAA : il repère, à partir du DOM et des
feuilles de style, les passages susceptibles de transmettre une information
par une caractéristique sensorielle. L'IA juge ensuite chaque candidat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import soupsieve
from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.css import CSSRule, inline_style, stylesheet_rules
from accessi_code.analysis.image_elements import image_kind
from accessi_code.analysis.structure import HEADING_TAGS, is_hidden
from accessi_code.models.audit_context import AuditContext

TEXT_LIMIT = 500
CONTEXT_LIMIT = 600

SKIPPED_TAGS = frozenset({"script", "style", "template", "noscript", "title", "head"})

BLOCK_TAGS = frozenset(
    {
        "p",
        "li",
        "dt",
        "dd",
        "td",
        "th",
        "caption",
        "figcaption",
        "label",
        "legend",
        "blockquote",
        "button",
        "summary",
        "pre",
        "address",
        *HEADING_TAGS,
    }
)

# Éléments de texte courant dont la mise en couleur relève de 3.1.1.
PHRASING_TAGS = frozenset(
    {
        "span",
        "font",
        "em",
        "strong",
        "b",
        "i",
        "mark",
        "small",
        "u",
        "s",
        "del",
        "ins",
        "code",
        "abbr",
        "cite",
        "q",
        "sup",
        "sub",
        "time",
        "var",
        "kbd",
        "samp",
        "dfn",
    }
)

# Conteneurs de mise en page : leur fond relève de la décoration, pas de 3.1.4.
LAYOUT_TAGS = frozenset(
    {"html", "body", "main", "header", "footer", "nav", "section", "article", "aside", "form", "table", "ul", "ol"}
)

TEXT_COLOR_PROPERTIES = ("color", "background", "background-color")
COLOR_PROPERTIES = (
    *TEXT_COLOR_PROPERTIES,
    "border",
    "border-color",
    "border-top",
    "border-bottom",
    "border-left",
    "border-right",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "outline",
    "outline-color",
    "text-decoration-color",
    "fill",
    "stroke",
)
NEUTRAL_VALUES = frozenset({"inherit", "initial", "unset", "revert", "currentcolor", "transparent", "none"})

# Sélecteurs qui signalent un état ou un statut (erreur, sélection, élément courant…).
STATE_SELECTOR = re.compile(
    r":(?:invalid|valid|checked|required|user-invalid)\b"
    r"|\[aria-(?:invalid|current|selected|checked|pressed)"
    r"|\.(?:is-)?(?:error|erreur|invalid|invalide|valid|valide|success|succes|succès|warning|danger|alert|alerte"
    r"|required|obligatoire|active|actif|selected|current|disabled|status|statut|badge|ok|ko)\b",
    re.IGNORECASE,
)
DYNAMIC_PSEUDO = re.compile(
    r":(?:invalid|valid|user-invalid|hover|focus|focus-visible|focus-within|active|visited)\b", re.IGNORECASE
)

_COLOR_NAMES = (
    r"rouges?|verte?s?|bleue?s?|jaunes?|oranges?|violete?s?|violettes?|roses?|grise?s?|noire?s?|blanc(?:he)?s?"
    r"|marron|turquoises?|dorée?s?|argentée?s?"
)
COLOR_INDICATION = re.compile(
    rf"(?<!\w)(?:{_COLOR_NAMES}|couleurs?|colorée?s?|surlignée?s?)(?!\w)",
    re.IGNORECASE,
)

# Pré-filtre resserré : seulement des tournures qui désignent une forme, une
# taille ou une position (« avant », « premier », « entre »… sont exclus).
SHAPE_SIZE_POSITION = re.compile(
    r"(?<!\w)(?:"
    r"ronde?s?|carrée?s?|circulaires?|triangles?|triangulaires?|losanges?|cercles?|étoiles?|flèches?"
    r"|en forme d[e']"
    r"|en (?:plus )?(?:gros|petits?|grands?) caractères|en gros|en petit"
    r"|(?:plus|moins) (?:grande?s?|petite?s?|grosse?s?)"
    r"|de (?:grande|petite) taille"
    r"|à (?:gauche|droite)|(?:sur la|de la|du côté) (?:gauche|droite)|du côté droit|ci-dessus|ci-dessous|ci-contre"
    r"|en haut|en bas|au-dessus|au-dessous|en dessous|plus haut|plus bas|dans le coin"
    r"|colonnes? de (?:gauche|droite)|en face"
    r")(?!\w)",
    re.IGNORECASE,
)


@dataclass
class Candidate:
    """Élément soumis au jugement de l'IA."""

    tag: Tag
    identifier: str
    text: str
    html: str
    context: str
    evidence: dict[str, Any] = field(default_factory=dict)


def normalize(value: str) -> str:
    return " ".join(value.split())


def identifier(tag: Tag, index: int) -> str:
    """Identifiant lisible : id, sinon classes, sinon position parmi les candidats."""
    element_id = tag.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return f"{tag.name}#{element_id.strip()}"
    classes = tag.get("class")
    if isinstance(classes, list) and classes:
        return f"{tag.name}.{'.'.join(str(name) for name in classes[:2])}"
    return f"{tag.name}[index={index}]"


def element_context(tag: Tag, limit: int = CONTEXT_LIMIT) -> str:
    """Texte du bloc parent et titre de la section, pour situer un candidat."""
    parts: list[str] = []
    block = tag if tag.name in BLOCK_TAGS else tag.find_parent(list(BLOCK_TAGS))
    if isinstance(block, Tag) and block is not tag:
        parts.append(f"Bloc ({block.name}) : {normalize(block.get_text(' ', strip=True))[:300]}")
    container = tag.find_parent(["fieldset", "form", "table", "figure", "ul", "ol"])
    if isinstance(container, Tag):
        parts.append(f"Conteneur ({container.name}) : {normalize(container.get_text(' ', strip=True))[:200]}")
    heading = tag.find_previous(list(HEADING_TAGS))
    if isinstance(heading, Tag):
        parts.append(f"Titre de la section : {normalize(heading.get_text(' ', strip=True))}")
    return " — ".join(parts)[:limit]


def _visible_in_body(tag: Tag) -> bool:
    return tag.find_parent(list(SKIPPED_TAGS)) is None and tag.name not in SKIPPED_TAGS and not is_hidden(tag)


# ----------------------------------------------------------------------
# Passages de texte (3.1.2, 10.9.1, 10.10.1)
# ----------------------------------------------------------------------


def text_blocks(soup: BeautifulSoup) -> list[Tag]:
    """Blocs de texte visibles, dans l'ordre du document, chacun une seule fois."""
    blocks: list[Tag] = []
    seen: set[int] = set()
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString) or not node.strip():
            continue
        parent = node.parent
        if not isinstance(parent, Tag) or parent.name in SKIPPED_TAGS:
            continue
        block = parent if parent.name in BLOCK_TAGS else parent.find_parent(list(BLOCK_TAGS)) or parent
        if id(block) in seen or block.name == "[document]":
            continue
        seen.add(id(block))
        if _visible_in_body(block):
            blocks.append(block)
    return blocks


def text_candidates(soup: BeautifulSoup, pattern: re.Pattern[str]) -> list[Candidate]:
    """Blocs dont le texte contient une tournure repérée par ``pattern``."""
    candidates: list[Candidate] = []
    for block in text_blocks(soup):
        text = normalize(block.get_text(" ", strip=True))
        matches = sorted({match.group(0).lower() for match in pattern.finditer(text)})
        if not matches:
            continue
        candidates.append(
            Candidate(
                tag=block,
                identifier=identifier(block, len(candidates)),
                text=text[:TEXT_LIMIT],
                html=str(block)[:400],
                context=element_context(block),
                evidence={"expressions": matches},
            )
        )
    return candidates


# ----------------------------------------------------------------------
# Couleurs appliquées par le code (3.1.1, 3.1.4)
# ----------------------------------------------------------------------


@dataclass
class _CompiledRule:
    rule: CSSRule
    matcher: Any


_TYPE_SELECTOR = re.compile(r"^(?:\*|:root|[a-z][a-z0-9]*)$", re.IGNORECASE)


def _compile_rules(rules: list[CSSRule], properties: tuple[str, ...]) -> list[_CompiledRule]:
    """
    Règles de couleur ciblant des éléments choisis (classe, id, attribut, état).

    Un sélecteur de type seul (``code { background: … }``) colore toute une
    catégorie d'éléments de façon uniforme : ce n'est pas une mise en couleur
    de mots choisis, la règle est ignorée.
    """
    compiled: list[_CompiledRule] = []
    for rule in rules:
        if _TYPE_SELECTOR.match(rule.selector.strip()):
            continue
        if not _color_values(rule.properties, properties):
            continue
        selector = DYNAMIC_PSEUDO.sub("", rule.selector).strip() or "*"
        try:
            compiled.append(_CompiledRule(rule, soupsieve.compile(selector)))
        except Exception:
            continue
    return compiled


def _color_values(properties: dict[str, str], wanted: tuple[str, ...]) -> list[str]:
    return [
        f"{name}: {value}"
        for name, value in properties.items()
        if name in wanted and value.strip().lower() not in NEUTRAL_VALUES
    ]


def _declarations(tag: Tag, rules: list[_CompiledRule], properties: tuple[str, ...]) -> list[str]:
    """Couleurs appliquées à l'élément : attribut, style en ligne, règles de feuille."""
    found: list[str] = []
    if tag.name == "font" and tag.get("color"):
        found.append(f'attribut color="{tag.get("color")}"')
    if tag.name == "mark":
        found.append("élément mark (surlignage)")
    found.extend(f"style en ligne : {value}" for value in _color_values(inline_style(tag), properties))
    for item in rules:
        try:
            matched = item.matcher.match(tag)
        except Exception:
            matched = False
        if matched:
            values = "; ".join(_color_values(item.rule.properties, properties))
            found.append(f"{item.rule.selector} {{ {values} }}")
    return found


def colored_words(context: AuditContext) -> list[Candidate]:
    """3.1.1 : mots ou groupes de mots mis en couleur (éléments de texte courant)."""
    soup = context.dom
    if not isinstance(soup, BeautifulSoup):
        return []
    rules = _compile_rules(stylesheet_rules(context), TEXT_COLOR_PROPERTIES)
    candidates: list[Candidate] = []
    for tag in soup.find_all(list(PHRASING_TAGS)):
        text = normalize(tag.get_text(" ", strip=True))
        if not text or not _visible_in_body(tag):
            continue
        declarations = _declarations(tag, rules, TEXT_COLOR_PROPERTIES)
        if not declarations:
            continue
        candidates.append(
            Candidate(
                tag=tag,
                identifier=identifier(tag, len(candidates)),
                text=text[:TEXT_LIMIT],
                html=str(tag)[:400],
                context=f"Mise en couleur : {' ; '.join(declarations)[:200]} — {element_context(tag)}",
                evidence={"colors": declarations},
            )
        )
    return candidates


def _underline_removed(tag: Tag, rules: list[CSSRule]) -> str | None:
    """Règle qui retire le soulignement d'un lien, ou None."""

    def removes(properties: dict[str, str]) -> bool:
        return any(
            properties.get(name, "").strip().lower().startswith("none")
            for name in ("text-decoration", "text-decoration-line")
        )

    if removes(inline_style(tag)):
        return "style en ligne : text-decoration: none"
    for rule in rules:
        if not removes(rule.properties):
            continue
        try:
            if soupsieve.match(DYNAMIC_PSEUDO.sub("", rule.selector).strip() or "*", tag):
                return f"{rule.selector} {{ text-decoration: none }}"
        except Exception:
            continue
    return None


def color_property_candidates(context: AuditContext) -> list[Candidate]:
    """
    3.1.4 : propriétés CSS de couleur susceptibles de porter une information.

    - liens placés dans un texte dont le soulignement est retiré (seule la
      couleur les distinguerait du texte) ;
    - éléments colorés par une règle d'état (erreur, sélection, élément courant…) ;
    - éléments (hors texte courant et conteneurs de mise en page) colorés par
      un style en ligne.

    Les éléments de texte courant colorés relèvent de 3.1.1.
    """
    soup = context.dom
    if not isinstance(soup, BeautifulSoup):
        return []
    sheet = stylesheet_rules(context)
    state_rules = _compile_rules([rule for rule in sheet if STATE_SELECTOR.search(rule.selector)], COLOR_PROPERTIES)

    candidates: list[Candidate] = []
    for tag in soup.find_all(True):
        if tag.name in PHRASING_TAGS or tag.name in LAYOUT_TAGS or not _visible_in_body(tag):
            continue
        reasons: list[str] = []
        evidence: dict[str, Any] = {}
        if tag.name == "a" and tag.has_attr("href"):
            removed = _underline_removed(tag, sheet)
            block = tag.find_parent(["p", "li", "td", "dd", "blockquote"])
            link_text = normalize(tag.get_text(" ", strip=True))
            if removed and isinstance(block, Tag) and len(normalize(block.get_text(" ", strip=True))) > len(link_text):
                reasons.append(f"lien dans un texte sans soulignement ({removed})")
                evidence["underline_removed"] = removed
        reasons.extend(_declarations(tag, state_rules, COLOR_PROPERTIES))
        if tag.name != "a":
            reasons.extend(f"style en ligne : {value}" for value in _color_values(inline_style(tag), COLOR_PROPERTIES))
        text = normalize(tag.get_text(" ", strip=True))
        if not reasons or len(text) > 300:
            continue
        candidates.append(
            Candidate(
                tag=tag,
                identifier=identifier(tag, len(candidates)),
                text=text[:TEXT_LIMIT] or f"(élément {tag.name} sans texte)",
                html=str(tag)[:400],
                context=f"Couleur appliquée : {' ; '.join(reasons)[:250]} — {element_context(tag)}",
                evidence={"colors": reasons, **evidence},
            )
        )
    return candidates


# ----------------------------------------------------------------------
# Médias (3.1.5, 3.1.6, 10.9.3, 10.9.4, 10.10.3, 10.10.4)
# ----------------------------------------------------------------------


def media_elements(soup: BeautifulSoup, names: tuple[str, ...]) -> list[Tag]:
    """Médias visibles du type demandé (``object``/``embed`` d'image exclus : ce sont des images)."""
    return [
        tag
        for tag in soup.find_all(list(names))
        if _visible_in_body(tag)
        and not (tag.name in {"object", "embed"} and image_kind(tag) is not None)
        and not (tag.name == "embed" and tag.find_parent("object") is not None)
    ]

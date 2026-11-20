"""
Animations d'une page : animations CSS, images animées et moyens de les arrêter
(RGAA 13.7 flashs, 13.8 contenus en mouvement ou clignotants).

Les propriétés animées sont classées en deux familles :
- luminosité (opacity, visibility, couleurs, filter…) : flash ou clignotement ;
- position (transform, left, margin…) : mouvement.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.components import component_name, normalize
from accessi_code.analysis.css import inline_style, stylesheet_rules
from accessi_code.models.audit_context import AuditContext

LIGHT_PROPERTIES = frozenset(
    {
        "opacity",
        "visibility",
        "color",
        "background",
        "background-color",
        "background-image",
        "filter",
        "box-shadow",
        "fill",
        "border-color",
        "outline-color",
        "text-shadow",
    }
)
MOTION_PROPERTIES = frozenset(
    {
        "transform",
        "translate",
        "rotate",
        "scale",
        "left",
        "right",
        "top",
        "bottom",
        "margin",
        "margin-left",
        "margin-right",
        "margin-top",
        "margin-bottom",
        "background-position",
        "offset-distance",
        "inset",
    }
)
# Surface maximale cumulée d'un flash (RGAA 13.7 : 21 824 pixels).
FLASH_AREA_LIMIT = 21824
# Durée maximale d'un mouvement ou clignotement sans contrôle (RGAA 13.8 : 5 secondes).
MOTION_DURATION_LIMIT = 5.0

_INTERACTION_PSEUDO = re.compile(r":(?:hover|focus|focus-within|focus-visible|active|checked|target)\b")
_PSEUDO = re.compile(r"::?[\w-]+(?:\([^)]*\))?")
_KEYFRAMES = re.compile(r"@(?:-webkit-|-moz-)?keyframes\s+([\w-]+)\s*\{", re.IGNORECASE)
_TIME = re.compile(r"^(-?[\d.]+)(ms|s)$", re.IGNORECASE)
_TIMING_KEYWORDS = frozenset(
    {
        "linear",
        "ease",
        "ease-in",
        "ease-out",
        "ease-in-out",
        "step-start",
        "step-end",
        "normal",
        "reverse",
        "alternate",
        "alternate-reverse",
        "none",
        "forwards",
        "backwards",
        "both",
        "running",
        "paused",
        "initial",
        "inherit",
        "unset",
    }
)
_CONTROL_WORDING = re.compile(
    r"\b(?:pause|stop|arr[eê]t\w*|suspend\w*|lecture|play|mettre en pause|figer|masquer l'animation|animations?)\b",
    re.IGNORECASE,
)


@dataclass
class Keyframes:
    name: str
    # (position en %, valeur) de chaque propriété animée, dans l'ordre des étapes.
    values: dict[str, list[tuple[float, str]]] = field(default_factory=dict)

    @property
    def properties(self) -> set[str]:
        return set(self.values)

    def changes(self, properties: frozenset[str], cyclic: bool = False) -> int:
        """
        Plus grand nombre de changements de valeur au cours d'un cycle pour une
        propriété de la famille. Une étape 0 % ou 100 % absente reprend la valeur
        de l'élément, différente des valeurs animées. ``cyclic`` : l'animation
        recommence au début, ce qui ajoute le saut de la dernière valeur à la première.
        """
        counts: list[int] = []
        for prop, steps in self.values.items():
            if prop not in properties:
                continue
            sequence = [value for _, value in steps]
            if steps[0][0] > 0:
                sequence.insert(0, "<valeur de l'élément>")
            if steps[-1][0] < 100:
                sequence.append("<valeur de l'élément>")
            count = sum(1 for before, after in zip(sequence, sequence[1:], strict=False) if before != after)
            counts.append(count + (cyclic and sequence[-1] != sequence[0]))
        return max(counts, default=0)


@dataclass
class CSSAnimation:
    """Animation CSS appliquée à des éléments de la page."""

    selector: str
    elements: list[Tag]
    keyframes: Keyframes
    duration_s: float
    delay_s: float
    iterations: float  # math.inf pour infinite
    alternate: bool
    # Surface cumulée des éléments animés (px²), si toutes les dimensions sont connues.
    area: float | None = None

    @property
    def cyclic(self) -> bool:
        """L'animation repart de sa première étape à chaque répétition."""
        return self.iterations > 1 and not self.alternate

    @property
    def total_s(self) -> float:
        return self.delay_s + self.duration_s * self.iterations

    def animates(self, properties: frozenset[str]) -> bool:
        return bool(self.keyframes.properties & properties)


def css_texts(context: AuditContext) -> list[tuple[str, str]]:
    """(source, texte sans commentaires) des balises style puis des fichiers CSS fournis."""
    texts: list[tuple[str, str]] = []
    if isinstance(context.dom, BeautifulSoup):
        for index, style in enumerate(context.dom.find_all("style")):
            if style.string:
                texts.append((f"style[index={index}]", style.string))
    texts += [(Path(path).name, text) for path, text in (context.css_sources or {}).items()]
    return [(label, re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)) for label, text in texts]


def block_end(text: str, opening: int) -> int:
    """Position de l'accolade fermante du bloc ouvert à ``opening``."""
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(text)


def _offset(selector: str) -> float:
    selector = selector.strip().lower()
    if selector == "from":
        return 0.0
    if selector == "to":
        return 100.0
    try:
        return float(selector.rstrip("%"))
    except ValueError:
        return 0.0


def page_keyframes(context: AuditContext) -> dict[str, Keyframes]:
    """Règles @keyframes des feuilles de style, par nom."""
    result: dict[str, Keyframes] = {}
    for _label, text in css_texts(context):
        for match in _KEYFRAMES.finditer(text):
            body = text[match.end() : block_end(text, match.end() - 1)]
            steps: list[tuple[float, dict[str, str]]] = []
            for stop in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
                properties = {
                    key.strip().lower(): value.strip().lower()
                    for key, _, value in (part.partition(":") for part in stop.group(2).split(";"))
                    if key.strip() and value.strip()
                }
                for selector in stop.group(1).split(","):
                    steps.append((_offset(selector), properties))
            steps.sort(key=lambda item: item[0])
            frames = Keyframes(match.group(1))
            for position, properties in steps:
                for prop, value in properties.items():
                    frames.values.setdefault(prop, []).append((position, value))
            result[frames.name] = frames
    return result


def _seconds(value: str) -> float | None:
    match = _TIME.match(value.strip())
    if not match:
        return None
    number = float(match.group(1))
    return number / 1000 if match.group(2).lower() == "ms" else number


def _split_top_level(value: str, separator: str = ",") -> list[str]:
    parts, depth, current = [], 0, ""
    for char in value:
        depth += char == "("
        depth -= char == ")"
        if char == separator and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def parse_animations(properties: dict[str, str]) -> list[dict[str, object]]:
    """Animations décrites par ``animation`` ou ``animation-*`` (nom, durée, délai, répétitions, sens)."""
    animations: list[dict[str, object]] = []
    shorthand = properties.get("animation", "")
    for part in _split_top_level(shorthand):
        entry: dict[str, object] = {"name": None, "duration": 0.0, "delay": 0.0, "iterations": 1.0, "alternate": False}
        times = 0
        for token in re.findall(r"[\w.%-]+\([^)]*\)|[^\s]+", part):
            lowered = token.lower()
            seconds = _seconds(lowered)
            if seconds is not None:
                entry["duration" if times == 0 else "delay"] = seconds
                times += 1
            elif lowered == "infinite":
                entry["iterations"] = math.inf
            elif re.fullmatch(r"[\d.]+", lowered):
                entry["iterations"] = float(lowered)
            elif lowered.startswith("alternate"):
                entry["alternate"] = True
            elif lowered not in _TIMING_KEYWORDS and "(" not in lowered:
                entry["name"] = token
        animations.append(entry)

    names = _split_top_level(properties.get("animation-name", ""))
    for index, name in enumerate(names):
        if index >= len(animations):
            animations.append({"name": None, "duration": 0.0, "delay": 0.0, "iterations": 1.0, "alternate": False})
        animations[index]["name"] = name
    for key, field_name in (("animation-duration", "duration"), ("animation-delay", "delay")):
        for index, value in enumerate(_split_top_level(properties.get(key, ""))):
            seconds = _seconds(value)
            if index < len(animations) and seconds is not None:
                animations[index][field_name] = seconds
    for index, value in enumerate(_split_top_level(properties.get("animation-iteration-count", ""))):
        if index < len(animations):
            animations[index]["iterations"] = math.inf if value == "infinite" else float(value or 1)
    for index, value in enumerate(_split_top_level(properties.get("animation-direction", ""))):
        if index < len(animations):
            animations[index]["alternate"] = value.startswith("alternate")
    return [item for item in animations if item["name"] and item["name"] != "none"]


def _matching(soup: BeautifulSoup, selector: str) -> list[Tag]:
    cleaned = _PSEUDO.sub("", selector).strip()
    if not cleaned:
        return []
    try:
        return list(soup.select(cleaned))
    except Exception:  # sélecteur non pris en charge par soupsieve
        return []


def css_animations(context: AuditContext) -> list[CSSAnimation]:
    """
    Animations CSS lancées sans interaction : les règles qui ne s'appliquent qu'au
    survol, au focus ou à l'activation sont ignorées, comme celles qui ne
    correspondent à aucun élément de la page.
    """
    soup = context.dom
    if not isinstance(soup, BeautifulSoup):
        return []
    frames = page_keyframes(context)
    animations: list[CSSAnimation] = []

    sources: list[tuple[str, dict[str, str], list[Tag]]] = []
    for rule in stylesheet_rules(context):
        if "animation" not in " ".join(rule.properties) or _INTERACTION_PSEUDO.search(rule.selector):
            continue
        for selector in _split_top_level(rule.selector):
            elements = _matching(soup, selector)
            if elements:
                sources.append((selector, rule.properties, elements))
    for element in soup.find_all(style=True):
        properties = inline_style(element)
        if any(key.startswith("animation") for key in properties):
            sources.append((f"{element.name}[style]", properties, [element]))

    for selector, properties, elements in sources:
        for entry in parse_animations({key.lower(): value for key, value in properties.items()}):
            keyframes = frames.get(str(entry["name"]))
            if keyframes is None:
                continue
            animations.append(
                CSSAnimation(
                    selector,
                    elements,
                    keyframes,
                    float(entry["duration"]),  # type: ignore[arg-type]
                    float(entry["delay"]),  # type: ignore[arg-type]
                    float(entry["iterations"]),  # type: ignore[arg-type]
                    bool(entry["alternate"]),
                    _total_area(elements, properties),
                )
            )
    return animations


def _total_area(elements: list[Tag], properties: dict[str, str]) -> float | None:
    areas = [element_area(element, properties) for element in elements]
    return None if not areas or None in areas else sum(area for area in areas if area is not None)


# ----------------------------------------------------------------------
# Images animées et dimensions
# ----------------------------------------------------------------------


def local_file(context: AuditContext, src: str) -> Path | None:
    parsed = urlparse(src)
    if parsed.scheme or parsed.netloc or src.startswith("data:"):
        return None
    base = context.html_path.parent if context.html_path else context.workspace_path
    path = base / parsed.path.lstrip("/")
    return path if path.is_file() else None


def is_animated_image_file(path: Path) -> bool:
    """GIF à plusieurs images, PNG animé (acTL) ou WebP animé (ANIM)."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return data.count(b"\x21\xf9\x04") > 1
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        idat = data.find(b"IDAT")
        return b"acTL" in data[: idat if idat != -1 else len(data)]
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return b"ANIM" in data[:200]
    return False


def element_area(element: Tag, rule: dict[str, str] | None = None) -> float | None:
    """
    Surface en pixels déclarée par width/height (style en ligne, règle CSS
    fournie, puis attributs), si elle est connue en pixels.
    """
    style = inline_style(element)
    sizes: list[float] = []
    for dimension in ("width", "height"):
        declared = style.get(dimension) or (rule or {}).get(dimension) or element.get(dimension) or ""
        value = str(declared).strip().lower().removesuffix("px")
        try:
            sizes.append(float(value))
        except ValueError:
            return None
    return sizes[0] * sizes[1]


# ----------------------------------------------------------------------
# Moyens de contrôle
# ----------------------------------------------------------------------


def pause_controls(soup: BeautifulSoup) -> list[str]:
    """Intitulés des boutons qui semblent arrêter, mettre en pause ou masquer une animation."""
    labels: list[str] = []
    candidates = soup.find_all(["button", "input", "a", "summary"]) + soup.find_all(
        attrs={"role": re.compile(r"^(?:button|switch|checkbox)$", re.IGNORECASE)}
    )
    for element in candidates:
        if element.name == "input" and str(element.get("type") or "").lower() not in {"button", "checkbox", "submit"}:
            continue
        name, _ = component_name(element, soup)
        text = normalize(" ".join(filter(None, [name, str(element.get("title") or "")])))
        if text and _CONTROL_WORDING.search(text) and text not in labels:
            labels.append(text)
    return labels

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Tags susceptibles de recevoir le focus par défaut
_FOCUSABLE_TAGS = {
    "a",
    "area",
    "button",
    "input",
    "select",
    "textarea",
    "details",
    "summary",
    "command",
}

# Tags interactifs additionnels (HTML5)
_INTERACTIVE_TAGS = {"dialog"}

# Expression régulière pour détecter outline: none / 0
_OUTLINE_NONE_RE = re.compile(r"(?:^|;)\s*outline\s*:\s*(none|0(?:px|em|rem|%)?)\b", re.IGNORECASE)

# Expression régulière pour détecter outline-offset négatif qui cache le focus
_OUTLINE_OFFSET_NEGATIVE_RE = re.compile(
    r"(?:^|;)\s*outline-offset\s*:\s*(-\d+(?:\.\d+)?)(?:px|em|rem|%)\b", re.IGNORECASE
)

# Expression régulière pour détecter box-shadow qui pourrait remplacer l'outline
_BOX_SHADOW_RE = re.compile(r"(?:^|;)\s*box-shadow\s*:\s*([^;]+)", re.IGNORECASE)

# Expression régulière pour détecter border visible
_BORDER_RE = re.compile(r"(?:^|;)\s*border(?:-(?:top|right|bottom|left))?\s*:\s*([^;]+)", re.IGNORECASE)

# Expression régulière pour détecter background-color
_BG_COLOR_RE = re.compile(r"(?:^|;)\s*background-color\s*:\s*([^;]+)", re.IGNORECASE)

# Expression régulière pour détecter color
_COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.IGNORECASE)

# Couleurs transparentes / inherit à ignorer
_TRANSPARENT_RE = re.compile(r"^\s*(transparent|rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\))\s*$", re.IGNORECASE)
_INHERIT_RE = re.compile(r"^\s*(inherit|initial|unset|revert)\s*$", re.IGNORECASE)
_CURRENT_COLOR_RE = re.compile(r"^\s*currentColor\s*$", re.IGNORECASE)

# Dimensions nulles
_ZERO_DIMENSION_RE = re.compile(r"^0(px|em|rem|%|pt|pc|in|cm|mm|ex|ch|vw|vh|vmin|vmax)?$", re.IGNORECASE)


def _selector_for(soup: BeautifulSoup, element: Tag) -> str:
    """Construit un sélecteur lisible et relativement stable pour un élément."""
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"
    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(c) for c in classes[:2])}"
    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass
    return element.name or "élément inconnu"


def _is_focusable_element(element: Tag) -> bool:
    """Vérifie si un élément peut recevoir le focus selon RGAA 10.7."""
    tag = element.name.lower() if element.name else ""

    # Éléments nativement focusables
    if tag in _FOCUSABLE_TAGS:
        # <a> sans href n'est pas focusable
        if tag == "a" and not element.has_attr("href"):
            return False
        # <input type="hidden"> n'est pas focusable
        if tag == "input" and element.get("type", "").lower() == "hidden":
            return False
        # <details> est focusable seulement s'il a un <summary>
        if tag == "details" and not element.find("summary"):
            return False
        # <area> focusable seulement dans une map
        if tag == "area" and not element.find_parent("map"):
            return False
        return True

    # Élément avec tabindex >= 1
    tabindex = element.get("tabindex")
    if tabindex is not None:
        try:
            return int(tabindex) >= 1
        except (ValueError, TypeError):
            pass

    # Contenteditable
    if element.has_attr("contenteditable"):
        editable = element.get("contenteditable", "").lower()
        if editable in ("true", "plaintext-only"):
            return True

    return False


def _inline_style(element: Tag) -> str:
    """Récupère le style en ligne d'un élément."""
    value = element.get("style", "")
    return value if isinstance(value, str) else ""


def _extract_stylesheet_rules(html_source: str) -> list[tuple[str, str]]:
    """Extrait les règles CSS simples des blocs <style>."""
    rules: list[tuple[str, str]] = []
    for block_index, block in enumerate(re.findall(r"<style\b[^>]*>(.*?)</style\s*>", html_source, re.I | re.S), 1):
        for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            selector = selector.strip()
            declarations = declarations.strip()
            if selector and declarations and not selector.startswith("@"):
                rules.append((f"style[{block_index}] {selector}", declarations))
    return rules


def _extract_focus_rules(html_source: str) -> list[tuple[str, str]]:
    """Extrait les règles CSS pour :focus et :focus-visible."""
    rules: list[tuple[str, str]] = []
    for block_index, block in enumerate(re.findall(r"<style\b[^>]*>(.*?)</style\s*>", html_source, re.I | re.S), 1):
        # Pattern pour :focus et :focus-visible
        pattern = r"([^{}]+):focus(?:-visible)?\s*\{([^{}]*)\}"
        for selector, declarations in re.findall(pattern, block, re.IGNORECASE):
            selector = selector.strip()
            declarations = declarations.strip()
            if selector and declarations and not selector.startswith("@"):
                rules.append((f"style[{block_index}] {selector}:focus", declarations))
    return rules


def _has_outline_visible(style: str) -> tuple[bool, str | None]:
    """Vérifie si l'élément a un outline visible (pas none, pas 0)."""
    match = _OUTLINE_NONE_RE.search(style)
    if match:
        # outline: none ou outline: 0 détecté
        return False, f"outline: {match.group(1)}"

    # Chercher une déclaration outline explicite
    outline_match = re.search(r"(?:^|;)\s*outline\s*:\s*([^;]+)", style, re.IGNORECASE)
    if outline_match:
        value = outline_match.group(1).strip().lower()
        if value and value not in ("none", "0", "0px", "0em", "0rem", "0%"):
            return True, value

    return False, None


def _has_outline_offset_negative(style: str) -> tuple[bool, str | None]:
    """Vérifie si outline-offset est négatif (cache le focus)."""
    match = _OUTLINE_OFFSET_NEGATIVE_RE.search(style)
    if match:
        return True, match.group(1)
    return False, None


def _has_box_shadow_focus(style: str) -> tuple[bool, str | None]:
    """Vérifie si box-shadow est utilisé comme indicateur de focus."""
    match = _BOX_SHADOW_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and "none" not in value:
            # Vérifier que ce n'est pas une ombre décorative trop subtile
            # Une ombre de focus typique a au moins un offset et un blur
            return True, value
    return False, None


def _has_border_focus(style: str) -> tuple[bool, str | None]:
    """Vérifie si border est utilisé comme indicateur de focus."""
    match = _BORDER_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and "none" not in value:
            first = value.split()[0] if value.split() else value
            if not _ZERO_DIMENSION_RE.match(first):
                return True, value
    return False, None


def _has_background_focus(style: str) -> tuple[bool, str | None]:
    """Vérifie si background-color change au focus."""
    match = _BG_COLOR_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and value not in ("transparent", "inherit", "initial", "unset", "revert"):
            if not _TRANSPARENT_RE.match(value) and not _INHERIT_RE.match(value):
                return True, value
    return False, None


def _has_visual_focus_indicator(style: str) -> tuple[bool, list[str]]:
    """Vérifie si l'élément a un indicateur visuel de focus."""
    indicators = []

    has_outline, outline_val = _has_outline_visible(style)
    if has_outline:
        indicators.append(f"outline: {outline_val}")

    has_box_shadow, shadow_val = _has_box_shadow_focus(style)
    if has_box_shadow:
        indicators.append(f"box-shadow: {shadow_val}")

    has_border, border_val = _has_border_focus(style)
    if has_border:
        indicators.append(f"border: {border_val}")

    has_bg, bg_val = _has_background_focus(style)
    if has_bg:
        indicators.append(f"background-color: {bg_val}")

    return len(indicators) > 0, indicators


def _get_color_value(style: str) -> str | None:
    """Extrait la valeur de la propriété color."""
    match = _COLOR_RE.search(style)
    if match:
        return match.group(1).strip()
    return None


def _has_explicit_outline_none_in_stylesheet(focus_rules: list[tuple[str, str]], element: Tag) -> bool:
    """Vérifie si une règle CSS force outline: none sur cet élément au focus."""
    tag = element.name.lower() if element.name else ""
    classes = element.get("class", [])
    class_selectors = [f".{c}" for c in classes] if isinstance(classes, list) else []
    element_id = element.get("id")
    id_selector = f"#{element_id}" if element_id else ""

    for selector, declarations in focus_rules:
        # Vérifier si le sélecteur peut correspondre à notre élément
        selector_lower = selector.lower()
        matches = False
        if tag and tag in selector_lower:
            matches = True
        if class_selectors and any(c in selector_lower for c in class_selectors):
            matches = True
        if id_selector and id_selector in selector_lower:
            matches = True
        if selector_lower in (":focus", "*:focus", "*:focus-visible"):
            matches = True

        if matches:
            if _OUTLINE_NONE_RE.search(declarations):
                return True
    return False


def _parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse une couleur CSS simple en RGB."""
    color_str = color_str.strip().lower()

    named_colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
        "silver": (192, 192, 192),
        "maroon": (128, 0, 0),
        "olive": (128, 128, 0),
        "purple": (128, 0, 128),
        "teal": (0, 128, 128),
        "navy": (0, 0, 128),
        "fuchsia": (255, 0, 255),
        "aqua": (0, 255, 255),
        "lime": (0, 255, 0),
        "yellow": (255, 255, 0),
    }

    if color_str in named_colors:
        return named_colors[color_str]

    if color_str.startswith("#"):
        hex_val = color_str[1:]
        if len(hex_val) == 3:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            return (r, g, b)
        elif len(hex_val) == 6:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            return (r, g, b)

    rgb_match = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_str)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

    rgba_match = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)", color_str)
    if rgba_match:
        r, g, b = int(rgba_match.group(1)), int(rgba_match.group(2)), int(rgba_match.group(3))
        return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

    return None


def _luminance(r: int, g: int, b: int) -> float:
    """Calcule la luminance relative selon WCAG."""

    def channel(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """Calcule le ratio de contraste entre deux couleurs."""
    l1 = _luminance(*color1)
    l2 = _luminance(*color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _get_focus_colors_from_stylesheet(
    focus_rules: list[tuple[str, str]], element: Tag
) -> tuple[str | None, list[str] | None]:
    """Tente de récupérer les couleurs de focus depuis les règles CSS."""
    tag = element.name.lower() if element.name else ""
    classes = element.get("class", [])
    class_selectors = [f".{c}" for c in classes] if isinstance(classes, list) else []
    element_id = element.get("id")
    id_selector = f"#{element_id}" if element_id else ""

    for selector, declarations in focus_rules:
        selector_lower = selector.lower()
        matches = False
        if tag and tag in selector_lower:
            matches = True
        if class_selectors and any(c in selector_lower for c in class_selectors):
            matches = True
        if id_selector and id_selector in selector_lower:
            matches = True
        if selector_lower in (":focus", "*:focus", "*:focus-visible"):
            matches = True

        if matches:
            bg_color = None
            match = _BG_COLOR_RE.search(declarations)
            if match:
                value = match.group(1).strip().lower()
                if value and value not in ("transparent", "inherit", "initial", "unset", "revert"):
                    if not _TRANSPARENT_RE.match(value) and not _INHERIT_RE.match(value):
                        bg_color = value

            _ = _get_color_value(declarations)  # Not used currently

            indicators = []
            if _has_outline_visible(declarations)[0]:
                indicators.append("outline")
            if _has_box_shadow_focus(declarations)[0]:
                indicators.append("box-shadow")
            if _has_border_focus(declarations)[0]:
                indicators.append("border")
            if bg_color:
                indicators.append("background-color")

            return bg_color, indicators if indicators else None

    return None, None


def _get_element_colors(soup: BeautifulSoup, element: Tag) -> tuple[str | None, str | None]:
    """Récupère la couleur de texte et la couleur de fond de l'élément (ou héritées)."""
    text_color = None
    bg_color = None

    # D'abord le style en ligne de l'élément
    style = _inline_style(element)
    if style:
        text_color = _get_color_value(style)
        match = _BG_COLOR_RE.search(style)
        if match:
            value = match.group(1).strip().lower()
            if value and value not in ("transparent", "inherit", "initial", "unset", "revert"):
                if not _TRANSPARENT_RE.match(value) and not _INHERIT_RE.match(value):
                    bg_color = value

    # Ensuite les ancêtres
    for ancestor in element.parents:
        if not isinstance(ancestor, Tag):
            continue
        if text_color and bg_color:
            break
        ancestor_style = _inline_style(ancestor)
        if ancestor_style:
            if not text_color:
                tc = _get_color_value(ancestor_style)
                if tc and tc.lower() not in ("inherit", "initial", "unset", "revert", "currentcolor"):
                    text_color = tc
            if not bg_color:
                match = _BG_COLOR_RE.search(ancestor_style)
                if match:
                    value = match.group(1).strip().lower()
                    if value and value not in ("transparent", "inherit", "initial", "unset", "revert"):
                        if not _TRANSPARENT_RE.match(value) and not _INHERIT_RE.match(value):
                            bg_color = value

    return text_color, bg_color


def _check_focus_contrast(
    element: Tag, focus_indicators: list[str], focus_bg_color: str | None, text_color: str | None, bg_color: str | None
) -> tuple[bool | None, float | None, str]:
    """
    Vérifie si l'indicateur de focus a un contraste >= 3:1.
    Retourne (passed, ratio, message).
    """
    # Si on a un background-color au focus, vérifier le contraste avec la couleur du texte
    if focus_bg_color and text_color:
        focus_bg_rgb = _parse_color(focus_bg_color)
        text_rgb = _parse_color(text_color)
        if focus_bg_rgb and text_rgb:
            ratio = _contrast_ratio(focus_bg_rgb, text_rgb)
            passed = ratio >= 3.0
            return passed, ratio, f"Contraste focus background/text: {ratio:.2f}:1"

    # Si on a un outline ou border, vérifier le contraste avec le fond
    if "outline" in str(focus_indicators) or "border" in str(focus_indicators):
        # Pour outline/border, on a besoin de la couleur de l'outline/border
        # Ce n'est pas directement disponible, on essaie de la déduire
        pass

    # Si on a box-shadow, vérifier le contraste avec le fond
    if "box-shadow" in str(focus_indicators):
        pass

    # Pas assez d'infos pour calculer automatiquement
    msg = "Contraste non vérifiable automatiquement (insuffisamment d'informations sur les couleurs de focus)"
    return None, None, msg


class Test1071(RGAATest):
    """Test 10.7.1 : Pour chaque élément recevant le focus, la prise de focus est visible."""

    test_id = "10.7.1"
    criterion_id = "10.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)
        html_source = getattr(context, "html_source", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.7.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        if not isinstance(html_source, str) or not html_source.strip():
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible pour analyser les styles.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # Trouver tous les éléments focusables dans le document
        focusable_elements = [elem for elem in soup.find_all(True) if _is_focusable_element(elem)]

        if not focusable_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun élément focusable détecté dans la page.",
                tested_elements=0,
            )

        # Extraire les règles CSS pour :focus
        focus_rules = _extract_focus_rules(html_source)

        findings: list[Finding] = []
        elements_with_issues = 0

        for element in focusable_elements:
            selector = _selector_for(soup, element)
            element_findings: list[Finding] = []

            # 1. Vérifier le style en ligne pour outline: none
            inline_style = _inline_style(element)
            has_outline_none = _OUTLINE_NONE_RE.search(inline_style)
            has_outline_offset_neg = _OUTLINE_OFFSET_NEGATIVE_RE.search(inline_style)

            # 2. Vérifier les règles CSS :focus pour outline: none
            css_outline_none = _has_explicit_outline_none_in_stylesheet(focus_rules, element)

            # 3. Vérifier la présence d'indicateurs visuels de focus
            # Dans le style en ligne (rare pour :focus, mais possible pour d'autres états)
            has_inline_indicator, inline_indicators = _has_visual_focus_indicator(inline_style)

            # Dans les règles CSS :focus
            css_focus_bg, css_focus_indicators = _get_focus_colors_from_stylesheet(focus_rules, element)

            # 4. Déterminer si le focus natif est supprimé
            native_focus_removed = has_outline_none or has_outline_offset_neg or css_outline_none

            # 5. Vérifier s'il y a un indicateur visuel d'auteur au focus
            has_author_focus_style = has_inline_indicator or (
                css_focus_indicators is not None and len(css_focus_indicators) > 0
            )

            # Récupérer les couleurs de l'élément pour vérification de contraste
            text_color, bg_color = _get_element_colors(soup, element)

            if native_focus_removed and not has_author_focus_style:
                # Échec certain : focus natif supprimé et pas de style d'auteur
                elements_with_issues += 1
                element_findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément focusable <{element.name}> a son focus natif supprimé "
                            "(outline: none ou outline-offset négatif) sans style de focus "
                            "de remplacement défini par l'auteur."
                        ),
                        recommendation=(
                            "Rétablir l'outline natif du navigateur ou définir un style de focus "
                            "visible (outline, box-shadow, border, ou changement de background-color) "
                            "avec un contraste d'au moins 3:1."
                        ),
                        evidence={
                            "element_tag": element.name,
                            "native_focus_removed": True,
                            "outline_none_inline": bool(has_outline_none),
                            "outline_offset_negative": bool(has_outline_offset_neg),
                            "outline_none_in_css": css_outline_none,
                            "author_focus_style": False,
                            "test_id": self.test_id,
                            "risk_type": "native_focus_removed_no_replacement",
                        },
                    )
                )

            elif native_focus_removed and has_author_focus_style:
                # Focus natif supprimé mais style d'auteur présent -> vérifier le contraste
                elements_with_issues += 1
                all_indicators = inline_indicators + (css_focus_indicators or [])
                passed, ratio, msg = _check_focus_contrast(element, all_indicators, css_focus_bg, text_color, bg_color)

                if passed is False:
                    # Contraste insuffisant
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a un style de focus d'auteur "
                                f"mais le contraste est insuffisant ({ratio:.2f}:1 < 3:1)."
                            ),
                            recommendation=(
                                "Augmenter le contraste de l'indicateur de focus pour atteindre "
                                "au moins 3:1 par rapport aux couleurs adjacentes."
                            ),
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": True,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "contrast_ratio": round(ratio, 2),
                                "required_ratio": "3:1",
                                "passed": False,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_insufficient",
                            },
                        )
                    )
                elif passed is True:
                    # Contraste suffisant
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a un style de focus d'auteur "
                                f"avec contraste suffisant ({ratio:.2f}:1 >= 3:1)."
                            ),
                            recommendation=None,
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": True,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "contrast_ratio": round(ratio, 2),
                                "required_ratio": "3:1",
                                "passed": True,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_sufficient",
                            },
                        )
                    )
                else:
                    # Ne peut pas vérifier automatiquement -> NEEDS_REVIEW
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a son focus natif supprimé "
                                "mais possède un style de focus d'auteur. "
                                "Impossible de vérifier automatiquement le contraste."
                            ),
                            recommendation=(
                                "Vérifier manuellement que l'indicateur de focus a un contraste "
                                "d'au moins 3:1 par rapport aux couleurs adjacentes."
                            ),
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": True,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "text_color": text_color,
                                "background_color": bg_color,
                                "needs_manual_check": True,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_needs_review",
                            },
                        )
                    )

            elif not native_focus_removed and not has_author_focus_style:
                # Focus natif présumé présent (pas de outline: none détecté) et pas de style d'auteur
                # Le focus natif du navigateur devrait être visible, mais on ne peut pas en être certain statiquement
                # On signale en NEEDS_REVIEW pour vérification manuelle
                element_findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément focusable <{element.name}> n'a pas de outline: ni de style "
                            "de focus d'auteur détecté statiquement. Le focus natif du navigateur "
                            "devrait être visible mais nécessite une vérification manuelle."
                        ),
                        recommendation=(
                            "Vérifier manuellement dans le navigateur que la prise de focus est "
                            "visiblement indiquée (outline par défaut du navigateur ou style personnalisé) "
                            "et que le contraste est d'au moins 3:1."
                        ),
                        evidence={
                            "element_tag": element.name,
                            "native_focus_removed": False,
                            "author_focus_style": False,
                            "outline_none_inline": bool(has_outline_none),
                            "outline_offset_negative": bool(has_outline_offset_neg),
                            "outline_none_in_css": css_outline_none,
                            "needs_manual_check": True,
                            "test_id": self.test_id,
                            "risk_type": "native_focus_needs_verification",
                        },
                    )
                )

            else:
                # Focus natif préservé ET style d'auteur présent -> vérifier le contraste du style d'auteur
                all_indicators = inline_indicators + (css_focus_indicators or [])
                passed, ratio, msg = _check_focus_contrast(element, all_indicators, css_focus_bg, text_color, bg_color)

                if passed is False:
                    elements_with_issues += 1
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a un style de focus d'auteur "
                                f"mais le contraste est insuffisant ({ratio:.2f}:1 < 3:1)."
                            ),
                            recommendation=(
                                "Augmenter le contraste de l'indicateur de focus pour atteindre "
                                "au moins 3:1 par rapport aux couleurs adjacentes."
                            ),
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": False,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "contrast_ratio": round(ratio, 2),
                                "required_ratio": "3:1",
                                "passed": False,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_insufficient",
                            },
                        )
                    )
                elif passed is True:
                    # Contraste suffisant
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a un style de focus d'auteur "
                                f"avec contraste suffisant ({ratio:.2f}:1 >= 3:1)."
                            ),
                            recommendation=None,
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": False,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "contrast_ratio": round(ratio, 2),
                                "required_ratio": "3:1",
                                "passed": True,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_sufficient",
                            },
                        )
                    )
                else:
                    # Ne peut pas vérifier automatiquement
                    element_findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"L'élément focusable <{element.name}> a un style de focus d'auteur. "
                                "Impossible de vérifier automatiquement le contraste."
                            ),
                            recommendation=(
                                "Vérifier manuellement que l'indicateur de focus a un contraste "
                                "d'au moins 3:1 par rapport aux couleurs adjacentes."
                            ),
                            evidence={
                                "element_tag": element.name,
                                "native_focus_removed": False,
                                "author_focus_style": True,
                                "focus_indicators": all_indicators,
                                "focus_background_color": css_focus_bg,
                                "text_color": text_color,
                                "background_color": bg_color,
                                "needs_manual_check": True,
                                "test_id": self.test_id,
                                "risk_type": "focus_contrast_needs_review",
                            },
                        )
                    )

            findings.extend(element_findings)

        # Analyser aussi les règles CSS internes pour détecter des outline: none globaux
        css_findings = _analyze_stylesheet_for_focus_issues(html_source, self.test_id, focus_rules)
        findings.extend(css_findings)

        # Déterminer le statut global
        # Échecs certains :
        # - native_focus_removed_no_replacement : toujours un échec (focus natif supprimé sans remplacement)
        # - focus_contrast_insufficient avec passed=False : contraste insuffisant vérifié
        fail_findings = [
            f
            for f in findings
            if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"
            or (f.evidence.get("risk_type") == "focus_contrast_insufficient" and f.evidence.get("passed") is False)
        ]

        # Besoin de révision : needs_manual_check ou risques stylesheet
        needs_review_findings = [
            f
            for f in findings
            if f.evidence.get("needs_manual_check", False)
            or f.evidence.get("risk_type")
            in {
                "stylesheet_outline_none_global",
                "stylesheet_focus_style_suspicious",
            }
        ]

        # PASS certains : focus_contrast_sufficient ou native_focus_preserved_with_author_style
        pass_findings = [
            f
            for f in findings
            if f.evidence.get("risk_type") in {"focus_contrast_sufficient"} and f.evidence.get("passed") is True
        ]

        if fail_findings:
            status = TestStatus.FAIL
            summary = (
                f"{len(fail_findings)} non-conformité(s) certaine(s) de focus visible détectée(s) sur "
                f"{len(focusable_elements)} élément(s) focusable(s). "
                f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style."
            )
        elif needs_review_findings or css_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(focusable_elements)} élément(s) focusable(s) examiné(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s) pour la visibilité du focus. "
                f"{len(css_findings)} risque(s) potentiel(s) dans les feuilles de style. "
                "La validation exige un contrôle manuel de la visibilité du focus (critère 10.7.1)."
            )
        elif pass_findings and len(pass_findings) == len(focusable_elements):
            status = TestStatus.PASS
            summary = (
                f"Tous les {len(focusable_elements)} élément(s) focusable(s) ont un focus visible "
                "avec contraste suffisant (>= 3:1)."
            )
        else:
            # Cas mixte ou indéterminé
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(focusable_elements)} élément(s) focusable(s) examiné(s). "
                "La validation exige un contrôle manuel de la visibilité du focus pour chaque élément."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(focusable_elements),
            metadata={
                "total_focusable_elements": len(focusable_elements),
                "elements_with_issues": elements_with_issues,
                "potential_issues": len(findings),
                "fail_conditions": len(fail_findings),
                "needs_review_conditions": len(needs_review_findings),
                "pass_conditions": len(pass_findings),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que chaque élément focusable a une indication de focus visible",
                    "vérifier que le contraste de l'indicateur de focus est >= 3:1",
                    "vérifier que le focus natif n'est pas supprimé sans remplacement",
                ],
                "manual_check_for": "critère 10.7.1 - visibilité de la prise de focus",
            },
        )


def _analyze_stylesheet_for_focus_issues(
    html_source: str,
    test_id: str,
    focus_rules: list[tuple[str, str]],
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style pour détecter des problèmes de focus."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    # 1. Détecter outline: none ou outline: 0 global
    for selector, declarations in rules:
        if _OUTLINE_NONE_RE.search(declarations):
            # Vérifier si c'est dans un contexte :focus
            if ":focus" in selector.lower():
                findings.append(
                    Finding(
                        element=selector[:160],
                        message=(
                            f"Règle CSS avec outline: none/0 sur :focus : '{selector}'. "
                            "Ceci supprime l'indicateur de focus natif du navigateur."
                        ),
                        recommendation=(
                            "Supprimer outline: none sur :focus ou remplacer par un style de focus "
                            "visible (outline personnalisé, box-shadow, border, background-color) "
                            "avec contraste >= 3:1."
                        ),
                        evidence={
                            "selector": selector[:160],
                            "declarations": declarations[:300],
                            "source_type": "stylesheet",
                            "risk_type": "stylesheet_outline_none_on_focus",
                            "test_id": test_id,
                        },
                    )
                )
            else:
                # outline: none global (pas sur :focus) - suspect
                findings.append(
                    Finding(
                        element=selector[:160],
                        message=(
                            f"Règle CSS avec outline: none/0 global : '{selector}'. "
                            "Ceci peut supprimer le focus sur des éléments interactifs."
                        ),
                        recommendation=(
                            "Vérifier que cette règle ne s'applique pas aux éléments focusables, "
                            "ou la limiter aux éléments non-interactifs."
                        ),
                        evidence={
                            "selector": selector[:160],
                            "declarations": declarations[:300],
                            "source_type": "stylesheet",
                            "risk_type": "stylesheet_outline_none_global",
                            "test_id": test_id,
                        },
                    )
                )

    # 2. Détecter des styles :focus suspects (sans indicateur visuel clair)
    for selector, declarations in focus_rules:
        has_visual = (
            _has_outline_visible(declarations)[0]
            or _has_box_shadow_focus(declarations)[0]
            or _has_border_focus(declarations)[0]
            or _has_background_focus(declarations)[0]
        )
        if not has_visual:
            # Règle :focus sans indicateur visuel détectable
            findings.append(
                Finding(
                    element=selector[:160],
                    message=(
                        f"Règle CSS :focus sans indicateur visuel détecté : '{selector}'. "
                        "Vérifier qu'elle définit bien un outline, box-shadow, border, "
                        "ou background-color visible avec contraste >= 3:1."
                    ),
                    recommendation=(
                        "Ajouter un indicateur visuel de focus dans cette règle : "
                        "outline, box-shadow, border, ou background-color avec contraste >= 3:1."
                    ),
                    evidence={
                        "selector": selector[:160],
                        "declarations": declarations[:300],
                        "source_type": "stylesheet",
                        "risk_type": "stylesheet_focus_style_suspicious",
                        "test_id": test_id,
                    },
                )
            )

    return findings

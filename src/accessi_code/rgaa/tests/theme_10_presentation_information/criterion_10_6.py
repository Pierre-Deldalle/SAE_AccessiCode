from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Tags susceptibles de contenir du texte pour le contraste
_TEXT_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "button",
    "caption",
    "dd",
    "dt",
    "em",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "label",
    "legend",
    "li",
    "p",
    "small",
    "span",
    "strong",
    "summary",
    "td",
    "th",
    "textarea",
}

# Conteneurs génériques qui peuvent contenir du texte
_CONTAINER_TAGS = {"div", "section", "article", "aside", "main", "header", "footer", "nav"}

# Expressions régulières pour détecter les propriétés CSS
_COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.IGNORECASE)
_TEXT_DECORATION_RE = re.compile(r"(?:^|;)\s*text-decoration\s*:\s*([^;]+)", re.IGNORECASE)
_BORDER_RE = re.compile(r"(?:^|;)\s*border(?:-(?:top|right|bottom|left))?\s*:\s*([^;]+)", re.IGNORECASE)
_BORDER_BOTTOM_RE = re.compile(r"(?:^|;)\s*border-bottom\s*:\s*([^;]+)", re.IGNORECASE)
_BOX_SHADOW_RE = re.compile(r"(?:^|;)\s*box-shadow\s*:\s*([^;]+)", re.IGNORECASE)
_OUTLINE_RE = re.compile(r"(?:^|;)\s*outline\s*:\s*([^;]+)", re.IGNORECASE)
_BACKGROUND_COLOR_RE = re.compile(r"(?:^|;)\s*background-color\s*:\s*([^;]+)", re.IGNORECASE)
# Pour détecter les dimensions nulles (0, 0px, 0em, etc.) sans confondre avec #000
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


def _is_link(element: Tag) -> bool:
    """Vérifie si un élément est un lien (a ou role=link)."""
    if element.name == "a" and element.has_attr("href"):
        return True
    role = element.get("role")
    if isinstance(role, str) and role.strip().lower() == "link":
        return True
    return False


def _has_rendered_text(element: Tag) -> bool:
    """Vérifie la présence de texte utile dans l'élément."""
    if element.name in {"script", "style", "noscript", "template"}:
        return False
    text = element.get_text(" ", strip=True)
    return bool(text)


def _inline_style(element: Tag) -> str:
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


def _extract_pseudo_rules(html_source: str, pseudo_class: str) -> list[tuple[str, str]]:
    """Extrait les règles CSS pour une pseudo-classe spécifique (:hover, :focus, etc.)."""
    rules: list[tuple[str, str]] = []
    for block_index, block in enumerate(re.findall(r"<style\b[^>]*>(.*?)</style\s*>", html_source, re.I | re.S), 1):
        # Pattern pour trouver les sélecteurs avec pseudo-classe
        pattern = rf"([^{{}}]+):{pseudo_class}\s*\{{([^{{}}]*)\}}"
        for selector, declarations in re.findall(pattern, block, re.IGNORECASE):
            selector = selector.strip()
            declarations = declarations.strip()
            if selector and declarations and not selector.startswith("@"):
                rules.append((f"style[{block_index}] {selector}:{pseudo_class}", declarations))
    return rules


def _get_color_value(style: str) -> str | None:
    """Extrait la valeur de la propriété color."""
    match = _COLOR_RE.search(style)
    if match:
        return match.group(1).strip()
    return None


def _has_text_decoration_underline(style: str) -> bool:
    """Vérifie si text-decoration contient underline."""
    match = _TEXT_DECORATION_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        return "underline" in value and "none" not in value
    return False


def _has_border_indicator(style: str) -> bool:
    """Vérifie si l'élément a une bordure visible (indicateur visuel)."""
    # Vérifier border
    match = _BORDER_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        # Vérifier que ce n'est pas "none" ou une dimension nulle (0, 0px, 0em, etc.)
        # mais ne pas confondre avec des couleurs comme #000
        first = value.split()[0] if value.split() else value
        if value and "none" not in value and not _ZERO_DIMENSION_RE.match(first):
            return True
    # Vérifier border-bottom spécifiquement (souvent utilisé pour les liens)
    match = _BORDER_BOTTOM_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        first = value.split()[0] if value.split() else value
        if value and "none" not in value and not _ZERO_DIMENSION_RE.match(first):
            return True
    return False


def _has_box_shadow(style: str) -> bool:
    """Vérifie si l'élément a un box-shadow."""
    match = _BOX_SHADOW_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and "none" not in value:
            return True
    return False


def _has_outline(style: str) -> bool:
    """Vérifie si l'élément a un outline."""
    match = _OUTLINE_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and "none" not in value:
            return True
    return False


def _has_background_indicator(style: str) -> bool:
    """Vérifie si l'élément a un background-color différent (indicateur visuel)."""
    match = _BACKGROUND_COLOR_RE.search(style)
    if match:
        value = match.group(1).strip().lower()
        if value and value not in ("transparent", "inherit", "initial", "unset", "revert"):
            return True
    return False


def _has_visual_indicator_other_than_color(style: str) -> bool:
    """Vérifie si l'élément a un indicateur visuel autre que la couleur."""
    return (
        _has_text_decoration_underline(style)
        or _has_border_indicator(style)
        or _has_box_shadow(style)
        or _has_outline(style)
        or _has_background_indicator(style)
    )


def _get_surrounding_text_color(soup: BeautifulSoup, element: Tag) -> str | None:
    """Tente de trouver la couleur du texte environnant (parent ou ancêtre)."""
    for ancestor in element.parents:
        if not isinstance(ancestor, Tag):
            continue
        style = _inline_style(ancestor)
        if style:
            color = _get_color_value(style)
            if color and color.lower() not in ("inherit", "initial", "unset", "revert", "currentcolor"):
                return color
    return None


def _parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse une couleur CSS simple en RGB (supporte hex, rgb, nombres nommés basiques)."""
    color_str = color_str.strip().lower()

    # Couleurs nommées basiques
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

    # Hex: #RGB, #RRGGBB
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

    # rgb(r, g, b)
    rgb_match = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_str)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

    # rgba - ignorer l'alpha pour le contraste
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


def _check_contrast(link_color: str, surrounding_color: str) -> tuple[bool, float | None]:
    """Vérifie si le contraste entre deux couleurs est >= 3:1."""
    link_rgb = _parse_color(link_color)
    surrounding_rgb = _parse_color(surrounding_color)

    if link_rgb is None or surrounding_rgb is None:
        return False, None

    ratio = _contrast_ratio(link_rgb, surrounding_rgb)
    return ratio >= 3.0, ratio


def _get_elements_to_check(soup: BeautifulSoup, tag_set: set[str]) -> list[Tag]:
    """
    Retourne les éléments à vérifier : éléments textuels + leurs conteneurs
    avec styles en ligne qui pourraient affecter le texte.
    """
    elements_to_check: list[Tag] = []
    seen_ids: set[int] = set()

    # 1. Ajouter tous les éléments textuels
    for element in soup.find_all(list(tag_set)):
        if _has_rendered_text(element):
            elem_id = id(element)
            if elem_id not in seen_ids:
                elements_to_check.append(element)
                seen_ids.add(elem_id)

    # 2. Ajouter les conteneurs ancêtres qui ont des styles en ligne
    for element in elements_to_check[:]:
        for ancestor in element.parents:
            if not isinstance(ancestor, Tag):
                continue
            if ancestor.name in _CONTAINER_TAGS and _inline_style(ancestor):
                anc_id = id(ancestor)
                if anc_id not in seen_ids:
                    elements_to_check.append(ancestor)
                    seen_ids.add(anc_id)

    return elements_to_check


def _analyze_link_for_1061(
    soup: BeautifulSoup,
    element: Tag,
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse un lien pour le test 10.6.1."""
    if not _is_link(element):
        return []

    if not _has_rendered_text(element):
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # 1. Analyser le style en ligne du lien
    inline_style = _inline_style(element)

    # Récupérer la couleur du lien
    link_color = _get_color_value(inline_style)

    # Vérifier si le lien a un indicateur visuel autre que la couleur dans l'état par défaut
    has_visual_indicator = _has_visual_indicator_other_than_color(inline_style)

    # Vérifier les règles CSS pour :hover
    hover_rules = _extract_pseudo_rules(html_source, "hover")
    has_hover_indicator = False
    hover_details = []
    for hover_selector, hover_declarations in hover_rules:
        # Vérifier si ce sélecteur correspond à notre élément
        # (approximation simple : vérifier si le tag ou la classe correspond)
        if element.name in hover_selector or (element.get("class") and any(c in hover_selector for c in element.get("class", []))):
            if _has_visual_indicator_other_than_color(hover_declarations):
                has_hover_indicator = True
                hover_details.append(f"{hover_selector}: {hover_declarations[:100]}")

    # Vérifier les règles CSS pour :focus
    focus_rules = _extract_pseudo_rules(html_source, "focus")
    has_focus_indicator = False
    focus_details = []
    for focus_selector, focus_declarations in focus_rules:
        if element.name in focus_selector or (element.get("class") and any(c in focus_selector for c in element.get("class", []))):
            if _has_visual_indicator_other_than_color(focus_declarations):
                has_focus_indicator = True
                focus_details.append(f"{focus_selector}: {focus_declarations[:100]}")

    # Vérifier aussi les styles en ligne pour :hover et :focus (rare mais possible via style attribute)
    # Note: les pseudo-classes ne peuvent pas être dans l'attribut style, seulement dans <style>

    # Si le lien a un indicateur visuel dans l'état par défaut, il n'entre pas dans le périmètre du test 10.6.1
    if has_visual_indicator:
        return []

    # Le lien est signalé uniquement par la couleur - vérifier les 3 conditions

    # Condition 1: Contraste >= 3:1 avec le texte environnant
    surrounding_color = _get_surrounding_text_color(soup, element)
    if link_color and surrounding_color:
        has_contrast, ratio = _check_contrast(link_color, surrounding_color)
        if not has_contrast:
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Le lien n'a pas un contraste suffisant ({ratio:.2f}:1) "
                        f"entre sa couleur ({link_color}) et le texte environnant ({surrounding_color}). "
                        "Le ratio minimum requis est 3:1."
                    ),
                    recommendation=(
                        "Augmenter le contraste entre la couleur du lien et la couleur du texte environnant "
                        "pour atteindre au moins 3:1, ou ajouter un indicateur visuel (soulignement, bordure, etc.)."
                    ),
                    evidence={
                        "link_color": link_color,
                        "surrounding_color": surrounding_color,
                        "contrast_ratio": round(ratio, 2) if ratio else None,
                        "required_ratio": "3:1",
                        "test_id": test_id,
                        "condition": "contrast",
                        "passed": False,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Le lien a un contraste suffisant ({ratio:.2f}:1) "
                        f"entre sa couleur ({link_color}) et le texte environnant ({surrounding_color})."
                    ),
                    recommendation=None,
                    evidence={
                        "link_color": link_color,
                        "surrounding_color": surrounding_color,
                        "contrast_ratio": round(ratio, 2),
                        "required_ratio": "3:1",
                        "test_id": test_id,
                        "condition": "contrast",
                        "passed": True,
                    },
                )
            )
    else:
        # Impossible de vérifier le contraste automatiquement
        findings.append(
            Finding(
                element=selector,
                message=(
                    f"Le lien est signalé uniquement par la couleur (color: {link_color or 'héritée'}). "
                    "Impossible de vérifier automatiquement le contraste avec le texte environnant."
                ),
                recommendation=(
                    "Vérifier manuellement que le contraste entre la couleur du lien et le texte environnant "
                    "est d'au moins 3:1, ou ajouter un indicateur visuel (soulignement, bordure, etc.)."
                ),
                evidence={
                    "link_color": link_color,
                    "surrounding_color": surrounding_color,
                    "test_id": test_id,
                    "condition": "contrast",
                    "needs_manual_check": True,
                },
            )
        )

    # Condition 2: Indicateur visuel au survol autre qu'un changement de couleur
    if has_hover_indicator:
        findings.append(
            Finding(
                element=selector,
                message="Le lien dispose d'une indication visuelle au survol autre qu'un changement de couleur.",
                recommendation=None,
                evidence={
                    "hover_details": hover_details,
                    "test_id": test_id,
                    "condition": "hover",
                    "passed": True,
                },
            )
        )
    else:
        # Pas d'indicateur hover trouvé dans les règles correspondantes
        # Cela ne signifie pas qu'il n'y en a pas du tout (autres sélecteurs possibles) -> NEEDS_REVIEW
        findings.append(
            Finding(
                element=selector,
                message=(
                    "Aucune indication visuelle au survol détectée dans les règles CSS correspondantes. "
                    "Vérifier manuellement la présence d'un indicateur au survol (autre qu'un changement de couleur)."
                ),
                recommendation=(
                    "Ajouter un indicateur visuel au survol : soulignement (text-decoration: underline), "
                    "bordure, ombre, changement de fond, etc."
                ),
                evidence={
                    "hover_rules_checked": len(hover_rules),
                    "hover_details": hover_details[:3]
                    if hover_details
                    else "Aucune règle :hover correspondante trouvée",
                    "test_id": test_id,
                    "condition": "hover",
                    "needs_manual_check": True,
                },
            )
        )

    # Condition 3: Indicateur visuel au focus autre qu'un changement de couleur
    if has_focus_indicator:
        findings.append(
            Finding(
                element=selector,
                message="Le lien dispose d'une indication visuelle au focus autre qu'un changement de couleur.",
                recommendation=None,
                evidence={
                    "focus_details": focus_details,
                    "test_id": test_id,
                    "condition": "focus",
                    "passed": True,
                },
            )
        )
    else:
        # Pas d'indicateur focus trouvé dans les règles correspondantes
        # Cela ne signifie pas qu'il n'y en a pas du tout -> NEEDS_REVIEW
        findings.append(
            Finding(
                element=selector,
                message=(
                    "Aucune indication visuelle au focus détectée dans les règles CSS correspondantes. "
                    "Vérifier manuellement la présence d'un indicateur au focus (autre qu'un changement de couleur)."
                ),
                recommendation=(
                    "Ajouter un indicateur visuel au focus : outline, soulignement, bordure, ombre, "
                    "changement de fond, etc. (note: outline est recommandé pour l'accessibilité)."
                ),
                focus_detail = focus_details[:3] if focus_details else "Aucune regle :focus correspondante trouvee",
                evidence={
                    "focus_rules_checked": len(focus_rules),
                    "focus_details": focus_detail,
                    "test_id": test_id,
                    "condition": "focus",
                    "needs_manual_check": True,
                },
            )
        )

    return findings


def _analyze_stylesheet_for_1061(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style internes pour le test 10.6.1."""
    # Cette analyse est plus complexe car on ne peut pas facilement faire le lien
    # entre les sélecteurs CSS et les éléments du DOM sans moteur de rendu.
    # On signale les règles qui pourraient concerner des liens.
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        # Chercher les règles qui s'appliquent potentiellement aux liens
        if "a" in selector.lower() or ":link" in selector.lower() or "role" in selector.lower():
            link_color = _get_color_value(declarations)
            has_visual = _has_visual_indicator_other_than_color(declarations)

            if link_color and not has_visual:
                findings.append(
                    Finding(
                        element=selector[:160],
                        message=(
                            f"Règle CSS potentielle pour lien avec color ({link_color}) "
                            "sans indicateur visuel autre que la couleur. "
                            "Vérifier si elle s'applique à des liens et si les conditions "
                            "10.6.1 sont respectées."
                        ),
                        recommendation=(
                            "Vérifier dans le navigateur si cette règle s'applique à des liens "
                            "signalés uniquement par la couleur. Si oui, s'assurer que : "
                            "le contraste est >= 3:1, qu'il y a un indicateur au survol, "
                            "et qu'il y a un indicateur au focus."
                        ),
                        evidence={
                            "selector": selector[:160],
                            "declarations": declarations[:300],
                            "source_type": "stylesheet",
                            "risk_type": "stylesheet_link_color_only",
                            "test_id": test_id,
                            "link_color": link_color,
                        },
                    )
                )

    return findings


class Test1061(RGAATest):
    """Test 10.6.1 : Chaque lien dont la nature n'est pas évidente, signalé uniquement par la couleur,
    vérifie : contraste >= 3:1, indication visuelle au survol, indication visuelle au focus."""

    test_id = "10.6.1"
    criterion_id = "10.6"

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
                summary="Le DOM n'est pas disponible ; le test 10.6.1 nécessite l'analyse de la page.",
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

        # Trouver tous les liens dans le document
        links = [elem for elem in soup.find_all(True) if _is_link(elem)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun lien détecté dans la page.",
                tested_elements=0,
            )

        # Analyser chaque lien
        findings: list[Finding] = []
        links_with_color_only = 0

        for element in links:
            element_findings = _analyze_link_for_1061(soup, element, html_source, self.test_id)
            if element_findings:
                links_with_color_only += 1
            findings.extend(element_findings)

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_for_1061(html_source, self.test_id)
        findings.extend(css_findings)

        # Déterminer le statut
        # Échecs certains : passed=False (ex: contraste insuffisant calculable)
        fail_findings = [
            f for f in findings
            if f.evidence.get("risk_type") == "stylesheet_link_color_only"
            or (f.evidence.get("condition") in {"contrast", "hover", "focus"}
                and f.evidence.get("passed") is False)
        ]

        # Besoin de révision manuelle : needs_manual_check=True ou risques stylesheet
        needs_review_findings = [
            f for f in findings
            if f.evidence.get("needs_manual_check", False)
            or f.evidence.get("risk_type") == "stylesheet_link_color_only"
        ]

        # Logique de statut selon la priorité : FAIL > NEEDS_REVIEW > PASS
        if fail_findings:
            status = TestStatus.FAIL
            summary = (
                f"{len(fail_findings)} non-conformité(s) certaine(s) détectée(s) sur "
                f"{links_with_color_only} lien(s) signalé(s) uniquement par la couleur. "
                f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style."
            )
        elif needs_review_findings or css_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(links)} lien(s) examiné(s), "
                f"{links_with_color_only} signalé(s) uniquement par la couleur. "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s). "
                f"{len(css_findings)} risque(s) potentiel(s) dans les feuilles de style. "
                "La validation exige un contrôle manuel des 3 conditions RGAA 10.6.1."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Tous les {links_with_color_only} lien(s) signalé(s) uniquement par la couleur "
                f"respectent les 3 conditions (contraste >= 3:1, indicateur survol, indicateur focus) "
                f"sur les {len(links)} lien(s) examiné(s)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(links),
            metadata={
                "total_links": len(links),
                "links_color_only": links_with_color_only,
                "potential_issues": len(findings),
                "fail_conditions": len(fail_findings),
                "needs_review_conditions": len(needs_review_findings),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier le contraste lien/texte >= 3:1 pour les liens couleur seule",
                    "vérifier l'indicateur visuel au survol (autre que couleur)",
                    "vérifier l'indicateur visuel au focus (autre que couleur)",
                ],
                "manual_check_for": "critère 10.6.1 - liens signalés uniquement par la couleur",
            },
        )

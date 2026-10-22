from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Tags susceptibles de contenir du texte à lire
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

# Conteneurs génériques qui peuvent contenir du texte et avoir des styles risqués
_CONTAINER_TAGS = {"div", "section", "article", "aside", "main", "header", "footer", "nav"}

# Conteneurs exempts du critère (texte non redimensionnable par nature)
_EXEMPT_CONTAINERS = {"canvas"}

# Expressions régulières pour détecter les propriétés CSS
_COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.IGNORECASE)
_BG_COLOR_RE = re.compile(r"(?:^|;)\s*background-color\s*:\s*([^;]+)", re.IGNORECASE)
_BG_IMAGE_RE = re.compile(r"(?:^|;)\s*background-image\s*:\s*([^;]+)", re.IGNORECASE)
_BG_SHORTHAND_RE = re.compile(r"(?:^|;)\s*background\s*:\s*([^;]+)", re.IGNORECASE)
_TRANSPARENT_RE = re.compile(r"^\s*(transparent|rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\))\s*$", re.IGNORECASE)
_INHERIT_RE = re.compile(r"^\s*(inherit|initial|unset|revert)\s*$", re.IGNORECASE)
_CURRENT_COLOR_RE = re.compile(r"^\s*currentColor\s*$", re.IGNORECASE)


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


def _is_exempt(element: Tag) -> bool:
    """Ignore le texte dans des conteneurs exempts (ex: canvas)."""
    return element.name in _EXEMPT_CONTAINERS or element.find_parent(list(_EXEMPT_CONTAINERS)) is not None


def _has_rendered_text(element: Tag) -> bool:
    """Vérifie la présence de texte utile dans l'élément."""
    if element.name in {"script", "style", "noscript", "template"} or _is_exempt(element):
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


def _has_color_declaration(style: str) -> tuple[bool, str | None]:
    """Vérifie si une déclaration color est présente et retourne sa valeur."""
    match = _COLOR_RE.search(style)
    if match:
        value = match.group(1).strip()
        return True, value
    return False, None


def _has_bg_color_declaration(style: str) -> tuple[bool, str | None]:
    """Vérifie si une déclaration background-color est présente et retourne sa valeur."""
    # Vérifier background-color explicite
    match = _BG_COLOR_RE.search(style)
    if match:
        value = match.group(1).strip()
        return True, value
    # Vérifier dans la propriété raccourcie background
    match = _BG_SHORTHAND_RE.search(style)
    if match:
        value = match.group(1).strip()
        # Chercher une couleur dans le background shorthand
        # Format: background: color image repeat position / size
        # On cherche une valeur de couleur (pas d'url, pas de mots-clés de position)
        if _COLOR_RE.search(value) or _BG_COLOR_RE.search(value):
            return True, value
    return False, None


def _has_bg_image_declaration(style: str) -> tuple[bool, str | None]:
    """Vérifie si une déclaration background-image est présente et retourne sa valeur."""
    # Vérifier background-image explicite
    match = _BG_IMAGE_RE.search(style)
    if match:
        value = match.group(1).strip()
        if value and value != "none":
            return True, value
    # Vérifier dans la propriété raccourcie background
    match = _BG_SHORTHAND_RE.search(style)
    if match:
        value = match.group(1).strip()
        if "url(" in value:
            return True, value
    return False, None


def _is_explicit_color(value: str) -> bool:
    """Vérifie si une valeur de couleur est explicite (pas transparent, inherit, etc.)."""
    if not value:
        return False
    if _TRANSPARENT_RE.match(value):
        return False
    if _INHERIT_RE.match(value):
        return False
    if _CURRENT_COLOR_RE.match(value):
        return False
    return True


def _is_explicit_bg_color(value: str) -> bool:
    """Vérifie si une valeur de background-color est explicite."""
    if not value:
        return False
    if _TRANSPARENT_RE.match(value):
        return False
    if _INHERIT_RE.match(value):
        return False
    return True


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
    for element in elements_to_check[:]:  # Copie pour itérer sur l'original
        for ancestor in element.parents:
            if not isinstance(ancestor, Tag):
                continue
            if ancestor.name in _CONTAINER_TAGS and _inline_style(ancestor):
                anc_id = id(ancestor)
                if anc_id not in seen_ids:
                    elements_to_check.append(ancestor)
                    seen_ids.add(anc_id)

    return elements_to_check


def _check_parent_for_bg_color(soup: BeautifulSoup, element: Tag) -> tuple[bool, str | None]:
    """Vérifie si un parent a une background-color explicite."""
    for ancestor in element.parents:
        if not isinstance(ancestor, Tag):
            continue
        style = _inline_style(ancestor)
        if style:
            has_bg, value = _has_bg_color_declaration(style)
            if has_bg and _is_explicit_bg_color(value):
                return True, value
    return False, None


def _check_parent_for_color(soup: BeautifulSoup, element: Tag) -> tuple[bool, str | None]:
    """Vérifie si un parent a une color explicite."""
    for ancestor in element.parents:
        if not isinstance(ancestor, Tag):
            continue
        style = _inline_style(ancestor)
        if style:
            has_color, value = _has_color_declaration(style)
            if has_color and _is_explicit_color(value):
                return True, value
    return False, None


def _analyze_element_for_1051(
    soup: BeautifulSoup,
    element: Tag,
    test_id: str,
) -> list[Finding]:
    """Analyse un élément pour le test 10.5.1 : color sans background-color."""
    style = _inline_style(element)
    if not style:
        return []

    if _is_exempt(element):
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # Vérifier si l'élément a une déclaration color explicite
    has_color, color_value = _has_color_declaration(style)
    if not has_color or not _is_explicit_color(color_value):
        return []

    # Vérifier si l'élément a une background-color explicite
    has_bg_color, bg_value = _has_bg_color_declaration(style)
    if has_bg_color and _is_explicit_bg_color(bg_value):
        return []  # OK : color + background-color sur le même élément

    # Vérifier les parents pour background-color hérité
    parent_has_bg, parent_bg_value = _check_parent_for_bg_color(soup, element)
    if parent_has_bg:
        return []  # OK : background-color hérité d'un parent

    # Échec : color sans background-color
    findings.append(
        Finding(
            element=selector,
            message=(
                f"L'élément a une couleur de police explicite (color: {color_value}) "
                "mais aucune couleur de fond (background-color) n'est définie "
                "sur l'élément ni héritée d'un parent."
            ),
            recommendation=(
                "Ajouter une déclaration background-color sur cet élément "
                "ou sur un parent, ou utiliser une valeur de couleur par défaut "
                "qui garantit le contraste."
            ),
            evidence={
                "property": "color",
                "color_value": color_value,
                "inline_style": style[:300],
                "test_id": test_id,
                "risk_type": "color_without_background",
            },
        )
    )

    return findings


def _analyze_stylesheet_for_1051(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style internes pour le test 10.5.1."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        # Vérifier si la règle a color sans background-color
        has_color, color_value = _has_color_declaration(declarations)
        if not has_color or not _is_explicit_color(color_value):
            continue

        has_bg_color, bg_value = _has_bg_color_declaration(declarations)
        if has_bg_color and _is_explicit_bg_color(bg_value):
            continue  # OK

        # Pour les feuilles de style, on ne peut pas vérifier l'héritage facilement
        # On signale en NEEDS_REVIEW
        findings.append(
            Finding(
                element=selector[:160],
                message=(
                    f"Règle CSS avec color ({color_value}) sans background-color explicite. "
                    "Vérifier si une couleur de fond est héritée d'un parent dans le rendu final."
                ),
                recommendation=(
                    "Vérifier dans le navigateur si cet élément a un fond coloré "
                    "lorsqu'il est rendu, ou ajouter background-color explicitement."
                ),
                evidence={
                    "selector": selector[:160],
                    "declarations": declarations[:300],
                    "source_type": "stylesheet",
                    "risk_type": "stylesheet_color_without_background",
                    "test_id": test_id,
                    "color_value": color_value,
                },
            )
        )

    return findings


def _analyze_element_for_1052(
    soup: BeautifulSoup,
    element: Tag,
    test_id: str,
) -> list[Finding]:
    """Analyse un élément pour le test 10.5.2 : background-color sans color."""
    style = _inline_style(element)
    if not style:
        return []

    if _is_exempt(element):
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # Vérifier si l'élément a une déclaration background-color explicite
    has_bg_color, bg_value = _has_bg_color_declaration(style)
    if not has_bg_color or not _is_explicit_bg_color(bg_value):
        return []

    # Vérifier si l'élément a une color explicite
    has_color, color_value = _has_color_declaration(style)
    if has_color and _is_explicit_color(color_value):
        return []  # OK : background-color + color sur le même élément

    # Vérifier les parents pour color hérité
    parent_has_color, parent_color_value = _check_parent_for_color(soup, element)
    if parent_has_color:
        return []  # OK : color hérité d'un parent

    # Échec : background-color sans color
    findings.append(
        Finding(
            element=selector,
            message=(
                f"L'élément a une couleur de fond explicite (background-color: {bg_value}) "
                "mais aucune couleur de police (color) n'est définie "
                "sur l'élément ni héritée d'un parent."
            ),
            recommendation=(
                "Ajouter une déclaration color sur cet élément "
                "ou sur un parent, ou utiliser une valeur de couleur par défaut "
                "qui garantit le contraste."
            ),
            evidence={
                "property": "background-color",
                "bg_color_value": bg_value,
                "inline_style": style[:300],
                "test_id": test_id,
                "risk_type": "background_without_color",
            },
        )
    )

    return findings


def _analyze_stylesheet_for_1052(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style internes pour le test 10.5.2."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        # Vérifier si la règle a background-color sans color
        has_bg_color, bg_value = _has_bg_color_declaration(declarations)
        if not has_bg_color or not _is_explicit_bg_color(bg_value):
            continue

        has_color, color_value = _has_color_declaration(declarations)
        if has_color and _is_explicit_color(color_value):
            continue  # OK

        # Pour les feuilles de style, on ne peut pas vérifier l'héritage facilement
        findings.append(
            Finding(
                element=selector[:160],
                message=(
                    f"Règle CSS avec background-color ({bg_value}) sans color explicite. "
                    "Vérifier si une couleur de police est héritée d'un parent dans le rendu final."
                ),
                recommendation=(
                    "Vérifier dans le navigateur si cet élément a une couleur de texte définie "
                    "lorsqu'il est rendu, ou ajouter color explicitement."
                ),
                evidence={
                    "selector": selector[:160],
                    "declarations": declarations[:300],
                    "source_type": "stylesheet",
                    "risk_type": "stylesheet_background_without_color",
                    "test_id": test_id,
                    "bg_color_value": bg_value,
                },
            )
        )

    return findings


def _analyze_element_for_1053(
    soup: BeautifulSoup,
    element: Tag,
    test_id: str,
) -> list[Finding]:
    """Analyse un élément pour le test 10.5.3 : background-image sans background-color fallback."""
    style = _inline_style(element)
    if not style:
        return []

    if _is_exempt(element):
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # Vérifier si l'élément a une déclaration background-image
    has_bg_image, bg_image_value = _has_bg_image_declaration(style)
    if not has_bg_image:
        return []

    # Vérifier si l'élément a une background-color explicite (fallback)
    has_bg_color, bg_value = _has_bg_color_declaration(style)
    if has_bg_color and _is_explicit_bg_color(bg_value):
        return []  # OK : background-image + background-color fallback sur le même élément

    # Vérifier les parents pour background-color hérité
    parent_has_bg, parent_bg_value = _check_parent_for_bg_color(soup, element)
    if parent_has_bg:
        return []  # OK : background-color hérité d'un parent

    # Échec : background-image sans background-color fallback
    findings.append(
        Finding(
            element=selector,
            message=(
                f"L'élément utilise une image d'arrière-plan (background-image: {bg_image_value[:50]}...) "
                "mais aucune couleur de fond de secours (background-color) n'est définie "
                "sur l'élément ni héritée d'un parent. Si l'image ne se charge pas, "
                "le texte peut devenir illisible."
            ),
            recommendation=(
                "Ajouter une déclaration background-color sur cet élément "
                "ou sur un parent, avec une couleur assurant un contraste suffisant "
                "avec la couleur du texte, pour garantir la lisibilité si l'image échoue."
            ),
            evidence={
                "property": "background-image",
                "bg_image_value": bg_image_value[:100],
                "inline_style": style[:300],
                "test_id": test_id,
                "risk_type": "background_image_without_fallback",
            },
        )
    )

    return findings


def _analyze_stylesheet_for_1053(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style internes pour le test 10.5.3."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        # Vérifier si la règle a background-image sans background-color
        has_bg_image, bg_image_value = _has_bg_image_declaration(declarations)
        if not has_bg_image:
            continue

        has_bg_color, bg_value = _has_bg_color_declaration(declarations)
        if has_bg_color and _is_explicit_bg_color(bg_value):
            continue  # OK

        # Pour les feuilles de style, on ne peut pas vérifier l'héritage facilement
        findings.append(
            Finding(
                element=selector[:160],
                message=(
                    f"Règle CSS avec background-image ({bg_image_value[:50]}...) "
                    "sans background-color de secours explicite. "
                    "Vérifier si une couleur de fond est héritée d'un parent dans le rendu final."
                ),
                recommendation=(
                    "Vérifier dans le navigateur si cet élément a une couleur de fond de secours "
                    "lorsqu'il est rendu, ou ajouter background-color explicitement "
                    "pour garantir la lisibilité si l'image échoue."
                ),
                evidence={
                    "selector": selector[:160],
                    "declarations": declarations[:300],
                    "source_type": "stylesheet",
                    "risk_type": "stylesheet_background_image_without_fallback",
                    "test_id": test_id,
                    "bg_image_value": bg_image_value[:100],
                },
            )
        )

    return findings


class Test1051(RGAATest):
    """Test 10.5.1 : Chaque déclaration CSS de couleur de police est accompagnée
    d'une déclaration de couleur de fond."""

    test_id = "10.5.1"
    criterion_id = "10.5"

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
                summary="Le DOM n'est pas disponible ; le test 10.5.1 nécessite l'analyse de la page.",
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

        # Sélectionner les éléments à vérifier (textuels + leurs conteneurs avec styles)
        elements_to_check = _get_elements_to_check(soup, _TEXT_TAGS)

        findings: list[Finding] = []
        for element in elements_to_check:
            findings.extend(_analyze_element_for_1051(soup, element, self.test_id))

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_for_1051(html_source, self.test_id)
        findings.extend(css_findings)

        # Déterminer le statut
        if findings:
            # Si des risques certains sont détectés (inline styles), c'est un FAIL
            inline_risks = [f for f in findings if f.evidence.get("risk_type") != "stylesheet_color_without_background"]
            if inline_risks:
                status = TestStatus.FAIL
                summary = (
                    f"{len(inline_risks)} élément(s) avec color sans background-color détecté(s) "
                    "dans les styles en ligne. "
                    f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
            else:
                # Risques seulement dans les feuilles de style = NEEDS_REVIEW
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    "Analyse statique terminée : "
                    f"{len(elements_to_check)} élément(s) examiné(s), "
                    f"{len(findings)} risque(s) potentiel(s) détecté(s) dans les feuilles de style. "
                    "Aucun risque certain dans les styles en ligne. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
        else:
            status = TestStatus.PASS
            summary = (
                f"Aucun risque détecté : toutes les déclarations color "
                f"ont une background-color correspondante sur les "
                f"{len(elements_to_check)} élément(s) examiné(s). "
                "La validation finale exige un contrôle du rendu réel dans le navigateur."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(elements_to_check),
            metadata={
                "elements_examined": len(elements_to_check),
                "potential_color_risks": len(findings),
                "inline_style_risks": len(
                    [f for f in findings if f.evidence.get("risk_type") != "stylesheet_color_without_background"]
                ),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier le contraste texte/fond dans le navigateur",
                    "vérifier l'héritage des couleurs de fond",
                ],
                "manual_check_for": "color sans background-color (critère 10.5.1)",
            },
        )


class Test1052(RGAATest):
    """Test 10.5.2 : Chaque déclaration CSS de couleur de fond est accompagnée
    d'une déclaration de couleur de police."""

    test_id = "10.5.2"
    criterion_id = "10.5"

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
                summary="Le DOM n'est pas disponible ; le test 10.5.2 nécessite l'analyse de la page.",
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

        # Sélectionner les éléments à vérifier (textuels + leurs conteneurs avec styles)
        elements_to_check = _get_elements_to_check(soup, _TEXT_TAGS)

        findings: list[Finding] = []
        for element in elements_to_check:
            findings.extend(_analyze_element_for_1052(soup, element, self.test_id))

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_for_1052(html_source, self.test_id)
        findings.extend(css_findings)

        # Déterminer le statut
        if findings:
            # Si des risques certains sont détectés (inline styles), c'est un FAIL
            inline_risks = [f for f in findings if f.evidence.get("risk_type") != "stylesheet_background_without_color"]
            if inline_risks:
                status = TestStatus.FAIL
                summary = (
                    f"{len(inline_risks)} élément(s) avec background-color sans color détecté(s) "
                    "dans les styles en ligne. "
                    f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
            else:
                # Risques seulement dans les feuilles de style = NEEDS_REVIEW
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    "Analyse statique terminée : "
                    f"{len(elements_to_check)} élément(s) examiné(s), "
                    f"{len(findings)} risque(s) potentiel(s) détecté(s) dans les feuilles de style. "
                    "Aucun risque certain dans les styles en ligne. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
        else:
            status = TestStatus.PASS
            summary = (
                f"Aucun risque détecté : toutes les déclarations background-color "
                f"ont une color correspondante sur les "
                f"{len(elements_to_check)} élément(s) examiné(s). "
                "La validation finale exige un contrôle du rendu réel dans le navigateur."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(elements_to_check),
            metadata={
                "elements_examined": len(elements_to_check),
                "potential_background_risks": len(findings),
                "inline_style_risks": len(
                    [f for f in findings if f.evidence.get("risk_type") != "stylesheet_background_without_color"]
                ),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier le contraste texte/fond dans le navigateur",
                    "vérifier l'héritage des couleurs de police",
                ],
                "manual_check_for": "background-color sans color (critère 10.5.2)",
            },
        )


class Test1053(RGAATest):
    """Test 10.5.3 : Chaque utilisation d'image pour créer une couleur de fond
    est accompagnée d'une déclaration de couleur de fond de secours."""

    test_id = "10.5.3"
    criterion_id = "10.5"

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
                summary="Le DOM n'est pas disponible ; le test 10.5.3 nécessite l'analyse de la page.",
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

        # Sélectionner les éléments à vérifier (textuels + leurs conteneurs avec styles)
        elements_to_check = _get_elements_to_check(soup, _TEXT_TAGS)

        findings: list[Finding] = []
        for element in elements_to_check:
            findings.extend(_analyze_element_for_1053(soup, element, self.test_id))

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_for_1053(html_source, self.test_id)
        findings.extend(css_findings)

        # Déterminer le statut
        if findings:
            # Si des risques certains sont détectés (inline styles), c'est un FAIL
            inline_risks = [
                f for f in findings if f.evidence.get("risk_type") != "stylesheet_background_image_without_fallback"
            ]
            if inline_risks:
                status = TestStatus.FAIL
                summary = (
                    f"{len(inline_risks)} élément(s) avec background-image sans background-color de secours détecté(s) "
                    "dans les styles en ligne. "
                    f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
            else:
                # Risques seulement dans les feuilles de style = NEEDS_REVIEW
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    "Analyse statique terminée : "
                    f"{len(elements_to_check)} élément(s) examiné(s), "
                    f"{len(findings)} risque(s) potentiel(s) détecté(s) dans les feuilles de style. "
                    "Aucun risque certain dans les styles en ligne. "
                    "La validation exige un contrôle du rendu réel dans le navigateur."
                )
        else:
            status = TestStatus.PASS
            summary = (
                f"Aucun risque détecté : toutes les déclarations background-image "
                f"ont une background-color de secours correspondante sur les "
                f"{len(elements_to_check)} élément(s) examiné(s). "
                "La validation finale exige un contrôle du rendu réel dans le navigateur."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(elements_to_check),
            metadata={
                "elements_examined": len(elements_to_check),
                "potential_bg_image_risks": len(findings),
                "inline_style_risks": len(
                    [
                        f
                        for f in findings
                        if f.evidence.get("risk_type") != "stylesheet_background_image_without_fallback"
                    ]
                ),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier la lisibilité du texte si l'image de fond échoue",
                    "vérifier l'héritage des couleurs de fond de secours",
                ],
                "manual_check_for": "background-image sans background-color fallback (critère 10.5.3)",
            },
        )

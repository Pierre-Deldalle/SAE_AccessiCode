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

# Expressions régulières pour détecter les risques CSS
_FIXED_DIMENSION_RE = re.compile(
    r"(?:^|;)\s*(width|min-width|max-width|height|min-height|max-height)\s*:\s*"
    r"(-?\d+(?:\.\d+)?)\s*(px|pt|em|rem|vh|vw|%)?",
    re.IGNORECASE,
)
_OVERFLOW_RE = re.compile(r"(?:^|;)\s*overflow(?:-[xy])?\s*:\s*(hidden|clip)\b", re.I)
_NOWRAP_RE = re.compile(r"(?:^|;)\s*white-space\s*:\s*nowrap\b", re.I)
_FIXED_FONT_SIZE_RE = re.compile(r"(?:^|;)\s*font-size\s*:\s*\d+(?:\.\d+)?\s*(px|pt)\b", re.I)
_ABSOLUTE_POSITION_RE = re.compile(r"(?:^|;)\s*position\s*:\s*(absolute|fixed)\b", re.I)


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


def _dimension_risks(style: str) -> list[tuple[str, str]]:
    """Détecte les dimensions fixes en px/pt qui risquent de couper le texte."""
    risks: list[tuple[str, str]] = []
    for prop, value, unit in _FIXED_DIMENSION_RE.findall(style):
        prop = prop.lower()
        unit = unit.lower()
        if unit in {"px", "pt"} and prop in {"width", "min-width", "max-width", "height", "min-height", "max-height"}:
            risks.append((prop, f"{value}{unit}"))
    return risks


def _analyze_element_risks(
    soup: BeautifulSoup,
    element: Tag,
    test_id: str,
) -> list[Finding]:
    """Analyse les risques de perte d'information pour un élément textuel."""
    style = _inline_style(element)
    if not style:
        return []

    # Ne pas analyser les conteneurs exempts
    if _is_exempt(element):
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # 1. Dimensions fixes en px/pt
    for prop, value in _dimension_risks(style):
        findings.append(
            Finding(
                element=selector,
                message=(
                    f"L'élément contenant du texte possède une dimension fixe "
                    f"({prop}: {value}) susceptible de couper le texte à 200 %."
                ),
                recommendation=(
                    "Vérifier le rendu à 200 %. Préférer une dimension adaptable "
                    "et permettre au conteneur de grandir avec son contenu."
                ),
                evidence={
                    "property": prop,
                    "value": value,
                    "inline_style": style[:300],
                    "test_id": test_id,
                    "risk_type": "fixed_dimension",
                },
            )
        )

    # 2. Overflow masquant
    overflow_match = _OVERFLOW_RE.search(style)
    if overflow_match:
        findings.append(
            Finding(
                element=selector,
                message=(
                    f"L'élément contenant du texte utilise "
                    f"overflow: {overflow_match.group(1)}, ce qui peut masquer "
                    "une partie du texte agrandi."
                ),
                recommendation=(
                    "Contrôler à 200 % qu'aucun texte ni aucune information ne "
                    "disparaît. Retirer le masquage ou prévoir un défilement adapté."
                ),
                evidence={
                    "overflow": overflow_match.group(1),
                    "inline_style": style[:300],
                    "test_id": test_id,
                    "risk_type": "clipped_overflow",
                },
            )
        )

    # 3. white-space: nowrap
    if _NOWRAP_RE.search(style):
        findings.append(
            Finding(
                element=selector,
                message="Le texte est forcé sur une seule ligne (white-space: nowrap).",
                recommendation=(
                    "Vérifier que le texte reste entièrement visible à 200 % et qu'il ne déborde pas de son conteneur."
                ),
                evidence={
                    "inline_style": style[:300],
                    "test_id": test_id,
                    "risk_type": "nowrap",
                },
            )
        )

    # 4. Positionnement absolute/fixed avec dimension fixe
    if _ABSOLUTE_POSITION_RE.search(style) and _FIXED_DIMENSION_RE.search(style):
        findings.append(
            Finding(
                element=selector,
                message=(
                    "Un élément de texte positionné en absolute/fixed possède "
                    "également une dimension fixe ; un chevauchement ou une coupure "
                    "est possible à 200 %."
                ),
                recommendation=(
                    "Vérifier le chevauchement et la perte de texte à 200 %. "
                    "Préférer une mise en page qui s'adapte au contenu."
                ),
                evidence={
                    "inline_style": style[:300],
                    "test_id": test_id,
                    "risk_type": "positioned_fixed_box",
                },
            )
        )

    return findings


def _analyze_stylesheet_risks(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS des feuilles de style internes pour détecter des risques."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        risks: list[tuple[str, str]] = []
        risks.extend((f"dimension fixe {prop}", value) for prop, value in _dimension_risks(declarations))
        overflow_match = _OVERFLOW_RE.search(declarations)
        if overflow_match:
            risks.append(("overflow masquant", overflow_match.group(1)))
        nowrap_match = _NOWRAP_RE.search(declarations)
        if nowrap_match:
            risks.append(("texte sans retour à la ligne", "nowrap"))

        if risks:
            risk_names = ", ".join(f"{name}: {value}" for name, value in risks)
            findings.append(
                Finding(
                    element=selector[:160],
                    message=(f"Règle CSS à examiner pour l'agrandissement à 200 % ({risk_names})."),
                    recommendation=(
                        "Vérifier dans le navigateur si cette règle s'applique "
                        "à du texte et provoque une coupure, un chevauchement "
                        "ou une perte d'information à 200 %."
                    ),
                    evidence={
                        "selector": selector[:160],
                        "declarations": declarations[:300],
                        "source_type": "stylesheet",
                        "risk_type": "stylesheet_layout_risk",
                        "test_id": test_id,
                    },
                )
            )
    return findings


def _count_exempt_elements(soup: BeautifulSoup) -> dict[str, int]:
    """Compte les éléments exempts du critère 10.4."""
    return {
        "canvas": len(soup.find_all("canvas")),
        "images_with_text_possible": len(soup.find_all("img")),
        "video_subtitles_not_verifiable_from_dom": len(soup.find_all("video")),
    }


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


class Test1041(RGAATest):
    """Test 10.4.1 : Aucune perte d'information à 200 %."""

    test_id = "10.4.1"
    criterion_id = "10.4"

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
                summary="Le DOM n'est pas disponible ; le test 10.4.1 nécessite l'analyse de la page.",
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
            findings.extend(_analyze_element_risks(soup, element, self.test_id))

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_risks(html_source, self.test_id)
        findings.extend(css_findings)

        exempt_counts = _count_exempt_elements(soup)

        # Déterminer le statut
        if findings:
            # Si des risques certains sont détectés (inline styles), c'est un FAIL
            inline_risks = [f for f in findings if f.evidence.get("risk_type") != "stylesheet_layout_risk"]
            if inline_risks:
                status = TestStatus.FAIL
                summary = (
                    f"{len(inline_risks)} risque(s) certain(s) de perte d'information "
                    "détecté(s) dans les styles en ligne. "
                    f"{len(css_findings)} risque(s) additionnel(s) dans les feuilles de style. "
                    "La validation exige un contrôle du rendu réel à 200 % dans le navigateur."
                )
            else:
                # Risques seulement dans les feuilles de style = NEEDS_REVIEW
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    "Analyse statique terminée : "
                    f"{len(elements_to_check)} élément(s) examiné(s), "
                    f"{len(findings)} risque(s) potentiel(s) détecté(s) dans les feuilles de style. "
                    "Aucun risque certain dans les styles en ligne. "
                    "La validation exige un contrôle du rendu réel à 200 % dans le navigateur."
                )
        else:
            status = TestStatus.PASS
            summary = (
                f"Aucun risque de perte d'information détecté sur les "
                f"{len(elements_to_check)} élément(s) examiné(s). "
                "La validation finale exige un contrôle du rendu réel à 200 % dans le navigateur."
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
                "potential_layout_risks": len(findings),
                "inline_style_risks": len(
                    [f for f in findings if f.evidence.get("risk_type") != "stylesheet_layout_risk"]
                ),
                "stylesheet_risks": len(css_findings),
                "exceptions_to_review": exempt_counts,
                "browser_zoom_test_performed": False,
                "required_manual_checks": [
                    "zoom texte du navigateur à 200 %",
                    "zoom graphique du navigateur à 200 %",
                    "composant de zoom propre au site, s'il existe",
                ],
                "manual_check_for": "perte d'information à 200 %",
            },
        )


class Test1042(RGAATest):
    """Test 10.4.2 : L'ensemble du texte peut être agrandi à 200 %."""

    test_id = "10.4.2"
    criterion_id = "10.4"

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
                summary="Le DOM n'est pas disponible ; le test 10.4.2 nécessite l'analyse de la page.",
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

        # Vérifier chaque élément pour la présence de tailles de police fixes
        for element in elements_to_check:
            style = _inline_style(element)
            if not style:
                continue

            selector = _selector_for(soup, element)

            # Détecter font-size en px ou pt (empêche l'agrandissement par zoom texte)
            for match in _FIXED_FONT_SIZE_RE.finditer(style):
                value = match.group(0).strip()
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément possède une taille de police fixe ({value}) "
                            "qui empêche l'agrandissement via le zoom texte du navigateur."
                        ),
                        recommendation=(
                            "Utiliser des unités relatives (em, rem, %) pour la taille de police "
                            "afin de permettre l'agrandissement par l'utilisateur."
                        ),
                        evidence={
                            "property": "font-size",
                            "value": value,
                            "inline_style": style[:300],
                            "test_id": self.test_id,
                            "risk_type": "fixed_font_size",
                        },
                    )
                )

        # Aussi vérifier tous les autres éléments avec du texte rendu qui ont font-size en ligne
        # (ex: div avec texte direct et font-size fixe)
        checked_ids = {id(e) for e in elements_to_check}
        additional_font_size_elements = 0
        for element in soup.find_all(True):
            if id(element) in checked_ids:
                continue
            if not _has_rendered_text(element):
                continue
            style = _inline_style(element)
            if not style:
                continue
            if not _FIXED_FONT_SIZE_RE.search(style):
                continue
            additional_font_size_elements += 1
            selector = _selector_for(soup, element)
            for match in _FIXED_FONT_SIZE_RE.finditer(style):
                value = match.group(0).strip()
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément possède une taille de police fixe ({value}) "
                            "qui empêche l'agrandissement via le zoom texte du navigateur."
                        ),
                        recommendation=(
                            "Utiliser des unités relatives (em, rem, %) pour la taille de police "
                            "afin de permettre l'agrandissement par l'utilisateur."
                        ),
                        evidence={
                            "property": "font-size",
                            "value": value,
                            "inline_style": style[:300],
                            "test_id": self.test_id,
                            "risk_type": "fixed_font_size",
                        },
                    )
                )

        total_elements_checked = len(elements_to_check) + additional_font_size_elements

        # Analyser aussi les règles CSS internes pour font-size fixe
        rules = _extract_stylesheet_rules(html_source)
        for selector, declarations in rules:
            for match in _FIXED_FONT_SIZE_RE.finditer(declarations):
                value = match.group(0).strip()
                findings.append(
                    Finding(
                        element=selector[:160],
                        message=(
                            f"Règle CSS avec taille de police fixe ({value}) "
                            "susceptible d'empêcher l'agrandissement du texte."
                        ),
                        recommendation=(
                            "Vérifier si cette règle s'applique à du texte et utiliser "
                            "des unités relatives (em, rem, %) à la place."
                        ),
                        evidence={
                            "selector": selector[:160],
                            "declarations": declarations[:300],
                            "source_type": "stylesheet",
                            "risk_type": "fixed_font_size_stylesheet",
                            "test_id": self.test_id,
                        },
                    )
                )

        exempt_counts = _count_exempt_elements(soup)

        # Déterminer le statut
        if findings:
            # Distinguer les risques certains (inline) des risques potentiels (stylesheet)
            inline_risks = [f for f in findings if f.evidence.get("risk_type") in {"fixed_font_size"}]
            stylesheet_risks = [f for f in findings if f.evidence.get("risk_type") == "fixed_font_size_stylesheet"]

            if inline_risks:
                status = TestStatus.FAIL
                summary = (
                    f"{len(inline_risks)} élément(s) avec taille de police fixe en ligne "
                    f"détecté(s) qui empêche(nt) l'agrandissement. "
                    f"{len(stylesheet_risks)} risque(s) additionnel(s) dans les feuilles de style. "
                    "La validation exige un contrôle du rendu réel à 200 % dans le navigateur."
                )
            else:
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    "Analyse statique terminée : "
                    f"{total_elements_checked} élément(s) examiné(s), "
                    f"{len(findings)} risque(s) potentiel(s) de taille de police fixe "
                    "détecté(s) dans les feuilles de style. "
                    "Aucune taille fixe en ligne détectée. "
                    "La validation exige un contrôle du rendu réel à 200 % dans le navigateur."
                )
        else:
            status = TestStatus.PASS
            summary = (
                f"Aucune taille de police fixe empêchant l'agrandissement détectée "
                f"sur les {total_elements_checked} élément(s) examiné(s). "
                "La validation finale exige un contrôle du rendu réel à 200 % dans le navigateur."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=total_elements_checked,
            metadata={
                "elements_examined": total_elements_checked,
                "fixed_font_size_risks": len(findings),
                "inline_font_size_risks": len(
                    [f for f in findings if f.evidence.get("risk_type") == "fixed_font_size"]
                ),
                "stylesheet_font_size_risks": len(
                    [f for f in findings if f.evidence.get("risk_type") == "fixed_font_size_stylesheet"]
                ),
                "exceptions_to_review": exempt_counts,
                "browser_zoom_test_performed": False,
                "required_manual_checks": [
                    "zoom texte du navigateur à 200 %",
                    "zoom graphique du navigateur à 200 %",
                    "composant de zoom propre au site, s'il existe",
                ],
                "manual_check_for": "agrandissement effectif de l'ensemble du texte à 200 %",
            },
        )

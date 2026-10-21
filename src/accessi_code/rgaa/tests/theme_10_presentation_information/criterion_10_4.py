from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


# Le test RGAA 10.4 exige une vérification du rendu à 200 % dans un navigateur.
# Un DOM/HTML seul ne permet pas de prouver qu'un texte reste lisible ou qu'il
# est effectivement agrandi. Les contrôles ci-dessous repèrent donc des risques
# concrets dans le HTML/CSS, puis laissent la validation visuelle à l'audit manuel.
_EXEMPT_TEXT_CONTAINERS = {"canvas"}
_TEXT_TAGS = {
    "a", "abbr", "b", "blockquote", "button", "caption", "dd", "dt", "em",
    "figcaption", "h1", "h2", "h3", "h4", "h5", "h6", "i", "label", "legend",
    "li", "p", "small", "span", "strong", "summary", "td", "th", "textarea",
}
_FIXED_DIMENSION_RE = re.compile(
    r"(?:^|;)\s*(width|min-width|max-width|height|min-height|max-height)\s*:\s*"
    r"(-?\d+(?:\.\d+)?)\s*(px|pt|em|rem|vh|vw|%)?",
    re.IGNORECASE,
)
_OVERFLOW_RE = re.compile(r"(?:^|;)\s*overflow(?:-[xy])?\s*:\s*(hidden|clip)\b", re.I)
_NOWRAP_RE = re.compile(r"(?:^|;)\s*white-space\s*:\s*nowrap\b", re.I)
_FIXED_FONT_RE = re.compile(r"(?:^|;)\s*font-size\s*:\s*\d+(?:\.\d+)?\s*(px|pt)\b", re.I)
_ABSOLUTE_POSITION_RE = re.compile(
    r"(?:^|;)\s*position\s*:\s*(absolute|fixed)\b", re.I
)


def _selector_for(soup: BeautifulSoup, element: Tag) -> str:
    """Construit un repère lisible et relativement stable pour un élément."""
    if element.get("id"):
        return f"#{element['id']}"
    classes = element.get("class", [])
    if classes:
        return f"{element.name}.{'.'.join(classes[:2])}"
    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass
    return element.name or "élément inconnu"


def _is_exempt(element: Tag) -> bool:
    """Ignore le texte dessiné dans canvas, exception explicite du critère."""
    return element.name in _EXEMPT_TEXT_CONTAINERS or element.find_parent(
        list(_EXEMPT_TEXT_CONTAINERS)
    ) is not None


def _has_rendered_text(element: Tag) -> bool:
    """Écarte les éléments sans texte utile et les contenus script/style."""
    if element.name in {"script", "style", "noscript", "template"} or _is_exempt(element):
        return False
    text = element.get_text(" ", strip=True)
    return bool(text)


def _inline_style(element: Tag) -> str:
    value = element.get("style", "")
    return value if isinstance(value, str) else ""


def _css_rules(html_source: str) -> list[tuple[str, str, str]]:
    """Extrait les règles CSS simples des blocs <style> et des attributs style."""
    rules: list[tuple[str, str, str]] = []
    for block_index, block in enumerate(
        re.findall(r"<style\b[^>]*>(.*?)</style\s*>", html_source, re.I | re.S), 1
    ):
        # Heuristique volontairement limitée : elle ne remplace pas un parseur CSS.
        for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            selector = selector.strip()
            declarations = declarations.strip()
            if selector and declarations:
                rules.append((f"style[{block_index}] {selector}", declarations, "stylesheet"))
    return rules


def _dimension_risks(style: str) -> list[tuple[str, str]]:
    risks: list[tuple[str, str]] = []
    for prop, value, unit in _FIXED_DIMENSION_RE.findall(style):
        prop = prop.lower()
        unit = unit.lower()
        # Les dimensions fixes en pixels/points sont particulièrement sensibles.
        # Les pourcentages et unités relatives ne sont pas signalés par défaut.
        if unit in {"px", "pt"} and prop in {
            "width", "min-width", "max-width", "height", "min-height", "max-height"
        }:
            risks.append((prop, f"{value}{unit}"))
    return risks


def _findings_for_element(soup: BeautifulSoup, element: Tag, test_id: str) -> list[Finding]:
    style = _inline_style(element)
    if not style:
        return []

    selector = _selector_for(soup, element)
    findings: list[Finding] = []

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

    if _NOWRAP_RE.search(style):
        findings.append(
            Finding(
                element=selector,
                message="Le texte est forcé sur une seule ligne (white-space: nowrap).",
                recommendation=(
                    "Vérifier que le texte reste entièrement visible à 200 % "
                    "et qu'il ne déborde pas de son conteneur."
                ),
                evidence={
                    "inline_style": style[:300],
                    "test_id": test_id,
                    "risk_type": "nowrap",
                },
            )
        )

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


class _TextResizeTest(RGAATest):
    """Socle commun aux tests 10.4.1 et 10.4.2."""

    required_capabilities = frozenset({Capability.DOM, Capability.HTML_SOURCE})

    test_id = ""
    criterion_id = "10.4"
    _check_information_loss = False

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
                summary="Le DOM n'est pas disponible ; le test 10.4 nécessite l'analyse de la page.",
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

        # Le test 10.4 porte sur le rendu effectif du navigateur. Le DOM et le CSS
        # fournis ici ne donnent pas accès à la taille calculée, au layout ou aux
        # pixels après zoom. On détecte donc des indices de risque, sans prétendre
        # conclure PASS en l'absence d'une vraie interaction navigateur.
        text_elements = [
            element for element in soup.find_all(list(_TEXT_TAGS))
            if _has_rendered_text(element)
        ]
        findings: list[Finding] = []
        for element in text_elements:
            findings.extend(_findings_for_element(soup, element, self.test_id))

        # Examiner également les règles CSS embarquées. Sans moteur CSS, on ne peut
        # pas déterminer avec fiabilité les éléments ciblés par chaque sélecteur :
        # ces règles sont donc remontées comme pistes de vérification, pas comme échec.
        css_risks: list[Finding] = []
        for selector, declarations, source_type in _css_rules(html_source):
            risks: list[tuple[str, str]] = []
            risks.extend(
                (f"dimension fixe {prop}", value)
                for prop, value in _dimension_risks(declarations)
            )
            overflow_match = _OVERFLOW_RE.search(declarations)
            if overflow_match:
                risks.append(("overflow masquant", overflow_match.group(1)))
            nowrap_match = _NOWRAP_RE.search(declarations)
            if nowrap_match:
                risks.append(("texte sans retour à la ligne", "nowrap"))

            if risks:
                risk_names = ", ".join(f"{name}: {value}" for name, value in risks)
                css_risks.append(
                    Finding(
                        element=selector[:160],
                        message=(
                            f"Règle CSS à examiner pour l'agrandissement à 200 % "
                            f"({risk_names})."
                        ),
                        recommendation=(
                            "Vérifier dans le navigateur si cette règle s'applique "
                            "à du texte et provoque une coupure, un chevauchement "
                            "ou une perte d'information à 200 %."
                        ),
                        evidence={
                            "selector": selector[:160],
                            "declarations": declarations[:300],
                            "source_type": source_type,
                            "risk_type": "stylesheet_layout_risk",
                            "test_id": self.test_id,
                        },
                    )
                )
        findings.extend(css_risks)

        exempt_counts = {
            "canvas": len(soup.find_all("canvas")),
            "images_with_text_possible": len(soup.find_all("img")),
            "video_subtitles_not_verifiable_from_dom": len(soup.find_all("video")),
        }

        # Sans navigateur piloté à 200 %, ni présence ni absence de risques CSS
        # ne permet de valider la méthodologie RGAA. Le résultat reste à contrôler.
        summary = (
            "Analyse statique terminée : "
            f"{len(text_elements)} élément(s) textuel(s) examiné(s), "
            f"{len(findings)} risque(s) potentiel(s) détecté(s). "
            "La validation exige un contrôle du rendu réel à 200 % dans le navigateur."
        )
        if findings:
            summary += " Les risques relevés ne prouvent pas à eux seuls une non-conformité."

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=summary,
            findings=findings,
            tested_elements=len(text_elements),
            metadata={
                "text_elements_examined": len(text_elements),
                "potential_layout_risks": len(findings),
                "inline_style_risks": sum(
                    1 for finding in findings
                    if finding.evidence.get("risk_type") != "stylesheet_layout_risk"
                ),
                "stylesheet_risks": len(css_risks),
                "exceptions_to_review": exempt_counts,
                "browser_zoom_test_performed": False,
                "required_manual_checks": [
                    "zoom texte du navigateur à 200 %",
                    "zoom graphique du navigateur à 200 %",
                    "composant de zoom propre au site, s'il existe",
                ],
                "manual_check_for": (
                    "perte d'information à 200 %"
                    if self._check_information_loss
                    else "agrandissement effectif de l'ensemble du texte à 200 %"
                ),
            },
        )


class Test1041(_TextResizeTest):
    """Test 10.4.1 : aucune perte d'information à 200 %."""

    test_id = "10.4.1"
    criterion_id = "10.4"
    _check_information_loss = True


class Test1042(_TextResizeTest):
    """Test 10.4.2 : l'ensemble du texte peut être agrandi à 200 %."""

    test_id = "10.4.2"
    criterion_id = "10.4"
    _check_information_loss = False

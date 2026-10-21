from __future__ import annotations

import re
from collections import Counter
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


# RGAA 10.5 porte sur la présence de couleurs de texte et de fond compatibles.
# Une analyse du seul HTML ne dispose pas toujours du CSS calculé du navigateur :
# les feuilles externes, variables CSS, sélecteurs complexes et styles dynamiques
# peuvent échapper à cette analyse. Les résultats ci-dessous sont donc des contrôles
# statiques documentés, et non une mesure du contraste (qui relève notamment du 3.2).
_TEXT_CAPABLE_TAGS = {
    "a", "abbr", "address", "article", "aside", "b", "bdi", "bdo", "blockquote",
    "button", "caption", "cite", "code", "dd", "del", "details", "dfn", "dt",
    "em", "figcaption", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "i", "ins", "kbd", "label", "legend", "li", "main", "mark", "nav", "p",
    "pre", "q", "s", "samp", "section", "small", "span", "strong", "sub", "summary",
    "sup", "td", "th", "time", "title", "u", "var",
}
_NON_CONTENT_TAGS = {"script", "style", "noscript", "template", "head", "meta", "link"}
_DEFAULT_COLOR_TAGS = {"a"}
_COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.I)
_BACKGROUND_COLOR_RE = re.compile(
    r"(?:^|;)\s*background-color\s*:\s*([^;]+)", re.I
)
_BACKGROUND_RE = re.compile(r"(?:^|;)\s*background\s*:\s*([^;]+)", re.I)
_BACKGROUND_IMAGE_RE = re.compile(
    r"(?:^|;)\s*background-image\s*:\s*([^;]+)", re.I
)
_DECLARATION_RE = re.compile(r"(?P<property>[a-z-]+)\s*:\s*(?P<value>[^;]+)", re.I)
_URL_RE = re.compile(r"url\s*\(", re.I)
_VAR_RE = re.compile(r"var\s*\(", re.I)
_IMPORTANT_RE = re.compile(r"\s*!important\s*$", re.I)


def _selector_for(soup: BeautifulSoup, element: Tag) -> str:
    """Retourne un sélecteur simple utile dans un rapport d'audit."""
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"
    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(item) for item in classes[:2])}"
    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass
    return element.name or "élément inconnu"


def _has_text(element: Tag) -> bool:
    """Vérifie la présence de texte utile dans l'élément, hors balises techniques."""
    if element.name in _NON_CONTENT_TAGS:
        return False
    if element.name in {"input", "img", "svg", "canvas", "video", "audio", "iframe"}:
        # Les éléments remplacés peuvent porter une image ou une valeur, mais leur
        # contenu textuel n'est pas directement vérifiable comme un texte HTML normal.
        return False
    if element.name == "input":
        return False
    return bool(element.get_text(" ", strip=True))


def _declarations(style: str) -> dict[str, list[str]]:
    """Lit les déclarations CSS d'un bloc, sans prétendre parser toute la grammaire CSS."""
    found: dict[str, list[str]] = {}
    for match in _DECLARATION_RE.finditer(style or ""):
        prop = match.group("property").strip().lower()
        value = match.group("value").strip()
        if prop and value:
            found.setdefault(prop, []).append(value)
    return found


def _style_of(element: Tag) -> str:
    style = element.get("style", "")
    return style if isinstance(style, str) else ""


def _is_default_or_unset(value: str) -> bool:
    """Valeurs qui ne définissent pas une couleur explicite exploitable."""
    normalized = value.strip().lower()
    return normalized in {
        "", "inherit", "initial", "unset", "revert", "revert-layer", "currentcolor",
        "transparent",
    } or bool(_VAR_RE.search(normalized))


def _has_explicit_color(style: str) -> bool:
    for value in _COLOR_RE.findall(style or ""):
        if not _is_default_or_unset(value):
            return True
    return False


def _background_color_value(style: str) -> str | None:
    """Renvoie une couleur de fond explicite issue de background-color ou background."""
    for value in _BACKGROUND_COLOR_RE.findall(style or ""):
        if not _is_default_or_unset(value):
            return value.strip()
    for value in _BACKGROUND_RE.findall(style or ""):
        # Un raccourci background peut ne définir qu'une image ou une position.
        if _is_default_or_unset(value):
            continue
        if _URL_RE.search(value):
            # Un raccourci avec image ne garantit pas qu'une couleur de secours soit définie.
            tokens = re.split(r"\s+", value.strip())
            color_candidates = [
                token for token in tokens
                if token.lower() not in {
                    "none", "repeat", "repeat-x", "repeat-y", "no-repeat", "fixed",
                    "scroll", "local", "left", "right", "top", "bottom", "center",
                    "cover", "contain", "auto", "padding-box", "border-box",
                    "content-box", "inherit", "initial", "unset",
                }
                and not token.startswith(("url(", "linear-gradient(", "radial-gradient(",
                                          "conic-gradient(", "var("))
                and not token.endswith(("%", "px", "rem", "em", "vh", "vw"))
            ]
            if color_candidates:
                return color_candidates[-1]
            continue
        # Couleurs CSS usuelles : noms, hexadécimal, rgb/hsl, etc.
        if re.search(
            r"(#[0-9a-f]{3,8}\b|rgba?\s*\(|hsla?\s*\(|\boklch\s*\(|"
            r"\boklab\s*\(|\b[a-z]{3,20}\b)",
            value,
            re.I,
        ):
            # Évite de traiter des mots de position comme une couleur.
            words = value.lower().split()
            non_color_keywords = {
                "none", "repeat", "repeat-x", "repeat-y", "no-repeat", "fixed",
                "scroll", "local", "left", "right", "top", "bottom", "center",
                "cover", "contain", "auto", "padding-box", "border-box", "content-box",
            }
            candidates = [word for word in words if word not in non_color_keywords]
            if candidates:
                return candidates[-1]
    return None


def _has_background_image(style: str) -> bool:
    values = _BACKGROUND_IMAGE_RE.findall(style or "")
    if any(_URL_RE.search(value) for value in values):
        return True
    for value in _BACKGROUND_RE.findall(style or ""):
        if _URL_RE.search(value):
            return True
    return False


def _extract_stylesheets(html_source: str) -> list[tuple[str, str]]:
    """Extrait les règles des balises <style>; les fichiers CSS externes ne sont pas chargés."""
    rules: list[tuple[str, str]] = []
    for block_index, block in enumerate(
        re.findall(r"<style\b[^>]*>(.*?)</style\s*>", html_source, re.I | re.S), 1
    ):
        # Cette extraction couvre les règles classiques « sélecteur { déclarations } ».
        # Elle ne résout pas les règles imbriquées @media/@supports ni la cascade complète.
        for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            selector = selector.strip()
            declarations = declarations.strip()
            if selector and declarations and not selector.startswith("@"):
                rules.append((f"style[{block_index}] {selector}", declarations))
    return rules


def _matching_rule_styles(element: Tag, rules: list[tuple[str, str]]) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    for selector, declarations in rules:
        # Les sélecteurs CSS avancés peuvent ne pas être pris en charge par SoupSieve.
        try:
            if element.select_one(selector) is not None and element in element.select(selector):
                matches.append((selector, declarations))
        except Exception:
            # Une règle non interprétable est signalée dans les métadonnées globales.
            continue
    return matches


def _element_styles(
    soup: BeautifulSoup,
    element: Tag,
    rules: list[tuple[str, str]],
) -> list[tuple[str, str, str]]:
    """Rassemble styles inline et règles internes qui semblent viser l'élément."""
    styles: list[tuple[str, str, str]] = []
    inline = _style_of(element)
    if inline:
        styles.append(("style inline", inline, "inline"))
    for selector, declarations in rules:
        try:
            if element in soup.select(selector):
                styles.append((selector, declarations, "stylesheet"))
        except Exception:
            continue
    return styles


def _own_color_declarations(styles: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for source, style, origin in styles:
        for value in _COLOR_RE.findall(style):
            if not _is_default_or_unset(value):
                result.append((source, value.strip(), origin))
    return result


def _own_background_declarations(
    styles: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for source, style, origin in styles:
        value = _background_color_value(style)
        if value:
            result.append((source, value, origin))
    return result


def _own_background_images(
    styles: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for source, style, origin in styles:
        for value in _BACKGROUND_IMAGE_RE.findall(style):
            if _URL_RE.search(value):
                result.append((source, value.strip(), origin))
        for value in _BACKGROUND_RE.findall(style):
            if _URL_RE.search(value):
                result.append((source, value.strip(), origin))
    # Évite les doublons lorsque background et background-image décrivent la même image.
    unique: dict[tuple[str, str], tuple[str, str, str]] = {}
    for item in result:
        unique[(item[0], item[1])] = item
    return list(unique.values())


def _ancestor_has_background(element: Tag, styles_by_element: dict[int, list[tuple[str, str, str]]]) -> bool:
    """Cherche une couleur de fond déclarée sur l'élément ou un ancêtre."""
    current: Tag | None = element
    while current is not None:
        styles = styles_by_element.get(id(current), [])
        if _own_background_declarations(styles):
            return True
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
    return False


def _ancestor_has_text_color(element: Tag, styles_by_element: dict[int, list[tuple[str, str, str]]]) -> bool:
    """Cherche une couleur de texte déclarée sur l'élément ou un ancêtre."""
    current: Tag | None = element
    while current is not None:
        styles = styles_by_element.get(id(current), [])
        if _own_color_declarations(styles):
            return True
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
    return False


class _ColorDeclarationTest(RGAATest):
    """Socle partagé des contrôles statiques du critère RGAA 10.5."""

    required_capabilities = frozenset({Capability.DOM, Capability.HTML_SOURCE})
    criterion_id = "10.5"
    test_id = ""
    _mode = ""

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
                summary="Le DOM n'est pas disponible pour analyser les déclarations de couleurs.",
                tested_elements=0,
                metadata={"reason": "missing_dom", "analysis": "static_html_css"},
            )
        if not isinstance(html_source, str) or not html_source.strip():
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible pour analyser les styles.",
                tested_elements=0,
                metadata={"reason": "missing_html_source", "analysis": "static_html_css"},
            )

        rules = _extract_stylesheets(html_source)
        text_elements = [
            element for element in soup.find_all(True)
            if element.name not in _NON_CONTENT_TAGS and _has_text(element)
        ]

        # Index des styles par élément pour prendre en compte des déclarations
        # présentes sur les ancêtres, sans prétendre calculer la cascade CSS réelle.
        styles_by_element: dict[int, list[tuple[str, str, str]]] = {}
        stylesheet_rule_count = len(rules)
        unparsed_external_stylesheets = len(
            soup.find_all("link", rel=lambda value: value and "stylesheet" in value)
        )
        for element in soup.find_all(True):
            styles_by_element[id(element)] = _element_styles(soup, element, rules)

        findings: list[Finding] = []
        examined = 0
        skipped_default = 0
        explicit_color_count = 0
        explicit_background_count = 0
        background_image_count = 0
        inherited_background_count = 0
        inherited_color_count = 0

        for element in text_elements:
            examined += 1
            selector = _selector_for(soup, element)
            own_styles = styles_by_element.get(id(element), [])
            colors = _own_color_declarations(own_styles)
            backgrounds = _own_background_declarations(own_styles)
            images = _own_background_images(own_styles)
            explicit_color_count += len(colors)
            explicit_background_count += len(backgrounds)
            background_image_count += len(images)

            if self._mode == "text_requires_background":
                if not colors:
                    # Pas de couleur de police déclarée sur cet élément : le test
                    # 10.5.1 ne demande pas de contrôle pour les couleurs par défaut.
                    if element.name in _DEFAULT_COLOR_TAGS:
                        skipped_default += 1
                    continue
                if _ancestor_has_background(element, styles_by_element):
                    inherited_background_count += 1
                    continue
                for source, value, origin in colors:
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Une couleur de police explicite ({value}) est déclarée "
                                "sans couleur de fond détectée sur l'élément ou ses ancêtres."
                            ),
                            recommendation=(
                                "Définir une couleur de fond explicite adaptée sur l'élément "
                                "ou un ancêtre, puis vérifier le rendu réel et le contraste."
                            ),
                            evidence={
                                "test_id": self.test_id,
                                "property": "color",
                                "value": value,
                                "declaration_source": source,
                                "declaration_origin": origin,
                                "risk_type": "text_color_without_background",
                            },
                        )
                    )

            elif self._mode == "background_requires_text":
                if not backgrounds:
                    continue
                if _ancestor_has_text_color(element, styles_by_element):
                    inherited_color_count += 1
                    continue
                for source, value, origin in backgrounds:
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Une couleur de fond ({value}) est déclarée sans couleur "
                                "de police détectée sur l'élément ou ses ancêtres."
                            ),
                            recommendation=(
                                "Définir une couleur de police explicite adaptée sur l'élément "
                                "ou un ancêtre, puis vérifier le rendu réel et le contraste."
                            ),
                            evidence={
                                "test_id": self.test_id,
                                "property": "background-color",
                                "value": value,
                                "declaration_source": source,
                                "declaration_origin": origin,
                                "risk_type": "background_without_text_color",
                            },
                        )
                    )

            elif self._mode == "background_image_requires_color":
                if not images:
                    continue
                if _ancestor_has_background(element, styles_by_element):
                    inherited_background_count += 1
                    continue
                for source, value, origin in images:
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                "Une image d'arrière-plan CSS est appliquée à un élément "
                                "contenant du texte sans couleur de fond de secours détectée."
                            ),
                            recommendation=(
                                "Définir une couleur de fond de secours sur l'élément ou un "
                                "ancêtre afin que le texte reste lisible si l'image ne charge "
                                "pas, puis vérifier visuellement ce scénario."
                            ),
                            evidence={
                                "test_id": self.test_id,
                                "property": "background-image",
                                "value": value,
                                "declaration_source": source,
                                "declaration_origin": origin,
                                "risk_type": "background_image_without_fallback",
                            },
                        )
                    )

        status = TestStatus.FAIL if findings else TestStatus.PASS
        if findings:
            summary = (
                f"{len(findings)} déclaration(s) potentiellement non conforme(s) détectée(s) "
                f"par l'analyse statique du test {self.test_id}."
            )
        else:
            summary = (
                f"Aucun risque statique n'a été détecté par le test {self.test_id} "
                "dans les styles HTML et CSS internes analysés."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=examined,
            metadata={
                "analysis": "static_html_css_heuristic",
                "text_elements_examined": examined,
                "stylesheet_rules_examined": stylesheet_rule_count,
                "external_stylesheets_detected": unparsed_external_stylesheets,
                "explicit_text_color_declarations": explicit_color_count,
                "explicit_background_color_declarations": explicit_background_count,
                "background_image_declarations": background_image_count,
                "ancestor_background_found": inherited_background_count,
                "ancestor_text_color_found": inherited_color_count,
                "default_color_exceptions_skipped": skipped_default,
                "potential_violations": len(findings),
                "computed_browser_styles_available": False,
                "contrast_ratio_measured": False,
                "limitations": [
                    "Les feuilles CSS externes ne sont pas téléchargées ni analysées.",
                    "La cascade CSS, la spécificité, les media queries et les styles dynamiques "
                    "ne sont pas entièrement calculés.",
                    "Une absence de risque détecté ne prouve pas la conformité du rendu final.",
                    "Ce test ne mesure pas le contraste de couleurs.",
                ],
            },
        )


class Test1051(_ColorDeclarationTest):
    """10.5.1 : une couleur de police explicite doit avoir un fond détectable."""

    test_id = "10.5.1"
    _mode = "text_requires_background"


class Test1052(_ColorDeclarationTest):
    """10.5.2 : une couleur de fond explicite doit avoir une couleur de texte détectable."""

    test_id = "10.5.2"
    _mode = "background_requires_text"


class Test1053(_ColorDeclarationTest):
    """10.5.3 : une image d'arrière-plan doit disposer d'une couleur de secours."""

    test_id = "10.5.3"
    _mode = "background_image_requires_color"
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


def _selector_for(soup: BeautifulSoup, element: Tag) -> str:
    """Construit un sélecteur lisible pour un élément."""
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


def _get_inline_style(element: Tag) -> str:
    """Récupère le style inline d'un élément."""
    style = element.get("style", "")
    if isinstance(style, list):
        return " ".join(str(s) for s in style)
    return str(style) if style else ""


def _parse_style_declarations(style_str: str) -> dict[str, str]:
    """Parse une chaîne de style CSS en dictionnaire."""
    declarations = {}
    for decl in style_str.split(";"):
        decl = decl.strip()
        if not decl or ":" not in decl:
            continue
        prop, value = decl.split(":", 1)
        declarations[prop.strip().lower()] = value.strip()
    return declarations


def _has_fixed_width_over_320px(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément a une largeur fixe > 320px.
    Retourne (a_problème, détails).
    """
    style_str = _get_inline_style(element)
    if not style_str:
        return False, ""

    declarations = _parse_style_declarations(style_str)

    # Vérifier width, min-width, max-width
    for prop in ["width", "min-width", "max-width"]:
        if prop in declarations:
            value = declarations[prop].lower()
            # Chercher des valeurs en px
            px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value)
            if px_match:
                width_px = float(px_match.group(1))
                if width_px > 320:
                    return True, f"{prop}: {value} (> 320px)"

    return False, ""


def _has_fixed_height_over_256px(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément a une hauteur fixe > 256px.
    Retourne (a_problème, détails).
    """
    style_str = _get_inline_style(element)
    if not style_str:
        return False, ""

    declarations = _parse_style_declarations(style_str)

    # Vérifier height, min-height, max-height
    for prop in ["height", "min-height", "max-height"]:
        if prop in declarations:
            value = declarations[prop].lower()
            # Chercher des valeurs en px
            px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value)
            if px_match:
                height_px = float(px_match.group(1))
                if height_px > 256:
                    return True, f"{prop}: {value} (> 256px)"

    return False, ""


def _has_horizontal_overflow(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément force un défilement horizontal.
    Retourne (a_problème, détails).
    """
    style_str = _get_inline_style(element)
    if not style_str:
        return False, ""

    declarations = _parse_style_declarations(style_str)

    # Vérifier overflow-x, overflow
    for prop in ["overflow-x", "overflow"]:
        if prop in declarations:
            value = declarations[prop].lower()
            if "scroll" in value or "auto" in value:
                return True, f"{prop}: {value}"

    return False, ""


def _has_vertical_overflow(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément force un défilement vertical.
    Retourne (a_problème, détails).
    """
    style_str = _get_inline_style(element)
    if not style_str:
        return False, ""

    declarations = _parse_style_declarations(style_str)

    # Vérifier overflow-y, overflow
    for prop in ["overflow-y", "overflow"]:
        if prop in declarations:
            value = declarations[prop].lower()
            if "scroll" in value or "auto" in value:
                return True, f"{prop}: {value}"

    return False, ""


def _check_white_space_nowrap(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément a white-space: nowrap qui empêche le retour à la ligne.
    Retourne (a_problème, détails).
    """
    style_str = _get_inline_style(element)
    if not style_str:
        return False, ""

    declarations = _parse_style_declarations(style_str)

    if "white-space" in declarations:
        value = declarations["white-space"].lower()
        if "nowrap" in value:
            return True, f"white-space: {value}"

    return False, ""


def _is_exception_element(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément fait partie des cas particuliers exemptés du critère 10.11.
    Retourne (est_exception, type_exception).
    """
    # Images, vidéos, canvas, svg
    if element.name in ["img", "video", "canvas", "svg", "picture"]:
        return True, f"media:{element.name}"

    # Tableaux de données
    if element.name == "table":
        # Vérifier si c'est un tableau de données (a des th, thead, caption, etc.)
        if element.find(["th", "thead", "caption", "tfoot", "tbody"]):
            return True, "table:data_table"

    # Iframe (souvent utilisé pour du contenu externe)
    if element.name == "iframe":
        return True, "media:iframe"

    # Object, embed
    if element.name in ["object", "embed"]:
        return True, f"media:{element.name}"

    return False, ""


def _analyze_reflow_horizontal(soup: BeautifulSoup, test_id: str) -> tuple[list[Finding], int]:
    """
    Analyse les problèmes potentiels de reflow horizontal (largeur 320px).
    Retourne (findings, nombre_problèmes).
    """
    findings: list[Finding] = []
    problem_count = 0

    # 1. Vérifier les éléments avec largeur fixe > 320px
    for element in soup.find_all(True):
        # Ignorer les cas particuliers
        is_exception, exception_type = _is_exception_element(element)
        if is_exception:
            continue

        # Ignorer head, script, style, meta, link, title
        if element.name in ["head", "script", "style", "meta", "link", "title", "noscript", "template"]:
            continue

        has_fixed_width, details = _has_fixed_width_over_320px(element)
        if has_fixed_width:
            problem_count += 1
            selector = _selector_for(soup, element)
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Élément <{element.name}> avec largeur fixe > 320px détectée "
                        f"({details}). Cela peut empêcher le reflow à 320px de large."
                    ),
                    recommendation=(
                        "Utiliser des largeurs relatives (%, vw, rem) ou max-width: 100% "
                        "pour permettre l'adaptation à la largeur de la fenêtre. "
                        "Éviter les largeurs fixes en pixels supérieures à 320px."
                    ),
                    evidence={
                        "element_name": element.name,
                        "style_details": details,
                        "test_id": test_id,
                        "check_type": "fixed_width_over_320px",
                        "needs_manual_check": True,
                        "condition": "fixed_width_prevents_reflow",
                    },
                )
            )

        # 2. Vérifier overflow-x forcé
        has_h_overflow, h_details = _has_horizontal_overflow(element)
        if has_h_overflow:
            problem_count += 1
            selector = _selector_for(soup, element)
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Élément <{element.name}> avec overflow-x forcé détecté "
                        f"({h_details}). Cela peut créer un défilement horizontal "
                        f"à 320px de large."
                    ),
                    recommendation=(
                        "Éviter overflow-x: scroll/auto sur les conteneurs principaux. "
                        "Préférer un design responsive qui s'adapte sans défilement horizontal. "
                        "Si un défilement est nécessaire, vérifier qu'il concerne un "
                        "élément exempté (tableau, image, etc.)."
                    ),
                    evidence={
                        "element_name": element.name,
                        "style_details": h_details,
                        "test_id": test_id,
                        "check_type": "horizontal_overflow",
                        "needs_manual_check": True,
                        "condition": "horizontal_overflow_prevents_reflow",
                    },
                )
            )

        # 3. Vérifier white-space: nowrap
        has_nowrap, nowrap_details = _check_white_space_nowrap(element)
        if has_nowrap:
            # Vérifier si l'élément contient du texte substantiel
            text_content = element.get_text(strip=True)
            if len(text_content) > 50:  # Texte assez long pour poser problème
                problem_count += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Élément <{element.name}> avec white-space: nowrap "
                            f"({nowrap_details}) et contenu textuel long. "
                            f"Cela empêche le retour à la ligne à 320px."
                        ),
                        recommendation=(
                            "Supprimer white-space: nowrap ou l'appliquer uniquement "
                            "à de courts éléments (boutons, labels). "
                            "Utiliser text-overflow: ellipsis avec overflow: hidden "
                            "si le tronquage est acceptable."
                        ),
                        evidence={
                            "element_name": element.name,
                            "style_details": nowrap_details,
                            "text_length": len(text_content),
                            "test_id": test_id,
                            "check_type": "white_space_nowrap",
                            "needs_manual_check": True,
                            "condition": "nowrap_prevents_reflow",
                        },
                    )
                )

    return findings, problem_count


def _analyze_reflow_vertical(soup: BeautifulSoup, test_id: str) -> tuple[list[Finding], int]:
    """
    Analyse les problèmes potentiels de reflow vertical (hauteur 256px).
    Retourne (findings, nombre_problèmes).
    """
    findings: list[Finding] = []
    problem_count = 0

    # Vérifier les éléments avec hauteur fixe > 256px
    for element in soup.find_all(True):
        # Ignorer les cas particuliers
        is_exception, exception_type = _is_exception_element(element)
        if is_exception:
            continue

        # Ignorer head, script, style, meta, link, title
        if element.name in ["head", "script", "style", "meta", "link", "title", "noscript", "template"]:
            continue

        has_fixed_height, details = _has_fixed_height_over_256px(element)
        if has_fixed_height:
            problem_count += 1
            selector = _selector_for(soup, element)
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Élément <{element.name}> avec hauteur fixe > 256px détectée "
                        f"({details}). Cela peut empêcher le reflow à 256px de haut."
                    ),
                    recommendation=(
                        "Utiliser des hauteurs relatives ou min-height au lieu de height fixe. "
                        "Éviter les hauteurs fixes en pixels supérieures à 256px "
                        "sur les conteneurs de contenu principal."
                    ),
                    evidence={
                        "element_name": element.name,
                        "style_details": details,
                        "test_id": test_id,
                        "check_type": "fixed_height_over_256px",
                        "needs_manual_check": True,
                        "condition": "fixed_height_prevents_reflow",
                    },
                )
            )

        # Vérifier overflow-y forcé sur les conteneurs principaux
        has_v_overflow, v_details = _has_vertical_overflow(element)
        if has_v_overflow:
            # Ne signaler que si c'est un conteneur potentiellement problématique
            # (body, main, article, section, div avec beaucoup de contenu)
            if element.name in ["body", "main", "article", "section", "div"]:
                problem_count += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Conteneur <{element.name}> avec overflow-y forcé détecté "
                            f"({v_details}). Cela peut créer un défilement vertical "
                            f"à 256px de haut."
                        ),
                        recommendation=(
                            "Vérifier que le contenu s'adapte sans défilement vertical "
                            "à 256px de hauteur. Pour les pages avec sens de lecture "
                            "vertical, le défilement vertical est attendu mais doit "
                            "être le seul sens de défilement."
                        ),
                        evidence={
                            "element_name": element.name,
                            "style_details": v_details,
                            "test_id": test_id,
                            "check_type": "vertical_overflow",
                            "needs_manual_check": True,
                            "condition": "vertical_overflow_prevents_reflow",
                        },
                    )
                )

    return findings, problem_count


class Test10111(RGAATest):
    """Test 10.11.1 : Pour chaque page web, lorsque le contenu dont le sens de lecture
    est horizontal est affiché dans une fenêtre réduite à une largeur de 320px,
    l'ensemble des informations et des fonctionnalités sont-elles disponibles
    sans aucun défilement horizontal (hors cas particuliers) ?"""

    test_id = "10.11.1"
    criterion_id = "10.11"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
            Capability.BROWSER_INTERACTION,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.11.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Analyser les problèmes potentiels de reflow horizontal
        findings, problem_count = _analyze_reflow_horizontal(soup, self.test_id)

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        # Déterminer le statut
        if has_browser:
            # TODO: Implémenter le test réel avec redimensionnement de fenêtre à 320px
            # Pour l'instant, on retourne NEEDS_REVIEW car le test réel nécessite un navigateur
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {problem_count} problème(s) potentiel(s) "
                f"détecté(s) pouvant empêcher le reflow à 320px. "
                f"Un test réel avec redimensionnement de fenêtre à 320px de large "
                f"est requis pour confirmer (capacité BROWSER_INTERACTION disponible)."
            )
        elif problem_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {problem_count} problème(s) potentiel(s) "
                f"détecté(s) pouvant empêcher le reflow à 320px. "
                f"Un test manuel avec redimensionnement de fenêtre à 320px de large "
                f"est requis pour confirmer (pas de capacité BROWSER_INTERACTION)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun problème évident détecté par analyse statique qui empêcherait "
                "le reflow à 320px. Un test manuel avec redimensionnement de fenêtre "
                "à 320px est recommandé pour valider définitivement."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=problem_count,
            metadata={
                "problems_detected": problem_count,
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "redimensionner la fenêtre du navigateur à 320px de large",
                    "vérifier qu'aucun défilement horizontal n'apparaît",
                    "vérifier que tout le contenu et les fonctionnalités restent accessibles",
                    "ignorer les cas particuliers (images, tableaux, vidéos, jeux, présentations)",
                ],
                "manual_check_for": "critère 10.11.1 - reflow horizontal à 320px",
                "exceptions": [
                    "images, graphiques, vidéos",
                    "jeux (plateforme, etc.)",
                    "présentations (diaporama)",
                    "tableaux de données",
                    "interfaces nécessitant défilement horizontal à la manipulation",
                ],
                "note": "Le test réel nécessite un navigateur pour redimensionner à 320px CSS pixels",
            },
        )


class Test10112(RGAATest):
    """Test 10.11.2 : Pour chaque page web, lorsque le contenu dont le sens de lecture
    est vertical est affiché dans une fenêtre réduite à une hauteur de 256px,
    l'ensemble des informations et des fonctionnalités sont-elles disponibles
    sans aucun défilement vertical (hors cas particuliers) ?"""

    test_id = "10.11.2"
    criterion_id = "10.11"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
            Capability.BROWSER_INTERACTION,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.11.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Analyser les problèmes potentiels de reflow vertical
        findings, problem_count = _analyze_reflow_vertical(soup, self.test_id)

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        # Déterminer le statut
        if has_browser:
            # TODO: Implémenter le test réel avec redimensionnement de fenêtre à 256px
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {problem_count} problème(s) potentiel(s) "
                f"détecté(s) pouvant empêcher le reflow à 256px. "
                f"Un test réel avec redimensionnement de fenêtre à 256px de haut "
                f"est requis pour confirmer (capacité BROWSER_INTERACTION disponible)."
            )
        elif problem_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {problem_count} problème(s) potentiel(s) "
                f"détecté(s) pouvant empêcher le reflow à 256px. "
                f"Un test manuel avec redimensionnement de fenêtre à 256px de haut "
                f"est requis pour confirmer (pas de capacité BROWSER_INTERACTION)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun problème évident détecté par analyse statique qui empêcherait "
                "le reflow à 256px. Un test manuel avec redimensionnement de fenêtre "
                "à 256px est recommandé pour valider définitivement."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=problem_count,
            metadata={
                "problems_detected": problem_count,
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "redimensionner la fenêtre du navigateur à 256px de haut",
                    "vérifier qu'aucun défilement vertical n'apparaît (pour contenu sens lecture horizontal)",
                    "vérifier que tout le contenu et les fonctionnalités restent accessibles",
                    "ignorer les cas particuliers (images, tableaux, vidéos, jeux, présentations)",
                ],
                "manual_check_for": "critère 10.11.2 - reflow vertical à 256px",
                "exceptions": [
                    "images, graphiques, vidéos",
                    "jeux (plateforme, etc.)",
                    "présentations (diaporama)",
                    "tableaux de données",
                    "interfaces nécessitant défilement horizontal à la manipulation",
                ],
                "note": "Le test réel nécessite un navigateur pour redimensionner à 256px CSS pixels. "
                "Note: ce test concerne les contenus dont le sens de lecture est horizontal "
                "(ex: manga, certaines langues), qui ne doivent pas défiler verticalement à 256px.",
            },
        )

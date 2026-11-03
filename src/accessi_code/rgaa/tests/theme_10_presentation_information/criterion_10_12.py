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


def _has_important_declaration(declarations: dict[str, str], property_name: str) -> bool:
    """Vérifie si une propriété a une déclaration !important."""
    value = declarations.get(property_name, "")
    return "!important" in value.lower()


def _has_fixed_value_preventing_override(declarations: dict[str, str], property_name: str) -> tuple[bool, str]:
    """
    Vérifie si une propriété a une valeur fixe qui empêche l'override utilisateur.
    Retourne (empêche_override, détails).
    """
    value = declarations.get(property_name, "")
    if not value:
        return False, ""

    value_lower = value.lower()

    # !important empêche l'override utilisateur
    if "!important" in value_lower:
        return True, f"{property_name}: {value} (!important)"

    # Pour line-height : valeurs fixes en px, em, rem sans unité relative
    # Note: 1.5 (sans unité) ou 150% sont acceptables car redéfinissables
    if property_name == "line-height":
        # Valeur numérique sans unité = ratio, c'est OK (peut être overridé)
        # Valeur avec unité (px, em, rem, %) = potentiellement problématique si fixe
        # Mais l'utilisateur peut toujours overridé avec !important
        # On signale les valeurs fixes en px comme plus problématiques
        px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value_lower)
        if px_match:
            return True, f"line-height: {value} (valeur fixe en px)"

    # Pour margin-bottom sur <p> : valeurs fixes en px
    if property_name == "margin-bottom":
        px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value_lower)
        if px_match:
            return True, f"margin-bottom: {value} (valeur fixe en px)"

    # Pour letter-spacing : valeurs fixes en px
    if property_name == "letter-spacing":
        px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value_lower)
        if px_match:
            return True, f"letter-spacing: {value} (valeur fixe en px)"
        # normal est OK (peut être overridé)
        if "normal" in value_lower:
            return False, ""

    # Pour word-spacing : valeurs fixes en px
    if property_name == "word-spacing":
        px_match = re.search(r"(\d+(?:\.\d+)?)\s*px", value_lower)
        if px_match:
            return True, f"word-spacing: {value} (valeur fixe en px)"
        if "normal" in value_lower:
            return False, ""

    return False, ""


def _is_exception_element(element: Tag) -> tuple[bool, str]:
    """
    Vérifie si un élément fait partie des cas particuliers exemptés du critère 10.12.
    Retourne (est_exception, type_exception).
    Cas particuliers selon RGAA 10.12 :
    - Sous-titres directement intégrés à une vidéo (<track> ou contenu vidéo)
    - Images texte (images contenant du texte)
    - Textes au sein d'une balise <canvas>
    """
    # Canvas
    if element.name == "canvas":
        return True, "canvas"

    # Video - les sous-titres intégrés sont dans <track> ou brûlés dans la vidéo
    # On ne peut pas détecter les sous-titres brûlés statiquement
    # On exempte les éléments video
    if element.name == "video":
        return True, "video"

    # Images texte - difficile à détecter statiquement
    # On exempte les images (l'utilisateur ne peut pas changer l'espacement dans une image)
    if element.name == "img":
        # Si l'image a un alt, ce n'est pas forcément une image-texte
        # Mais par sécurité, on exempte les images
        return True, "img"

    # SVG contenant du texte - exempté comme image
    if element.name == "svg":
        return True, "svg"

    # Picture
    if element.name == "picture":
        return True, "picture"

    return False, ""


def _analyze_text_spacing_conflicts(soup: BeautifulSoup, test_id: str) -> tuple[list[Finding], dict[str, int]]:
    """
    Analyse les conflits potentiels avec la redéfinition de l'espacement du texte par l'utilisateur.
    Retourne (findings, compteurs_par_type).
    """
    findings: list[Finding] = []
    counters = {
        "line_height_conflict": 0,
        "margin_bottom_conflict": 0,
        "letter_spacing_conflict": 0,
        "word_spacing_conflict": 0,
        "total_elements_checked": 0,
    }

    for element in soup.find_all(True):
        # Ignorer les cas particuliers
        is_exception, exception_type = _is_exception_element(element)
        if is_exception:
            continue

        # Ignorer head, script, style, meta, link, title, noscript, template
        if element.name in ["head", "script", "style", "meta", "link", "title", "noscript", "template"]:
            continue

        counters["total_elements_checked"] += 1

        # Récupérer le style inline
        style_str = _get_inline_style(element)
        if not style_str:
            continue

        declarations = _parse_style_declarations(style_str)

        # Vérifier line-height sur tous les éléments
        if "line-height" in declarations:
            has_conflict, details = _has_fixed_value_preventing_override(declarations, "line-height")
            if has_conflict:
                counters["line_height_conflict"] += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément <{element.name}> définit une hauteur de ligne (line-height) fixe "
                            f"({details}). Cela peut empêcher l'utilisateur de redéfinir "
                            f"cette propriété selon ses besoins (critère 10.12)."
                        ),
                        recommendation=(
                            "Éviter les valeurs fixes en pixels pour line-height. "
                            "Utiliser des valeurs relatives (em, rem, %, sans unité) "
                            "ou ne pas définir la propriété pour laisser le contrôle à l'utilisateur. "
                            "Si une valeur par défaut est nécessaire, utiliser des unités relatives."
                        ),
                        evidence={
                            "element_name": element.name,
                            "property": "line-height",
                            "style_details": details,
                            "test_id": test_id,
                            "check_type": "line_height_conflict",
                            "needs_manual_check": True,
                            "condition": "line_height_prevents_user_override",
                            "wcag_criterion": "1.4.12",
                            "rgaa_criterion": "10.12",
                        },
                    )
                )

        # Vérifier margin-bottom UNIQUEMENT sur les éléments <p>
        if element.name == "p" and "margin-bottom" in declarations:
            has_conflict, details = _has_fixed_value_preventing_override(declarations, "margin-bottom")
            if has_conflict:
                counters["margin_bottom_conflict"] += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément <p> définit une marge après paragraphe (margin-bottom) fixe "
                            f"({details}). Cela peut empêcher l'utilisateur de redéfinir "
                            f"cette propriété selon ses besoins (critère 10.12)."
                        ),
                        recommendation=(
                            "Éviter les valeurs fixes en pixels pour margin-bottom sur les paragraphes. "
                            "Utiliser des valeurs relatives (em, rem, %) "
                            "ou ne pas définir la propriété pour laisser le contrôle à l'utilisateur."
                        ),
                        evidence={
                            "element_name": "p",
                            "property": "margin-bottom",
                            "style_details": details,
                            "test_id": test_id,
                            "check_type": "margin_bottom_conflict",
                            "needs_manual_check": True,
                            "condition": "margin_bottom_prevents_user_override",
                            "wcag_criterion": "1.4.12",
                            "rgaa_criterion": "10.12",
                        },
                    )
                )

        # Vérifier letter-spacing sur tous les éléments
        if "letter-spacing" in declarations:
            has_conflict, details = _has_fixed_value_preventing_override(declarations, "letter-spacing")
            if has_conflict:
                counters["letter_spacing_conflict"] += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément <{element.name}> définit un espacement des lettres (letter-spacing) fixe "
                            f"({details}). Cela peut empêcher l'utilisateur de redéfinir "
                            f"cette propriété selon ses besoins (critère 10.12)."
                        ),
                        recommendation=(
                            "Éviter les valeurs fixes en pixels pour letter-spacing. "
                            "Utiliser des valeurs relatives (em, rem) ou 'normal' "
                            "ou ne pas définir la propriété pour laisser le contrôle à l'utilisateur."
                        ),
                        evidence={
                            "element_name": element.name,
                            "property": "letter-spacing",
                            "style_details": details,
                            "test_id": test_id,
                            "check_type": "letter_spacing_conflict",
                            "needs_manual_check": True,
                            "condition": "letter_spacing_prevents_user_override",
                            "wcag_criterion": "1.4.12",
                            "rgaa_criterion": "10.12",
                        },
                    )
                )

        # Vérifier word-spacing sur tous les éléments
        if "word-spacing" in declarations:
            has_conflict, details = _has_fixed_value_preventing_override(declarations, "word-spacing")
            if has_conflict:
                counters["word_spacing_conflict"] += 1
                selector = _selector_for(soup, element)
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"L'élément <{element.name}> définit un espacement des mots (word-spacing) fixe "
                            f"({details}). Cela peut empêcher l'utilisateur de redéfinir "
                            f"cette propriété selon ses besoins (critère 10.12)."
                        ),
                        recommendation=(
                            "Éviter les valeurs fixes en pixels pour word-spacing. "
                            "Utiliser des valeurs relatives (em, rem) ou 'normal' "
                            "ou ne pas définir la propriété pour laisser le contrôle à l'utilisateur."
                        ),
                        evidence={
                            "element_name": element.name,
                            "property": "word-spacing",
                            "style_details": details,
                            "test_id": test_id,
                            "check_type": "word_spacing_conflict",
                            "needs_manual_check": True,
                            "condition": "word_spacing_prevents_user_override",
                            "wcag_criterion": "1.4.12",
                            "rgaa_criterion": "10.12",
                        },
                    )
                )

    return findings, counters


class Test10121(RGAATest):
    """Test 10.12.1 : Dans chaque page web, le texte reste-t-il lisible lorsque l'affichage
    est modifié selon ces conditions (hors cas particuliers) ?
    - L'espacement entre les lignes (line-height) est augmenté jusqu'à 1,5 fois la taille de la police
    - L'espacement suivant les paragraphes (balise <p>) est augmenté jusqu'à 2 fois la taille de la police
    - L'espacement des lettres (letter-spacing) est augmenté jusqu'à 0,12 fois la taille de la police
    - L'espacement des mots (word-spacing) est augmenté jusqu'à 0,16 fois la taille de la police
    """

    test_id = "10.12.1"
    criterion_id = "10.12"

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
                summary="Le DOM n'est pas disponible ; le test 10.12.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Analyser les conflits potentiels avec l'espacement du texte
        findings, counters = _analyze_text_spacing_conflicts(soup, self.test_id)

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        total_conflicts = sum(
            counters[k]
            for k in [
                "line_height_conflict",
                "margin_bottom_conflict",
                "letter_spacing_conflict",
                "word_spacing_conflict",
            ]
        )

        # Déterminer le statut
        if has_browser:
            # TODO: Implémenter le test réel avec application des styles utilisateur
            # Pour l'instant, on retourne NEEDS_REVIEW car le test réel nécessite un navigateur
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {total_conflicts} conflit(s) potentiel(s) "
                f"détecté(s) pouvant empêcher la redéfinition de l'espacement du texte par l'utilisateur. "
                f"Un test réel avec application des styles utilisateur (line-height: 1.5, "
                f"margin-bottom: 2em sur <p>, letter-spacing: 0.12em, word-spacing: 0.16em) "
                f"est requis pour confirmer (capacité BROWSER_INTERACTION disponible)."
            )
        elif total_conflicts > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {total_conflicts} conflit(s) potentiel(s) "
                f"détecté(s) pouvant empêcher la redéfinition de l'espacement du texte par l'utilisateur. "
                f"Un test manuel avec application des styles utilisateur est requis pour confirmer "
                f"(pas de capacité BROWSER_INTERACTION)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun conflit évident détecté par analyse statique qui empêcherait "
                "la redéfinition de l'espacement du texte par l'utilisateur. "
                "Un test manuel avec application des styles utilisateur "
                "(line-height: 1.5, margin-bottom: 2em, letter-spacing: 0.12em, word-spacing: 0.16em) "
                "est recommandé pour valider définitivement."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=total_conflicts,
            metadata={
                "conflicts_detected": total_conflicts,
                "line_height_conflicts": counters["line_height_conflict"],
                "margin_bottom_conflicts": counters["margin_bottom_conflict"],
                "letter_spacing_conflicts": counters["letter_spacing_conflict"],
                "word_spacing_conflicts": counters["word_spacing_conflict"],
                "total_elements_checked": counters["total_elements_checked"],
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "appliquer line-height: 1.5 sur tous les éléments",
                    "appliquer margin-bottom: 2em sur tous les éléments <p>",
                    "appliquer letter-spacing: 0.12em sur tous les éléments",
                    "appliquer word-spacing: 0.16em sur tous les éléments",
                    "vérifier que le texte reste lisible",
                    "vérifier qu'il n'y a pas de perte de contenu ni de fonctionnalité",
                    "ignorer les cas particuliers (sous-titres vidéo intégrés, images texte, canvas)",
                ],
                "manual_check_for": "critère 10.12.1 - espacement du texte redéfinissable par l'utilisateur",
                "exceptions": [
                    "sous-titres directement intégrés à une vidéo",
                    "images texte",
                    "texte au sein d'une balise <canvas>",
                ],
                "applied_styles": {
                    "line-height": "1.5",
                    "margin-bottom (p)": "2em",
                    "letter-spacing": "0.12em",
                    "word-spacing": "0.16em",
                },
                "reference": "WCAG 1.4.12 (AA) / EN 301 549 9.1.4.12",
            },
        )

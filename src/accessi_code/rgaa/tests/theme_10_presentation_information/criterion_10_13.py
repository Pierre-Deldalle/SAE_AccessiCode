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


def _is_user_agent_controlled(element: Tag) -> bool:
    """
    Vérifie si le contenu additionnel est contrôlé par l'agent utilisateur.
    Cas particuliers exemptés :
    - Infobulles natives (attribut title)
    - Validation native de formulaire
    """
    # title attribute = tooltip natif
    if element.has_attr("title"):
        return True

    # Validation native (input avec required, pattern, etc.)
    if element.name in ["input", "textarea", "select"]:
        if element.has_attr("required") or element.has_attr("pattern"):
            return True

    return False


def _is_activation_triggered(element: Tag) -> bool:
    """
    Vérifie si le contenu devient visible par activation utilisateur.
    Cas particuliers exemptés :
    - Fenêtres de dialogue (role=dialog, alertdialog)
    - Menus déclenchés par clic (aria-haspopup, aria-expanded)
    """
    # Role dialog ou alertdialog
    role = element.get("role", "").lower()
    if role in ["dialog", "alertdialog"]:
        return True

    # Éléments avec aria-haspopup (menus, listbox, tree, grid, dialog)
    if element.has_attr("aria-haspopup"):
        return True

    # Détails/Summary (disclosure widget natif)
    if element.name == "details":
        return True

    return False


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


def _matches_selector(element: Tag, selector: str) -> bool:
    """Vérifie si un élément correspond à un sélecteur CSS simple."""
    selector = selector.lower()
    tag = element.name.lower() if element.name else ""

    # ID
    element_id = element.get("id")
    if element_id and f"#{element_id.lower()}" in selector:
        return True

    # Classe
    classes = element.get("class", [])
    if isinstance(classes, list):
        for cls in classes:
            if f".{cls.lower()}" in selector:
                return True

    # Tag
    if tag and tag in selector:
        # Vérifier que c'est bien le tag (pas dans une classe/id)
        # Approximation simple
        return True

    return False


def _has_hover_focus_visibility_change(
    element: Tag,
    rules: list[tuple[str, str]],
    html_source: str,
) -> tuple[bool, list[str]]:
    """
    Détecte si un élément a des règles CSS qui changent sa visibilité
    au survol (:hover) ou focus (:focus, :focus-visible, :focus-within).
    Retourne (a_changement, détails).
    """
    details = []

    # Les styles inline ne peuvent pas contenir :hover/:focus directement

    # Vérifier les règles CSS
    pseudo_classes = (":hover", ":focus", ":focus-visible", ":focus-within")
    for selector, declarations in rules:
        # Chercher les pseudo-classes hover/focus dans le sélecteur
        if any(pc in selector for pc in pseudo_classes):
            # Vérifier si ce sélecteur pourrait s'appliquer à notre élément
            # ou à un parent/frère qui affecterait cet élément
            if _matches_selector(element, selector):
                # Analyser les déclarations pour des changements de visibilité
                decl_lower = declarations.lower().replace(" ", "")  # Normalize spaces
                visibility_changes = []

                if "display:" in decl_lower and any(v in decl_lower for v in ("block", "flex", "grid", "inline")):
                    visibility_changes.append("display")
                if "visibility:" in decl_lower and "visible" in decl_lower:
                    visibility_changes.append("visibility")
                if "opacity:" in decl_lower and ("1" in decl_lower or "0." in decl_lower):
                    visibility_changes.append("opacity")
                if "transform:" in decl_lower and ("translate" in decl_lower or "scale" in decl_lower):
                    visibility_changes.append("transform")
                if "z-index:" in decl_lower:
                    visibility_changes.append("z-index")
                if "pointer-events:" in decl_lower and "auto" in decl_lower:
                    visibility_changes.append("pointer-events")

                if visibility_changes:
                    details.append(f"CSS rule '{selector}': {', '.join(visibility_changes)}")

    # Vérifier aussi les attributs ARIA qui indiquent un contenu conditionnel
    if element.has_attr("aria-expanded"):
        details.append(f"aria-expanded={element.get('aria-expanded')}")

    if element.has_attr("aria-controls"):
        details.append(f"aria-controls={element.get('aria-controls')}")

    return len(details) > 0, details


def _find_trigger_elements(soup: BeautifulSoup, html_source: str) -> list[dict]:
    """
    Trouve les éléments qui peuvent déclencher l'affichage de contenu additionnel
    au survol ou focus.
    """
    triggers = []
    rules = _extract_stylesheet_rules(html_source)

    for element in soup.find_all(True):
        # Ignorer les éléments non interactifs
        if element.name in ["head", "script", "style", "meta", "link", "title", "noscript", "template", "html", "body"]:
            continue

        # Ignorer les cas particuliers
        if _is_user_agent_controlled(element):
            continue
        if _is_activation_triggered(element):
            continue

        # Vérifier si cet élément a des styles hover/focus qui révèlent du contenu
        has_change, details = _has_hover_focus_visibility_change(element, rules, html_source)
        if has_change:
            triggers.append(
                {
                    "element": element,
                    "selector": _selector_for(soup, element),
                    "details": details,
                    "tag": element.name,
                }
            )

    return triggers


def _find_hover_focus_content_elements(soup: BeautifulSoup, html_source: str) -> list[dict]:
    """
    Trouve les éléments qui sont des contenus additionnels affichés
    au survol ou focus d'un composant d'interface.
    """
    content_elements = []
    rules = _extract_stylesheet_rules(html_source)

    for element in soup.find_all(True):
        # Ignorer les éléments structurels
        if element.name in ["head", "script", "style", "meta", "link", "title", "noscript", "template", "html", "body"]:
            continue

        # Ignorer les cas particuliers
        if _is_user_agent_controlled(element):
            continue
        if _is_activation_triggered(element):
            continue

        # Vérifier si l'élément est masqué par défaut et affiché au hover/focus
        # Indices : display:none, visibility:hidden, opacity:0, position off-screen, etc.
        inline_style = _get_inline_style(element).lower()
        hidden_by_default = False
        hidden_reasons = []

        if "display:none" in inline_style.replace(" ", ""):
            hidden_by_default = True
            hidden_reasons.append("display: none (inline)")
        if "visibility:hidden" in inline_style.replace(" ", ""):
            hidden_by_default = True
            hidden_reasons.append("visibility: hidden (inline)")
        if "opacity:0" in inline_style.replace(" ", ""):
            hidden_by_default = True
            hidden_reasons.append("opacity: 0 (inline)")

        # Vérifier les règles CSS
        for selector, declarations in rules:
            if _matches_selector(element, selector):
                decl_lower = declarations.lower().replace(" ", "")
                if "display:none" in decl_lower:
                    hidden_by_default = True
                    hidden_reasons.append(f"display: none (CSS: {selector})")
                if "visibility:hidden" in decl_lower:
                    hidden_by_default = True
                    hidden_reasons.append(f"visibility: hidden (CSS: {selector})")
                if "opacity:0" in decl_lower:
                    hidden_by_default = True
                    hidden_reasons.append(f"opacity: 0 (CSS: {selector})")

        # Vérifier si cet élément est affiché au hover/focus d'un autre élément
        # (sélecteurs comme .trigger:hover .content, .trigger:focus + .content, etc.)
        shown_on_hover_focus = False
        show_details = []

        pseudo_classes = (":hover", ":focus", ":focus-visible", ":focus-within")
        for selector, declarations in rules:
            if any(pc in selector for pc in pseudo_classes):
                # Vérifier si le sélecteur cible cet élément
                # Pattern: .trigger:hover .content, .trigger:focus > .content, etc.
                if _matches_selector(element, selector):
                    decl_lower = declarations.lower().replace(" ", "")  # Normalize spaces
                    visible_props = []
                    if "display:" in decl_lower and any(v in decl_lower for v in ("block", "flex", "grid", "inline")):
                        visible_props.append("display")
                    if "visibility:" in decl_lower and "visible" in decl_lower:
                        visible_props.append("visibility")
                    if "opacity:" in decl_lower and "1" in decl_lower:
                        visible_props.append("opacity")
                    if visible_props:
                        shown_on_hover_focus = True
                        show_details.append(f"CSS rule '{selector}': {', '.join(visible_props)}")

        # Attributs ARIA indiquant un contenu conditionnel
        conditional_roles = {"tooltip", "menu", "listbox", "tree", "grid", "dialog"}
        role = element.get("role", "").lower()
        if element.has_attr("role") and role in conditional_roles:
            if hidden_by_default:
                shown_on_hover_focus = True
                show_details.append(f"role={role} with hidden default")

        if hidden_by_default and shown_on_hover_focus:
            content_elements.append(
                {
                    "element": element,
                    "selector": _selector_for(soup, element),
                    "hidden_reasons": hidden_reasons,
                    "show_details": show_details,
                    "tag": element.name,
                }
            )

    return content_elements


def _has_dismiss_mechanism(element: Tag, html_source: str) -> tuple[bool, list[str]]:
    """
    Vérifie s'il existe un mécanisme pour masquer le contenu additionnel
    sans déplacer le focus ou le pointeur (ex: touche Echap).
    """
    details = []

    # Vérifier les scripts pour la gestion de la touche Echap
    escape_patterns = [
        r"keydown.*[Ee]scape",
        r"key.*[Ee]scape",
        r"keyCode\s*===\s*27",
        r"keyCode\s*==\s*27",
        r"which\s*===\s*27",
        r"which\s*==\s*27",
        r"code\s*===\s*['\"]Escape['\"]",
        r"code\s*==\s*['\"]Escape['\"]",
    ]

    for pattern in escape_patterns:
        if re.search(pattern, html_source, re.IGNORECASE):
            details.append("Script détecté gérant la touche Echap")
            return True, details

    # Vérifier si l'élément a un attribut indiquant qu'il est fermable
    if element.has_attr("data-dismiss") or element.has_attr("data-close"):
        details.append("Attribut de fermeture détecté")
        return True, details

    return False, details


def _can_hover_content_without_disappearing(element: Tag, html_source: str) -> tuple[bool, list[str]]:
    """
    Vérifie si le contenu additionnel peut être survolé par la souris
    sans disparaître (test 10.13.2).
    Cela nécessite généralement que le contenu soit dans le même contexte
    de survol que le déclencheur (structure parent/enfant ou sibling adjacent).
    """
    details = []

    # Vérifier la structure DOM : le contenu doit être accessible depuis le déclencheur
    # sans sortir de la zone de survol
    # Cela est difficile à déterminer statiquement, on cherche des indices

    # Si le contenu est enfant du déclencheur, c'est généralement OK
    parent = element.parent
    if parent:
        # Chercher si le parent a des styles hover qui affichent l'enfant
        parent_style = _get_inline_style(parent).lower()
        if ":hover" in parent_style:
            details.append("Contenu enfant d'un élément avec :hover")
            return True, details

    # Vérifier les règles CSS pour des sélecteurs comme .parent:hover .child
    rules = _extract_stylesheet_rules(html_source)
    visible_props = [
        "display:block",
        "display:flex",
        "display:grid",
        "visibility:visible",
        "opacity:1",
    ]
    for selector, declarations in rules:
        if ":hover" in selector:
            # Pattern .trigger:hover .content ou .trigger:hover > .content
            if _matches_selector(element, selector):
                decl_lower = declarations.lower().replace(" ", "")  # Normalize spaces
                if any(prop in decl_lower for prop in visible_props):
                    details.append(f"CSS rule '{selector}' montre le contenu au hover du parent")
                    return True, details

    return False, details


def _content_remains_visible_until_dismissed(element: Tag, html_source: str) -> tuple[bool, list[str]]:
    """
    Vérifie si le contenu additionnel reste visible selon les conditions du test 10.13.3 :
    - Jusqu'à ce que l'utilisateur retire le pointeur/focus du contenu et du déclencheur
    - Jusqu'à ce que l'utilisateur déclenche une action de masquage
    - Jusqu'à ce que l'information ne soit plus valide
    """
    details = []

    # Vérifier s'il y a un timeout de masquage automatique (pas bon pour 10.13.3)
    timeout_patterns = [
        r"setTimeout.*hide",
        r"setTimeout.*close",
        r"setTimeout.*display\s*=\s*['\"]none['\"]",
        r"setTimeout.*\.style\.display",
        r"setInterval.*hide",
        r"setInterval.*close",
        r"setInterval.*display\s*=\s*['\"]none['\"]",
        r"delay.*hide",
    ]

    has_auto_hide = False
    for pattern in timeout_patterns:
        if re.search(pattern, html_source, re.IGNORECASE | re.DOTALL):
            has_auto_hide = True
            details.append("Script avec masquage automatique détecté (setTimeout/setInterval)")

    # Vérifier si le contenu a un rôle qui implique une persistance
    role = element.get("role", "").lower()
    if role in ["tooltip", "dialog", "alertdialog", "menu", "listbox"]:
        details.append(f"Rôle '{role}' implique une gestion de visibilité standard")

    # Vérifier aria-live pour les messages d'état
    if element.has_attr("aria-live"):
        details.append(f"aria-live={element.get('aria-live')} (message d'état)")

    # Pour le test 10.13.3, on ne peut pas déterminer statiquement
    # On signale pour vérification manuelle
    return not has_auto_hide, details


class Test10131(RGAATest):
    """Test 10.13.1 : Chaque contenu additionnel devenant visible à la prise de focus
    ou au survol d'un composant d'interface peut-il être masqué par une action
    de l'utilisateur sans déplacer le focus ou le pointeur de la souris (hors cas particuliers) ?"""

    test_id = "10.13.1"
    criterion_id = "10.13"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
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
        html_source = getattr(context, "html_source", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.13.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        if not isinstance(html_source, str) or not html_source.strip():
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible pour analyser les styles et scripts.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # Trouver les contenus additionnels affichés au hover/focus
        content_elements = _find_hover_focus_content_elements(soup, html_source)

        if not content_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu additionnel au survol/focus détecté (hors cas particuliers).",
                tested_elements=0,
            )

        findings: list[Finding] = []
        content_without_dismiss = 0

        for content_info in content_elements:
            element = content_info["element"]
            selector = content_info["selector"]

            # Vérifier s'il y a un mécanisme de masquage
            has_dismiss, dismiss_details = _has_dismiss_mechanism(element, html_source)

            # Vérifier si le contenu masque d'autres contenus informatifs
            # (difficile à déterminer statiquement, on signale pour vérification)
            masks_content = True  # Par défaut, on suppose qu'il peut masquer

            if not has_dismiss and masks_content:
                content_without_dismiss += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol/focus "
                            f"sans mécanisme de masquage détecté (touche Echap ou équivalent). "
                            f"Détails : {', '.join(content_info['show_details'])}. "
                            f"Masqué par défaut : {', '.join(content_info['hidden_reasons'])}."
                        ),
                        recommendation=(
                            "Ajouter un mécanisme permettant de masquer le contenu additionnel "
                            "sans déplacer le focus ni le pointeur de la souris. "
                            "La touche Echap (Escape) est la méthode recommandée. "
                            "Vérifier aussi que le contenu ne masque pas d'autres informations importantes."
                        ),
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "has_dismiss_mechanism": has_dismiss,
                            "dismiss_details": dismiss_details,
                            "masks_other_content": masks_content,
                            "test_id": self.test_id,
                            "needs_manual_check": True,
                            "condition": "no_dismiss_mechanism",
                            "wcag_criterion": "1.4.13",
                        },
                    )
                )
            else:
                # Contenu avec mécanisme de masquage ou ne masquant pas d'info
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol/focus "
                            f"avec mécanisme de masquage détecté ou ne masquant pas d'information. "
                            f"Détails : {', '.join(content_info['show_details'])}."
                        ),
                        recommendation=None,
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "has_dismiss_mechanism": has_dismiss,
                            "dismiss_details": dismiss_details,
                            "masks_other_content": masks_content,
                            "test_id": self.test_id,
                            "condition": "dismiss_mechanism_present",
                            "passed": True,
                        },
                    )
                )

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        if has_browser:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(content_elements)} contenu(s) additionnel(s) "
                f"au survol/focus détecté(s). {content_without_dismiss} sans mécanisme de masquage. "
                f"Un test réel avec navigateur est requis pour confirmer le comportement "
                f"(capacité BROWSER_INTERACTION disponible)."
            )
        elif content_without_dismiss > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse statique terminée : {len(content_elements)} contenu(s) additionnel(s) "
                f"au survol/focus détecté(s). {content_without_dismiss} sans mécanisme de masquage "
                f"(échec certain du critère 10.13.1)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Tous les {len(content_elements)} contenu(s) additionnel(s) au survol/focus "
                f"ont un mécanisme de masquage détecté ou ne masquent pas d'information."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(content_elements),
            metadata={
                "content_elements_found": len(content_elements),
                "without_dismiss_mechanism": content_without_dismiss,
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que chaque contenu additionnel peut être masqué via Echap",
                    "vérifier que le masquage ne déplace pas le focus ni le pointeur",
                    "vérifier que le contenu ne masque pas d'autres informations informatives",
                    "ignorer les cas particuliers : title natif, validation native, dialogues modaux",
                ],
                "manual_check_for": "critère 10.13.1 - masquage du contenu additionnel au survol/focus",
                "exceptions": [
                    "infobulles contrôlées par l'agent utilisateur (attribut title)",
                    "validation native de formulaire",
                    "contenus additionnels visibles par activation (dialogues modaux, menus aria-haspopup)",
                ],
                "reference": "WCAG 1.4.13 (AA) / EN 301 549 9.1.4.13",
            },
        )


class Test10132(RGAATest):
    """Test 10.13.2 : Chaque contenu additionnel qui apparait au survol d'un composant
    d'interface peut-il être survolé par le pointeur de la souris sans disparaître
    (hors cas particuliers) ?"""

    test_id = "10.13.2"
    criterion_id = "10.13"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
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
        html_source = getattr(context, "html_source", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.13.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        if not isinstance(html_source, str) or not html_source.strip():
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible pour analyser les styles et scripts.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # Trouver les contenus additionnels affichés au hover (pas au focus seul)
        content_elements = _find_hover_focus_content_elements(soup, html_source)

        # Filtrer pour ne garder que ceux qui sont déclenchés au hover
        # (difficile à distinguer statiquement, on teste tous les contenus additionnels)
        hover_content_elements = []
        for content_info in content_elements:
            # Vérifier si l'affichage est déclenché par :hover (vs :focus)
            show_details = content_info["show_details"]
            is_hover_triggered = any(":hover" in detail for detail in show_details)
            # Si on ne peut pas déterminer, on assume que c'est possible
            if is_hover_triggered or not any(":focus" in detail for detail in show_details):
                hover_content_elements.append(content_info)

        if not hover_content_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu additionnel au survol détecté (hors cas particuliers).",
                tested_elements=0,
            )

        findings: list[Finding] = []
        content_not_hoverable = 0

        for content_info in hover_content_elements:
            element = content_info["element"]
            selector = content_info["selector"]

            # Vérifier si le contenu peut être survolé sans disparaître
            can_hover, hover_details = _can_hover_content_without_disappearing(element, html_source)

            if not can_hover:
                content_not_hoverable += 1
                show_details_str = ", ".join(content_info["show_details"])
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol "
                            f"mais structure DOM/CSS ne garantit pas qu'il reste visible "
                            f"lorsque la souris le survole. Détails d'affichage : {show_details_str}."
                        ),
                        recommendation=(
                            "S'assurer que le contenu additionnel reste visible lorsque "
                            "l'utilisateur déplace la souris du déclencheur vers le contenu. "
                            "Structurer le DOM pour que le contenu soit enfant du déclencheur "
                            "ou utiliser des sélecteurs CSS appropriés (.trigger:hover .content). "
                            "Éviter les délais de masquage trop courts."
                        ),
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "can_hover_without_disappearing": can_hover,
                            "hover_details": hover_details,
                            "test_id": self.test_id,
                            "needs_manual_check": True,
                            "condition": "content_disappears_on_hover",
                            "wcag_criterion": "1.4.13",
                        },
                    )
                )
            else:
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol "
                            f"avec structure permettant le survol sans disparition. "
                            f"Détails : {', '.join(hover_details)}."
                        ),
                        recommendation=None,
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "can_hover_without_disappearing": can_hover,
                            "hover_details": hover_details,
                            "test_id": self.test_id,
                            "condition": "content_hoverable",
                            "passed": True,
                        },
                    )
                )

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        if has_browser:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(hover_content_elements)} contenu(s) additionnel(s) "
                f"au survol détecté(s). {content_not_hoverable} potentiellement non survolables. "
                f"Un test réel avec navigateur est requis pour confirmer le comportement "
                f"(capacité BROWSER_INTERACTION disponible)."
            )
        elif content_not_hoverable > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse statique terminée : {len(hover_content_elements)} contenu(s) additionnel(s) "
                f"au survol détecté(s). {content_not_hoverable} ne semblent pas pouvoir être "
                f"survolés sans disparaître (échec certain du critère 10.13.2)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Tous les {len(hover_content_elements)} contenu(s) additionnel(s) au survol "
                f"ont une structure permettant le survol sans disparition."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(hover_content_elements),
            metadata={
                "hover_content_elements_found": len(hover_content_elements),
                "not_hoverable": content_not_hoverable,
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "survoler le déclencheur, puis déplacer la souris vers le contenu additionnel",
                    "vérifier que le contenu reste visible pendant le survol",
                    "vérifier l'absence de délai de masquage trop court",
                    "ignorer les cas particuliers : title natif, validation native, dialogues modaux",
                ],
                "manual_check_for": "critère 10.13.2 - survol du contenu additionnel sans disparition",
                "exceptions": [
                    "infobulles contrôlées par l'agent utilisateur (attribut title)",
                    "validation native de formulaire",
                    "contenus additionnels visibles par activation (dialogues modaux, menus aria-haspopup)",
                ],
                "reference": "WCAG 1.4.13 (AA) / EN 301 549 9.1.4.13",
            },
        )


class Test10133(RGAATest):
    """Test 10.13.3 : Chaque contenu additionnel qui apparaît à la prise de focus
    ou au survol d'un composant d'interface vérifie-t-il une de ces conditions
    (hors cas particuliers) ?
    - Le contenu reste visible jusqu'à ce que l'utilisateur retire le pointeur/focus
    - Le contenu reste visible jusqu'à ce que l'utilisateur déclenche une action de masquage
    - Le contenu reste visible jusqu'à ce qu'il ne soit plus valide"""

    test_id = "10.13.3"
    criterion_id = "10.13"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
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
        html_source = getattr(context, "html_source", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.13.3 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        if not isinstance(html_source, str) or not html_source.strip():
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible pour analyser les styles et scripts.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # Trouver tous les contenus additionnels au hover/focus
        content_elements = _find_hover_focus_content_elements(soup, html_source)

        if not content_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu additionnel au survol/focus détecté (hors cas particuliers).",
                tested_elements=0,
            )

        findings: list[Finding] = []
        content_not_persistent = 0

        for content_info in content_elements:
            element = content_info["element"]
            selector = content_info["selector"]

            # Vérifier la persistance du contenu
            remains_visible, persist_details = _content_remains_visible_until_dismissed(element, html_source)

            # Vérifier aussi s'il y a un mécanisme de dismissal
            has_dismiss, dismiss_details = _has_dismiss_mechanism(element, html_source)

            # Déterminer si le contenu est un message d'état (valide tant que l'état persiste)
            is_status_message = False
            has_aria_live = element.has_attr("aria-live")
            role = element.get("role", "").lower()
            has_status_role = element.has_attr("role") and role == "status"
            if has_aria_live or has_status_role:
                is_status_message = True
                persist_details.append("Message d'état (aria-live/role=status)")

            if not remains_visible and not is_status_message:
                content_not_persistent += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol/focus "
                            f"mais peut disparaître avant que l'utilisateur ne retire le focus/pointeur "
                            f"ou ne déclenche une action de masquage. "
                            f"Détails : {', '.join(persist_details)}."
                        ),
                        recommendation=(
                            "S'assurer que le contenu additionnel reste visible selon l'une des conditions : "
                            "1) Jusqu'au retrait du pointeur/focus du contenu ET du déclencheur ; "
                            "2) Jusqu'à une action utilisateur de masquage (Echap, bouton fermer) ; "
                            "3) Jusqu'à ce que l'information ne soit plus valide (message d'erreur, état). "
                            "Éviter les timeouts de masquage automatique courts."
                        ),
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "remains_visible_until_dismissed": remains_visible,
                            "persist_details": persist_details,
                            "has_dismiss_mechanism": has_dismiss,
                            "dismiss_details": dismiss_details,
                            "is_status_message": is_status_message,
                            "test_id": self.test_id,
                            "needs_manual_check": True,
                            "condition": "content_not_persistent",
                            "wcag_criterion": "1.4.13",
                        },
                    )
                )
            else:
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel <{content_info['tag']}> affiché au survol/focus "
                            f"avec persistance conforme. "
                            f"Détails : {', '.join(persist_details)}."
                        ),
                        recommendation=None,
                        evidence={
                            "element_tag": content_info["tag"],
                            "selector": selector,
                            "hidden_reasons": content_info["hidden_reasons"],
                            "show_details": content_info["show_details"],
                            "remains_visible_until_dismissed": remains_visible,
                            "persist_details": persist_details,
                            "has_dismiss_mechanism": has_dismiss,
                            "dismiss_details": dismiss_details,
                            "is_status_message": is_status_message,
                            "test_id": self.test_id,
                            "condition": "content_persistent",
                            "passed": True,
                        },
                    )
                )

        # Vérifier si on a BROWSER_INTERACTION pour un test réel
        has_browser = services is not None and getattr(services, "browser_interaction", None) is not None

        if has_browser:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {len(content_elements)} contenu(s) additionnel(s) "
                f"au survol/focus détecté(s). {content_not_persistent} potentiellement non persistants. "
                f"Un test réel avec navigateur est requis pour confirmer le comportement "
                f"(capacité BROWSER_INTERACTION disponible)."
            )
        elif content_not_persistent > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse statique terminée : {len(content_elements)} contenu(s) additionnel(s) "
                f"au survol/focus détecté(s). {content_not_persistent} ne respectent pas "
                f"les conditions de persistance (échec certain du critère 10.13.3)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Tous les {len(content_elements)} contenu(s) additionnel(s) au survol/focus "
                f"respectent les conditions de persistance du critère 10.13.3."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(content_elements),
            metadata={
                "content_elements_found": len(content_elements),
                "not_persistent": content_not_persistent,
                "browser_interaction_available": has_browser,
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que le contenu reste visible jusqu'au retrait du focus/pointeur",
                    "vérifier que le contenu reste visible jusqu'à une action de masquage (Echap)",
                    "vérifier que les messages d'état restent visibles tant qu'ils sont valides",
                    "vérifier l'absence de timeouts de masquage automatique",
                    "ignorer les cas particuliers : title natif, validation native, dialogues modaux",
                ],
                "manual_check_for": "critère 10.13.3 - persistance du contenu additionnel au survol/focus",
                "exceptions": [
                    "infobulles contrôlées par l'agent utilisateur (attribut title)",
                    "validation native de formulaire",
                    "contenus additionnels visibles par activation (dialogues modaux, menus aria-haspopup)",
                ],
                "persistence_conditions": [
                    "visible jusqu'au retrait pointeur/focus du contenu ET du déclencheur",
                    "visible jusqu'à action utilisateur de masquage (Echap, bouton fermer)",
                    "visible jusqu'à ce que l'information ne soit plus valide (erreur, état)",
                ],
                "reference": "WCAG 1.4.13 (AA) / EN 301 549 9.1.4.13",
            },
        )

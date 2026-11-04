from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext


@dataclass
class CSSRule:
    """Représente une règle CSS parsée."""

    selector: str
    properties: dict[str, str]
    source: str  # "inline", "style_tag", "external"
    line_number: int | None = None


@dataclass
class PseudoClassRule:
    """Représente une règle CSS avec pseudo-classe (:hover, :focus, etc.)."""

    base_selector: str
    pseudo_class: str  # "hover", "focus", "active", etc.
    full_selector: str
    properties: dict[str, str]
    reveals_content: bool  # True si la règle rend visible du contenu caché


def extract_css_from_context(context: AuditContext) -> list[CSSRule]:
    """
    Extrait toutes les règles CSS de la page.

    Sources :
    - Balises <style>
    - Attributs style inline
    - Feuilles de style externes (si accessibles localement)
    """
    rules: list[CSSRule] = []

    if not isinstance(context.dom, BeautifulSoup):
        return rules

    soup = context.dom

    # 1. Balises <style>
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            css_text = style_tag.string
            line_num = style_tag.sourceline if hasattr(style_tag, "sourceline") else None
            rules.extend(_parse_css_text(css_text, "style_tag", line_num))

    # 2. Attributs style inline
    for element in soup.find_all(style=True):
        style_attr = element.get("style")
        if isinstance(style_attr, str) and style_attr.strip():
            # Pour le style inline, le sélecteur est l'élément lui-même
            selector = _get_element_selector(soup, element)
            properties = _parse_inline_style(style_attr)
            if properties:
                rules.append(
                    CSSRule(
                        selector=selector,
                        properties=properties,
                        source="inline",
                        line_number=element.sourceline if hasattr(element, "sourceline") else None,
                    )
                )

    # 3. Feuilles de style externes (link rel="stylesheet")
    # Note: On ne peut pas facilement récupérer le contenu des CSS externes
    # sans faire des requêtes HTTP. On se limite aux CSS inline et dans <style>.

    return rules


def _parse_css_text(css_text: str, source: str, base_line: int | None = None) -> list[CSSRule]:
    """Parse un texte CSS et retourne les règles."""
    rules: list[CSSRule] = []

    # Supprimer les commentaires
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

    # Pattern pour trouver les règles CSS: selector { properties }
    # Ce pattern est simplifié et ne gère pas tous les cas complexes
    rule_pattern = re.compile(r"([^{]+)\{([^}]+)\}", re.DOTALL)

    for match in rule_pattern.finditer(css_text):
        selector_text = match.group(1).strip()
        properties_text = match.group(2).strip()

        # Séparer les sélecteurs multiples (séparés par des virgules)
        selectors = [s.strip() for s in selector_text.split(",") if s.strip()]

        properties = _parse_css_properties(properties_text)

        if not properties:
            continue

        for selector in selectors:
            # Calculer le numéro de ligne approximatif
            line_num = None
            if base_line is not None:
                line_num = base_line + css_text[: match.start()].count("\n")

            rules.append(CSSRule(selector=selector, properties=properties, source=source, line_number=line_num))

    return rules


def _parse_css_properties(properties_text: str) -> dict[str, str]:
    """Parse les propriétés CSS d'une règle."""
    properties: dict[str, str] = {}

    # Pattern pour property: value;
    prop_pattern = re.compile(r"([\w-]+)\s*:\s*([^;]+);?", re.MULTILINE)

    for match in prop_pattern.finditer(properties_text):
        prop_name = match.group(1).strip().lower()
        prop_value = match.group(2).strip()
        properties[prop_name] = prop_value

    return properties


def _parse_inline_style(style_text: str) -> dict[str, str]:
    """Parse un attribut style inline."""
    return _parse_css_properties(style_text)


def _get_element_selector(soup: BeautifulSoup, element: Tag) -> str:
    """Génère un sélecteur CSS pour un élément."""
    # Essayer d'utiliser l'ID
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"

    # Essayer d'utiliser les classes
    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        class_str = ".".join(str(c) for c in classes[:2])
        return f"{element.name}.{class_str}"

    # Fallback: utiliser le nom de balise avec index
    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass

    return element.name or "unknown"


def find_pseudo_class_rules(rules: list[CSSRule]) -> list[PseudoClassRule]:
    """
    Trouve les règles CSS qui utilisent des pseudo-classes :hover, :focus, :active, etc.
    et qui révèlent du contenu (display, visibility, opacity, etc.).
    """
    pseudo_rules: list[PseudoClassRule] = []

    # Propriétés qui peuvent révéler/masquer du contenu
    reveal_properties = {
        "display": [
            "block",
            "flex",
            "grid",
            "inline",
            "inline-block",
            "inline-flex",
            "inline-grid",
            "table",
            "table-row",
            "table-cell",
        ],
        "visibility": ["visible"],
        "opacity": ["1", "0.9", "0.8", "0.7", "0.6", "0.5", "0.4", "0.3", "0.2", "0.1"],
        "overflow": ["visible", "auto", "scroll"],
        "height": ["auto"],  # hauteur auto peut révéler
        "max-height": ["none", "1000px", "9999px"],  # grandes valeurs
        "transform": [],  # transform peut révéler (translate, scale)
        "clip-path": [],  # clip-path peut révéler
        "z-index": [],  # z-index élevé peut révéler
    }

    # Propriétés qui masquent du contenu
    hide_properties = {
        "display": ["none"],
        "visibility": ["hidden", "collapse"],
        "opacity": ["0"],
        "overflow": ["hidden"],
        "height": ["0", "0px"],
        "max-height": ["0", "0px"],
        "transform": ["scale(0)", "translateX(-9999px)", "translateY(-9999px)"],
        "clip-path": ["inset(100%)"],
    }

    pseudo_classes = ["hover", "focus", "active", "focus-visible", "focus-within"]

    for rule in rules:
        selector = rule.selector.strip()

        # Chercher les pseudo-classes dans le sélecteur
        for pseudo in pseudo_classes:
            # Pattern pour :hover, :focus, etc. (pas ::before, ::after)
            pseudo_pattern = rf":{pseudo}\b"
            if re.search(pseudo_pattern, selector):
                # Extraire le sélecteur de base (sans la pseudo-classe)
                base_selector = re.sub(rf":{pseudo}\b", "", selector).strip()
                # Nettoyer les sélecteurs multiples
                base_selector = re.sub(r",\s*$", "", base_selector).strip()
                base_selector = re.sub(r"^\s*,", "", base_selector).strip()

                # Vérifier si cette règle révèle du contenu
                reveals = _rule_reveals_content(rule.properties, reveal_properties, hide_properties)

                pseudo_rules.append(
                    PseudoClassRule(
                        base_selector=base_selector,
                        pseudo_class=pseudo,
                        full_selector=selector,
                        properties=rule.properties,
                        reveals_content=reveals,
                    )
                )

    return pseudo_rules


def _rule_reveals_content(
    properties: dict[str, str], reveal_props: dict[str, list[str]], hide_props: dict[str, list[str]]
) -> bool:
    """Détermine si une règle CSS révèle du contenu précédemment masqué."""

    # D'abord vérifier si la règle contient des propriétés de révélation
    for prop, reveal_values in reveal_props.items():
        if prop in properties:
            value = properties[prop].lower()
            if not reveal_values:  # Toute valeur compte (ex: transform)
                return True
            for rv in reveal_values:
                if rv.lower() in value:
                    return True

    # Vérifier si la règle annule une propriété de masquage
    # (ex: display: block sur un élément qui a display: none par défaut)
    # C'est plus difficile à détecter sans connaître l'état initial

    return False


def _element_matches_selector(element: Tag, selector: str) -> bool:
    """Vérifie si un élément correspond à un sélecteur CSS."""
    try:
        # Utiliser BeautifulSoup's select pour tester
        # On ne peut pas tester directement un élément, donc on vérifie
        # si l'élément serait sélectionné par ce sélecteur
        parent = element.parent
        if parent is None:
            return False
        # Trouver tous les éléments qui correspondent au sélecteur dans le parent
        matches = parent.select(selector)
        return element in matches
    except Exception:
        return False


def _rule_hides_content(properties: dict[str, str]) -> tuple[bool, str]:
    """
    Vérifie si une règle CSS masque du contenu.
    Retourne (masque, méthode_de_masquage).
    """
    hide_properties = {
        "display": ["none"],
        "visibility": ["hidden", "collapse"],
        "opacity": ["0"],
        "overflow": ["hidden"],
        "height": ["0", "0px"],
        "max-height": ["0", "0px"],
    }

    for prop, hide_values in hide_properties.items():
        if prop in properties:
            value = properties[prop].lower()
            for hv in hide_values:
                if hv.lower() in value:
                    return True, f"{prop}_{hv.replace(':', '_').replace('(', '').replace(')', '')}"
    return False, ""


def find_elements_with_hidden_content(
    soup: BeautifulSoup,
    css_rules: list[CSSRule] | None = None,
) -> list[dict[str, Any]]:
    """
    Trouve les éléments qui semblent être du contenu caché (tooltips, dropdowns, etc.)
    basé sur leur style initial, leurs attributs, ou des règles CSS.
    """
    hidden_elements: list[dict[str, Any]] = []
    seen_selectors: set[str] = set()

    # 1. Vérifier les règles CSS (non pseudo-classes) qui masquent du contenu
    if css_rules:
        for rule in css_rules:
            # Ignorer les règles avec pseudo-classes (elles sont gérées séparément)
            pseudo_classes = ["hover", "focus", "active", "focus-visible", "focus-within"]
            if any(f":{pseudo}" in rule.selector for pseudo in pseudo_classes):
                continue

            hides, method = _rule_hides_content(rule.properties)
            if hides:
                try:
                    elements = soup.select(rule.selector)
                    for element in elements:
                        selector = _get_element_selector(soup, element)
                        if selector not in seen_selectors:
                            seen_selectors.add(selector)
                            hidden_elements.append(
                                {
                                    "element": element,
                                    "selector": selector,
                                    "hide_method": f"css_{method}",
                                }
                            )
                except Exception:
                    # Sélecteur invalide, ignorer
                    pass

    # 2. Vérifier les styles inline
    for element in soup.find_all(True):
        style = element.get("style", "")
        if isinstance(style, str):
            style_lower = style.lower()
            # Chercher des patterns de masquage
            if any(
                prop in style_lower
                for prop in [
                    "display:none",
                    "display: none",
                    "visibility:hidden",
                    "visibility: hidden",
                    "opacity:0",
                    "opacity: 0",
                    "height:0",
                    "height: 0px",
                    "max-height:0",
                    "max-height: 0px",
                    "overflow:hidden",
                    "overflow: hidden",
                ]
            ):
                selector = _get_element_selector(soup, element)
                if selector not in seen_selectors:
                    seen_selectors.add(selector)
                    hidden_elements.append(
                        {
                            "element": element,
                            "selector": selector,
                            "hide_method": _detect_hide_method(style_lower),
                        }
                    )

        # 3. Vérifier les attributs ARIA qui suggèrent du contenu conditionnel
        if element.get("role") in ["tooltip", "dialog", "alert", "status", "menu", "listbox", "tree"]:
            selector = _get_element_selector(soup, element)
            if selector not in seen_selectors:
                seen_selectors.add(selector)
                hidden_elements.append(
                    {
                        "element": element,
                        "selector": selector,
                        "hide_method": "aria_role",
                    }
                )

        # 4. Attributs hidden ou aria-hidden
        if element.has_attr("hidden") or element.get("aria-hidden") == "true":
            selector = _get_element_selector(soup, element)
            if selector not in seen_selectors:
                seen_selectors.add(selector)
                hidden_elements.append(
                    {
                        "element": element,
                        "selector": selector,
                        "hide_method": "hidden_attr",
                    }
                )

    return hidden_elements


def _detect_hide_method(style: str) -> str:
    """Détecte la méthode de masquage utilisée."""
    if "display:none" in style or "display: none" in style:
        return "display_none"
    if "visibility:hidden" in style or "visibility: hidden" in style:
        return "visibility_hidden"
    if "opacity:0" in style or "opacity: 0" in style:
        return "opacity_zero"
    if "height:0" in style or "height: 0px" in style:
        return "height_zero"
    if "max-height:0" in style or "max-height: 0px" in style:
        return "max_height_zero"
    if "overflow:hidden" in style or "overflow: hidden" in style:
        return "overflow_hidden"
    return "unknown"


def check_content_accessible_on_states(
    soup: BeautifulSoup,
    pseudo_rules: list[PseudoClassRule],
    hidden_elements: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Vérifie si le contenu révélé par :hover/:focus est aussi accessible
    via d'autres états (focus, active, autre composant).

    Retourne un dict avec les résultats par élément de contenu caché.
    """
    results = {
        "hover_revealed": [],  # Contenu révélé au hover
        "focus_revealed": [],  # Contenu révélé au focus
        "accessible_elsewhere": {},  # Pour chaque contenu, où il est accessible
    }

    # Grouper les règles pseudo par sélecteur de base
    hover_rules = [r for r in pseudo_rules if r.pseudo_class == "hover" and r.reveals_content]
    focus_rules = [r for r in pseudo_rules if r.pseudo_class == "focus" and r.reveals_content]
    active_rules = [r for r in pseudo_rules if r.pseudo_class == "active" and r.reveals_content]
    focus_visible_rules = [r for r in pseudo_rules if r.pseudo_class == "focus-visible" and r.reveals_content]
    focus_within_rules = [r for r in pseudo_rules if r.pseudo_class == "focus-within" and r.reveals_content]

    # Pour chaque élément caché, vérifier quels états le révèlent
    for hidden in hidden_elements:
        hidden_selector = hidden["selector"]

        # Vérifier quels pseudo-classes ciblent cet élément (ou un parent)
        hover_selectors = _find_matching_selectors(hover_rules, hidden_selector, soup)
        focus_selectors = _find_matching_selectors(focus_rules, hidden_selector, soup)
        active_selectors = _find_matching_selectors(active_rules, hidden_selector, soup)
        focus_visible_selectors = _find_matching_selectors(focus_visible_rules, hidden_selector, soup)
        focus_within_selectors = _find_matching_selectors(focus_within_rules, hidden_selector, soup)

        accessible_via = []
        if hover_selectors:
            accessible_via.append("hover")
        if focus_selectors:
            accessible_via.append("focus")
        if active_selectors:
            accessible_via.append("active")
        if focus_visible_selectors:
            accessible_via.append("focus-visible")
        if focus_within_selectors:
            accessible_via.append("focus-within")

        # Vérifier aussi l'activation via un autre composant (plus complexe)
        # Pour l'instant, on note simplement

        result = {
            "hidden_element": hidden_selector,
            "hide_method": hidden["hide_method"],
            "accessible_via": accessible_via,
            "hover_selectors": hover_selectors,
            "focus_selectors": focus_selectors,
            "active_selectors": active_selectors,
            "focus_visible_selectors": focus_visible_selectors,
            "focus_within_selectors": focus_within_selectors,
        }

        if "hover" in accessible_via:
            results["hover_revealed"].append(result)
        if "focus" in accessible_via:
            results["focus_revealed"].append(result)

        results["accessible_elsewhere"][hidden_selector] = accessible_via

    return results


def _find_matching_selectors(
    pseudo_rules: list[PseudoClassRule],
    target_selector: str,
    soup: BeautifulSoup,
) -> list[str]:
    """
    Trouve les règles pseudo qui peuvent cibler l'élément cible.
    C'est une approximation basée sur les sélecteurs CSS.
    """
    matching: list[str] = []

    for rule in pseudo_rules:
        base_sel = rule.base_selector.strip()
        if not base_sel:
            continue

        # Vérification simple: le sélecteur de base correspond-il à l'élément ou un ancêtre ?
        # On essaie de matcher le sélecteur CSS contre l'élément
        try:
            elements = soup.select(base_sel)
            for el in elements:
                # Vérifier si l'élément cible est cet élément ou un descendant
                target_el = soup.select_one(target_selector)
                if target_el and (el == target_el or el in target_el.parents):
                    matching.append(rule.full_selector)
                    break
        except Exception:
            # Sélecteur invalide, ignorer
            pass

    return matching

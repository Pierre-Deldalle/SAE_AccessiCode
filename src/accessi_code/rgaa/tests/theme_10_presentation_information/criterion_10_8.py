from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Expressions régulières pour détecter les propriétés CSS masquant le contenu
_DISPLAY_NONE_RE = re.compile(r"(?:^|;)\s*display\s*:\s*none\b", re.IGNORECASE)
_VISIBILITY_HIDDEN_RE = re.compile(r"(?:^|;)\s*visibility\s*:\s*hidden\b", re.IGNORECASE)
_OPACITY_ZERO_RE = re.compile(r"(?:^|;)\s*opacity\s*:\s*(0(?:px|em|rem|%)?|0?\.\d+)\b", re.IGNORECASE)
_POSITION_OFFSCREEN_RE = re.compile(
    r"(?:^|;)\s*(?:left|right|top|bottom)\s*:\s*(-?\d{4,}(?:px|em|rem|%))\b", re.IGNORECASE
)
_CLIP_RECT_ZERO_RE = re.compile(r"clip\s*:\s*rect\s*\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)", re.IGNORECASE)
_CLIP_PATH_RE = re.compile(r"clip-path\s*:\s*(?:inset|polygon|circle|ellipse)\s*\([^)]*\)", re.IGNORECASE)

# Classes CSS courantes pour masquer du contenu (visuellement mais pas pour AT)
_VISUALLY_HIDDEN_CLASSES = {
    "visually-hidden",
    "sr-only",
    "screen-reader-only",
    "sr-only-focusable",
    "a11y-hidden",
    "hidden",
    "invisible",
    "hide",
    "visuallyhidden",
}

# Attributs ARIA et HTML pour contenu caché
_HIDDEN_ATTR = "hidden"
_ARIA_HIDDEN_ATTR = "aria-hidden"
_TABINDEX_ATTR = "tabindex"
_ROLE_ATTR = "role"


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


def _inline_style(element: Tag) -> str:
    """Récupère le style en ligne d'un élément."""
    value = element.get("style", "")
    return value if isinstance(value, str) else ""


def _has_hidden_attribute(element: Tag) -> bool:
    """Vérifie si l'élément a l'attribut HTML5 hidden."""
    return element.has_attr(_HIDDEN_ATTR)


def _is_input_type_hidden(element: Tag) -> bool:
    """Vérifie si l'élément est un input type=hidden."""
    return element.name == "input" and element.get("type", "").lower() == "hidden"


def _has_aria_hidden(element: Tag) -> tuple[bool, str | None]:
    """Vérifie si l'élément a aria-hidden et retourne sa valeur."""
    value = element.get(_ARIA_HIDDEN_ATTR)
    if isinstance(value, str):
        value_lower = value.lower()
        # aria-hidden="false" signifie explicitement PAS masqué pour les AT
        if value_lower == "false":
            return False, None
        return True, value_lower
    return False, None


def _has_visually_hidden_class(element: Tag) -> bool:
    """Vérifie si l'élément a une classe de masquage visuel connu."""
    classes = element.get("class", [])
    if isinstance(classes, list):
        class_set = {c.lower() for c in classes}
        return bool(class_set & _VISUALLY_HIDDEN_CLASSES)
    return False


def _has_hidden_css_style(style: str) -> tuple[bool, list[str]]:
    """
    Vérifie si le style en ligne contient des propriétés masquant le contenu.
    Retourne (est_caché, liste_des_raisons).
    """
    reasons = []

    if _DISPLAY_NONE_RE.search(style):
        reasons.append("display: none")
    if _VISIBILITY_HIDDEN_RE.search(style):
        reasons.append("visibility: hidden")
    if _OPACITY_ZERO_RE.search(style):
        reasons.append("opacity: 0")
    if _POSITION_OFFSCREEN_RE.search(style):
        reasons.append("position off-screen")
    if _CLIP_RECT_ZERO_RE.search(style):
        reasons.append("clip: rect(0,0,0,0)")
    if _CLIP_PATH_RE.search(style):
        reasons.append("clip-path")

    return len(reasons) > 0, reasons


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


def _is_hidden_by_stylesheet(element: Tag, rules: list[tuple[str, str]]) -> tuple[bool, list[str], str | None]:
    """
    Vérifie si l'élément est masqué par une règle CSS dans <style>.
    Retourne (est_caché, raisons, sélecteur_correspondant).
    """
    tag = element.name.lower() if element.name else ""
    classes = element.get("class", [])
    class_selectors = [f".{c}" for c in classes] if isinstance(classes, list) else []
    element_id = element.get("id")
    id_selector = f"#{element_id}" if element_id else ""

    hidden_reasons = []
    matched_selector = None

    for selector, declarations in rules:
        selector_lower = selector.lower()
        matches = False

        if tag and tag in selector_lower:
            matches = True
        if class_selectors and any(c in selector_lower for c in class_selectors):
            matches = True
        if id_selector and id_selector in selector_lower:
            matches = True

        if matches:
            has_hidden, reasons = _has_hidden_css_style(declarations)
            if has_hidden:
                hidden_reasons.extend(reasons)
                matched_selector = selector

    return len(hidden_reasons) > 0, hidden_reasons, matched_selector


def _is_content_meant_for_at(element: Tag) -> bool:
    """
    Détermine si le contenu caché a vocation à être restitué par les technologies d'assistance.
    Contenu NON destiné aux AT : statistiques, tracking, métadonnées, etc.
    """
    # Rôle indiquant du contenu non destiné aux AT
    role = element.get(_ROLE_ATTR)
    if isinstance(role, str):
        role_lower = role.strip().lower()
        if role_lower in {"presentation", "none", "status"}:
            return False

    # aria-hidden="true" indique explicitement de ne pas restituer
    has_aria, aria_value = _has_aria_hidden(element)
    if has_aria and aria_value == "true":
        return False

    # Attribut hidden indique que le contenu n'est pas pertinent
    if _has_hidden_attribute(element):
        return False

    # Input type=hidden n'est pas destiné aux AT
    if _is_input_type_hidden(element):
        return False

    # Classes de masquage visuel seul (sr-only, visually-hidden) -> destiné aux AT
    if _has_visually_hidden_class(element):
        return True

    # Par défaut, on considère que le contenu caché pourrait être destiné aux AT
    # et nécessite une vérification manuelle
    return True


def _has_keyboard_trigger_before(element: Tag, soup: BeautifulSoup) -> tuple[bool, str | None]:
    """
    Vérifie s'il existe un élément focusable/interactif AVANT ce contenu
    qui pourrait déclencher son affichage (bouton, lien, etc.).
    """
    # Chercher les éléments précédents dans le DOM
    previous_elements = []
    for prev in element.previous_elements:
        if isinstance(prev, Tag):
            previous_elements.append(prev)
        if len(previous_elements) > 50:  # Limiter la recherche
            break

    for prev_elem in reversed(previous_elements):  # Du plus proche au plus loin
        if _is_focusable_or_interactive(prev_elem):
            selector = _selector_for(soup, prev_elem)
            return True, f"Élément interactif précédent : {selector} ({prev_elem.name})"

    return False, None


def _is_focusable_or_interactive(element: Tag) -> bool:
    """Vérifie si un élément est focusable ou interactif (peut déclencher une action)."""
    tag = element.name.lower() if element.name else ""

    # Éléments nativement focusables
    if tag in {"a", "button", "input", "select", "textarea", "details", "summary", "area"}:
        if tag == "a" and not element.has_attr("href"):
            return False
        if tag == "input" and element.get("type", "").lower() == "hidden":
            return False
        if tag == "area" and not element.find_parent("map"):
            return False
        return True

    # tabindex >= 0
    tabindex = element.get(_TABINDEX_ATTR)
    if tabindex is not None:
        try:
            return int(tabindex) >= 0
        except (ValueError, TypeError):  # fmt: skip
            pass

    # contenteditable
    if element.has_attr("contenteditable"):
        editable = element.get("contenteditable", "").lower()
        if editable in ("true", "plaintext-only"):
            return True

    # role button, link, etc.
    role = element.get(_ROLE_ATTR)
    if isinstance(role, str):
        role_lower = role.strip().lower()
        if role_lower in {"button", "link", "menuitem", "tab", "checkbox", "radio", "slider"}:
            return True

    return False


def _has_focus_repositioning_script(element: Tag, html_source: str) -> tuple[bool, str | None]:
    """
    Vérifie s'il existe du JavaScript qui repositionne le focus sur cet élément.
    Recherche basique de patterns comme element.focus(), focus(), etc.
    """
    element_id = element.get("id")
    if not element_id:
        return False, None

    # Patterns de recherche de focus programmatique
    focus_patterns = [
        rf"document\.getElementById\s*\(\s*['\"]{re.escape(element_id)}['\"]\s*\)\s*\.\s*focus\s*\(",
        rf"\$\s*\(\s*['\"]#{re.escape(element_id)}['\"]\s*\)\s*\.\s*focus\s*\(",
        rf"['\"]#{re.escape(element_id)}['\"]\s*\.\s*focus\s*\(",
        rf"focus\s*\(\s*['\"]#{re.escape(element_id)}['\"]\s*\)",
    ]

    for pattern in focus_patterns:
        if re.search(pattern, html_source, re.IGNORECASE):
            return True, f"Script détecté repositionnant le focus sur #{element_id}"

    return False, None


def _analyze_hidden_content(
    soup: BeautifulSoup,
    element: Tag,
    html_source: str,
    stylesheet_rules: list[tuple[str, str]],
    test_id: str,
) -> list[Finding]:
    """Analyse un élément masqué pour le test 10.8.1."""
    selector = _selector_for(soup, element)
    findings: list[Finding] = []

    # Détecter pourquoi l'élément est caché
    hidden_reasons = []
    hidden_methods = []

    # 1. Attribut hidden
    if _has_hidden_attribute(element):
        hidden_reasons.append("attribut HTML hidden")
        hidden_methods.append("hidden")

    # 1b. Input type=hidden
    if _is_input_type_hidden(element):
        hidden_reasons.append("input type=hidden")
        hidden_methods.append("input-hidden")

    # 2. aria-hidden
    has_aria, aria_value = _has_aria_hidden(element)
    if has_aria:
        hidden_reasons.append(f'aria-hidden="{aria_value}"')
        hidden_methods.append("aria-hidden")

    # 3. Classes de masquage visuel
    if _has_visually_hidden_class(element):
        classes = element.get("class", [])
        matching = [c for c in classes if isinstance(c, str) and c.lower() in _VISUALLY_HIDDEN_CLASSES]
        hidden_reasons.append(f"classe(s) de masquage visuel : {', '.join(matching)}")
        hidden_methods.append("css-class")

    # 4. Style en ligne
    inline_style = _inline_style(element)
    if inline_style:
        has_hidden, reasons = _has_hidden_css_style(inline_style)
        if has_hidden:
            hidden_reasons.extend([f"style en ligne : {r}" for r in reasons])
            hidden_methods.append("inline-style")

    # 5. Feuille de style interne
    hidden_by_css, css_reasons, css_selector = _is_hidden_by_stylesheet(element, stylesheet_rules)
    if hidden_by_css:
        hidden_reasons.extend([f"feuille de style ({css_selector}) : {r}" for r in css_reasons])
        hidden_methods.append("stylesheet")

    # Si aucune raison de masquage détectée, l'élément n'est pas dans le périmètre
    if not hidden_reasons:
        return []

    # Déterminer si le contenu est destiné aux technologies d'assistance
    meant_for_at = _is_content_meant_for_at(element)

    # Construire le message de base
    base_message = f"Contenu caché détecté ({', '.join(hidden_reasons)}) sur l'élément <{element.name}>. "

    if not meant_for_at:
        # Cas 1 : Contenu qui a vocation à être ignoré par les AT
        findings.append(
            Finding(
                element=selector,
                message=base_message + "Ce contenu a vocation à être ignoré par les technologies d'assistance.",
                recommendation=None,
                evidence={
                    "hidden_methods": hidden_methods,
                    "hidden_reasons": hidden_reasons,
                    "meant_for_at": False,
                    "test_id": test_id,
                    "condition": "ignored_by_at",
                    "passed": True,
                },
            )
        )
    else:
        # Cas 2 : Contenu qui DOIT être restituable par les AT
        # Vérifier s'il y a un déclencheur clavier/souris avant
        has_trigger, trigger_info = _has_keyboard_trigger_before(element, soup)

        # Vérifier s'il y a un repositionnement de focus programmatique
        has_focus_script, script_info = _has_focus_repositioning_script(element, html_source)

        if has_trigger or has_focus_script:
            # Le contenu est restituable via une action utilisateur ou script
            details = []
            if has_trigger:
                details.append(trigger_info)
            if has_focus_script:
                details.append(script_info)

            findings.append(
                Finding(
                    element=selector,
                    message=base_message + "Le contenu est restituable via : " + " ; ".join(details),
                    recommendation=None,
                    evidence={
                        "hidden_methods": hidden_methods,
                        "hidden_reasons": hidden_reasons,
                        "meant_for_at": True,
                        "has_trigger": has_trigger,
                        "trigger_info": trigger_info,
                        "has_focus_script": has_focus_script,
                        "script_info": script_info,
                        "test_id": test_id,
                        "condition": "restorable",
                        "passed": True,
                    },
                )
            )
        else:
            # Pas de mécanisme de restitution détecté -> NEEDS_REVIEW
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        base_message + "Ce contenu devrait être restituable par les technologies d'assistance, "
                        "mais aucun mécanisme de déclenchement (action utilisateur sur élément précédent "
                        "ou repositionnement de focus) n'a été détecté statiquement."
                    ),
                    recommendation=(
                        "Vérifier manuellement que : "
                        "1) Ce contenu a bien vocation à être restitué par les AT ; "
                        "2) Il est rendu accessible via une action utilisateur (clic/clavier sur un élément précédent) "
                        "ou un repositionnement programmatique du focus ; "
                        '3) Sinon, ajouter aria-hidden="true" ou l\'attribut hidden si ce contenu doit être ignoré.'
                    ),
                    evidence={
                        "hidden_methods": hidden_methods,
                        "hidden_reasons": hidden_reasons,
                        "meant_for_at": True,
                        "has_trigger": False,
                        "has_focus_script": False,
                        "test_id": test_id,
                        "condition": "restorable",
                        "needs_manual_check": True,
                    },
                )
            )

    return findings


def _analyze_stylesheet_for_hidden_content(
    html_source: str,
    test_id: str,
) -> list[Finding]:
    """Analyse les règles CSS pour détecter du contenu potentiellement masqué."""
    rules = _extract_stylesheet_rules(html_source)
    findings: list[Finding] = []

    for selector, declarations in rules:
        has_hidden, reasons = _has_hidden_css_style(declarations)
        if has_hidden:
            # Vérifier si c'est une classe de masquage visuel connue
            is_visually_hidden_class = any(cls in selector.lower() for cls in _VISUALLY_HIDDEN_CLASSES)

            if is_visually_hidden_class:
                css_message = "Classe de masquage visuel (destinée aux AT)."
            else:
                css_message = "Vérifier si ce contenu doit être accessible aux AT."

            findings.append(
                Finding(
                    element=selector[:160],
                    message=(f"Règle CSS masquant du contenu : '{selector}' ({', '.join(reasons)}). {css_message}"),
                    recommendation=(
                        "Vérifier dans le navigateur si cette règle s'applique à du contenu "
                        "qui devrait être restitué par les technologies d'assistance. "
                        "Si oui, s'assurer qu'un mécanisme de restitution existe (action utilisateur ou focus)."
                    ),
                    evidence={
                        "selector": selector[:160],
                        "declarations": declarations[:300],
                        "source_type": "stylesheet",
                        "hidden_reasons": reasons,
                        "is_visually_hidden_class": is_visually_hidden_class,
                        "risk_type": "stylesheet_hidden_content",
                        "test_id": test_id,
                    },
                )
            )

    return findings


class Test1081(RGAATest):
    """Test 10.8.1 : Pour chaque page web, chaque contenu caché vérifie l'une des conditions :
    - vocation à être ignoré par les technologies d'assistance, OU
    - restituable par les technologies d'assistance via action utilisateur ou repositionnement de focus."""

    test_id = "10.8.1"
    criterion_id = "10.8"

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
                summary="Le DOM n'est pas disponible ; le test 10.8.1 nécessite l'analyse de la page.",
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

        # Trouver tous les éléments potentiellement cachés
        # On examine tous les éléments car n'importe lequel peut être caché
        all_elements = soup.find_all(True)

        if not all_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun élément dans la page.",
                tested_elements=0,
            )

        # Extraire les règles CSS pour analyse
        stylesheet_rules = _extract_stylesheet_rules(html_source)

        findings: list[Finding] = []
        hidden_elements_count = 0

        for element in all_elements:
            element_findings = _analyze_hidden_content(soup, element, html_source, stylesheet_rules, self.test_id)
            if element_findings:
                hidden_elements_count += 1
            findings.extend(element_findings)

        # Analyser aussi les règles CSS internes
        css_findings = _analyze_stylesheet_for_hidden_content(html_source, self.test_id)
        findings.extend(css_findings)

        # Déterminer le statut global
        # Échecs certains : pas de mécanisme de restitution détecté ET meant_for_at=True
        # Mais comme on ne peut pas être certain statiquement, on met en NEEDS_REVIEW
        # Les vrais FAIL sont détectés si on peut prouver l'absence de mécanisme
        # Pour l'instant, on suit la logique : incertitude -> NEEDS_REVIEW

        needs_review_findings = [
            f
            for f in findings
            if f.evidence.get("needs_manual_check", False) or f.evidence.get("risk_type") == "stylesheet_hidden_content"
        ]

        pass_findings = [
            f
            for f in findings
            if f.evidence.get("condition") in {"ignored_by_at", "restorable"} and f.evidence.get("passed") is True
        ]

        # Logique de statut : FAIL > NEEDS_REVIEW > PASS
        # Note : Dans ce test, on ne produit pas de FAIL certain statiquement
        # car on ne peut pas prouver l'absence de mécanisme JS complexe
        # On signale en NEEDS_REVIEW pour vérification manuelle
        if needs_review_findings or css_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse statique terminée : {hidden_elements_count} élément(s) caché(s) détecté(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s) pour la restitution aux AT. "
                f"{len(css_findings)} règle(s) CSS de masquage détectée(s). "
                "La validation exige un contrôle manuel du critère 10.8.1."
            )
        elif pass_findings and hidden_elements_count > 0:
            status = TestStatus.PASS
            summary = (
                f"Tous les {hidden_elements_count} élément(s) caché(s) respectent le critère : "
                f"{len(pass_findings)} condition(s) validée(s) (ignoré par AT ou restituable)."
            )
        else:
            status = TestStatus.PASS
            summary = "Aucun contenu caché détecté dans la page."

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=hidden_elements_count,
            metadata={
                "total_elements_checked": len(all_elements),
                "hidden_elements_found": hidden_elements_count,
                "potential_issues": len(findings),
                "pass_conditions": len(pass_findings),
                "needs_review_conditions": len(needs_review_findings),
                "stylesheet_risks": len(css_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que chaque contenu caché a vocation à être ignoré par les AT, "
                    "ou est restituable via action utilisateur sur élément précédent",
                    "vérifier l'existence d'un repositionnement programmatique du focus",
                    "vérifier la cohérence aria-hidden / hidden avec l'état visuel",
                ],
                "manual_check_for": "critère 10.8.1 - contenus cachés et technologies d'assistance",
            },
        )

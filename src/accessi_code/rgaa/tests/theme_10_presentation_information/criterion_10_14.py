from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.css import (
    check_content_accessible_on_states,
    extract_css_from_context,
    find_elements_with_hidden_content,
    find_pseudo_class_rules,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


def _selector_for(soup: BeautifulSoup, element) -> str:
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


class Test10141(RGAATest):
    """
    Test 10.14.1 : Dans chaque page web, les contenus additionnels apparaissant au survol
    d'un composant d'interface via les styles CSS respectent-ils si nécessaire une de ces conditions ?

    Les contenus additionnels apparaissent également à l'activation du composant
    via le clavier et tout dispositif de pointage ;
    Les contenus additionnels apparaissent également à la prise de focus du composant ;
    Les contenus additionnels apparaissent également par le biais de l'activation
    ou de la prise de focus d'un autre composant.
    """

    test_id = "10.14.1"
    criterion_id = "10.14"

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

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.14.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Vérifier la disponibilité du code source HTML (requis pour l'analyse CSS)
        if not getattr(context, "html_source", None):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible ; le test 10.14.1 nécessite l'analyse du CSS.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # 1. Extraire toutes les règles CSS de la page
        css_rules = extract_css_from_context(context)

        if not css_rules:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucune règle CSS détectée dans la page.",
                tested_elements=0,
                metadata={"css_rules_found": 0},
            )

        # 2. Trouver les règles avec pseudo-classes qui révèlent du contenu
        pseudo_rules = find_pseudo_class_rules(css_rules)

        # Filtrer seulement :hover (pour ce test)
        hover_rules = [r for r in pseudo_rules if r.pseudo_class == "hover" and r.reveals_content]

        if not hover_rules:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu additionnel révélé au survol (:hover) détecté.",
                tested_elements=0,
                metadata={
                    "css_rules_found": len(css_rules),
                    "hover_rules_found": 0,
                },
            )

        # 3. Trouver les éléments qui semblent être du contenu caché (tooltips, dropdowns, etc.)
        hidden_elements = find_elements_with_hidden_content(soup, css_rules)

        # 4. Vérifier l'accessibilité du contenu révélé au hover via d'autres états
        accessibility_results = check_content_accessible_on_states(soup, pseudo_rules, hidden_elements)

        hover_revealed = accessibility_results["hover_revealed"]

        if not hover_revealed:
            # Il y a des règles :hover mais aucun élément caché détecté qui correspond
            # Cela peut être normal (ex: changement de couleur au hover)
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary=(
                    f"{len(hover_rules)} règle(s) :hover détectée(s) mais aucun "
                    "contenu additionnel caché correspondant trouvé."
                ),
                tested_elements=len(hover_rules),
                metadata={
                    "css_rules_found": len(css_rules),
                    "hover_rules_found": len(hover_rules),
                    "hidden_elements_found": len(hidden_elements),
                },
            )

        # 5. Analyser chaque contenu révélé au hover
        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0

        for item in hover_revealed:
            hidden_selector = item["hidden_element"]
            accessible_via = item["accessible_via"]
            hide_method = item["hide_method"]

            # Vérifier la conformité selon RGAA 10.14.1
            # Le contenu doit être accessible via AU MOINS UNE de ces conditions :
            # 1. Activation du composant (clavier/souris) -> :active
            # 2. Prise de focus du composant -> :focus, :focus-visible
            # 3. Activation ou focus d'un autre composant -> focus sur un autre élément

            is_compliant = False
            compliance_methods = []

            # Condition 1: Activation (:active)
            if "active" in accessible_via:
                is_compliant = True
                compliance_methods.append("activation (:active)")

            # Condition 2: Focus (:focus, :focus-visible, :focus-within)
            if "focus" in accessible_via or "focus-visible" in accessible_via or "focus-within" in accessible_via:
                is_compliant = True
                if "focus" in accessible_via:
                    compliance_methods.append("focus (:focus)")
                if "focus-visible" in accessible_via:
                    compliance_methods.append("focus visible (:focus-visible)")
                if "focus-within" in accessible_via:
                    compliance_methods.append("focus within (:focus-within)")

            # Condition 3: Focus/activation d'un autre composant
            # Difficile à détecter statiquement, on note comme vérification manuelle
            # Si le contenu est accessible via :focus sur un autre sélecteur
            # (ex: .parent:focus .tooltip), on peut le détecter
            other_component_focus = False
            for rule_sel in item.get("focus_selectors", []):
                if rule_sel != hidden_selector and not rule_sel.startswith(hidden_selector):
                    # Le focus est sur un autre élément qui révèle ce contenu
                    other_component_focus = True
                    break

            if other_component_focus:
                is_compliant = True
                compliance_methods.append("focus sur un autre composant")

            selector = hidden_selector

            if is_compliant:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel révélé au survol (méthode de masquage: {hide_method}) "
                            f"est également accessible via : {', '.join(compliance_methods)}."
                        ),
                        recommendation=(
                            "Conforme au critère 10.14.1. Le contenu additionnel est accessible "
                            "sans survol de la souris."
                        ),
                        evidence={
                            "hide_method": hide_method,
                            "compliance_methods": compliance_methods,
                            "accessible_via": accessible_via,
                            "hover_selectors": item.get("hover_selectors", []),
                            "focus_selectors": item.get("focus_selectors", []),
                            "active_selectors": item.get("active_selectors", []),
                            "test_id": self.test_id,
                        },
                    )
                )
            else:
                non_compliant_count += 1
                accessible_str = ", ".join(accessible_via) if accessible_via else "aucun"
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel révélé uniquement au survol "
                            f"(méthode de masquage: {hide_method}) "
                            f"n'est pas accessible via activation, focus, "
                            f"ou focus d'un autre composant. "
                            f"États d'accessibilité détectés : {accessible_str}."
                        ),
                        recommendation=(
                            "Rendre le contenu additionnel accessible au clavier : "
                            "1) L'afficher aussi au focus (:focus, :focus-visible) du composant déclencheur ; "
                            "2) L'afficher aussi à l'activation (:active) du composant ; "
                            "3) Ou le rendre accessible via l'activation/focus d'un autre composant "
                            "(ex: bouton 'Afficher l'aide'). "
                            "Utiliser :focus-visible pour l'accessibilité clavier sans affecter le style souris."
                        ),
                        evidence={
                            "hide_method": hide_method,
                            "accessible_via": accessible_via,
                            "hover_selectors": item.get("hover_selectors", []),
                            "focus_selectors": item.get("focus_selectors", []),
                            "active_selectors": item.get("active_selectors", []),
                            "needs_manual_check": True,
                            "test_id": self.test_id,
                        },
                    )
                )

        # 6. Déterminer le statut global
        tested_elements = len(hover_revealed)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) additionnel(s) révélé(s) au survol. "
                f"{non_compliant_count} non conforme(s) (accessible uniquement au survol), "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) additionnel(s) révélé(s) au survol. "
                f"Tous sont accessibles via d'autres moyens (focus, activation, ou autre composant)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "css_rules_found": len(css_rules),
                "hover_rules_found": len(hover_rules),
                "hidden_elements_found": len(hidden_elements),
                "hover_revealed_count": len(hover_revealed),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que le contenu au survol est accessible au clavier (Tab, Entrée, Espace)",
                    "vérifier :focus-visible pour les styles de focus clavier uniquement",
                    "vérifier l'accessibilité via un bouton/lien explicite pour afficher le contenu",
                    "vérifier que le contenu reste visible assez longtemps pour être lu",
                ],
                "manual_check_for": "critère 10.14.1 - contenus additionnels au survol",
            },
        )


class Test10142(RGAATest):
    """
    Test 10.14.2 : Dans chaque page web, les contenus additionnels apparaissant au focus
    d'un composant d'interface via les styles CSS respectent-ils si nécessaire une de ces conditions ?

    Les contenus additionnels apparaissent également à l'activation du composant
    via le clavier et tout dispositif de pointage ;
    Les contenus additionnels apparaissent également au survol du composant ;
    Les contenus additionnels apparaissent également par le biais de l'activation
    ou du survol d'un autre composant.
    """

    test_id = "10.14.2"
    criterion_id = "10.14"

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

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.14.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Vérifier la disponibilité du code source HTML (requis pour l'analyse CSS)
        if not getattr(context, "html_source", None):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible ; le test 10.14.2 nécessite l'analyse du CSS.",
                tested_elements=0,
                metadata={"reason": "missing_html_source"},
            )

        # 1. Extraire toutes les règles CSS de la page
        css_rules = extract_css_from_context(context)

        if not css_rules:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucune règle CSS détectée dans la page.",
                tested_elements=0,
                metadata={"css_rules_found": 0},
            )

        # 2. Trouver les règles avec pseudo-classes qui révèlent du contenu
        pseudo_rules = find_pseudo_class_rules(css_rules)

        # Filtrer seulement :focus, :focus-visible, :focus-within (pour ce test)
        focus_pseudo_classes = ["focus", "focus-visible", "focus-within"]
        focus_rules = [r for r in pseudo_rules if r.pseudo_class in focus_pseudo_classes and r.reveals_content]

        if not focus_rules:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu additionnel révélé au focus (:focus, :focus-visible, :focus-within) détecté.",
                tested_elements=0,
                metadata={
                    "css_rules_found": len(css_rules),
                    "focus_rules_found": 0,
                },
            )

        # 3. Trouver les éléments qui semblent être du contenu caché
        hidden_elements = find_elements_with_hidden_content(soup, css_rules)

        # 4. Vérifier l'accessibilité du contenu révélé au focus via d'autres états
        accessibility_results = check_content_accessible_on_states(soup, pseudo_rules, hidden_elements)

        focus_revealed = accessibility_results["focus_revealed"]

        if not focus_revealed:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary=(
                    f"{len(focus_rules)} règle(s) :focus/:focus-visible/:focus-within détectée(s) mais aucun "
                    "contenu additionnel caché correspondant trouvé."
                ),
                tested_elements=len(focus_rules),
                metadata={
                    "css_rules_found": len(css_rules),
                    "focus_rules_found": len(focus_rules),
                    "hidden_elements_found": len(hidden_elements),
                },
            )

        # 5. Analyser chaque contenu révélé au focus
        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0

        for item in focus_revealed:
            hidden_selector = item["hidden_element"]
            accessible_via = item["accessible_via"]
            hide_method = item["hide_method"]

            # Vérifier la conformité selon RGAA 10.14.2
            # Le contenu doit être accessible via AU MOINS UNE de ces conditions :
            # 1. Activation du composant (clavier/souris) -> :active
            # 2. Survol du composant -> :hover
            # 3. Activation ou survol d'un autre composant

            is_compliant = False
            compliance_methods = []

            # Condition 1: Activation (:active)
            if "active" in accessible_via:
                is_compliant = True
                compliance_methods.append("activation (:active)")

            # Condition 2: Survol (:hover)
            if "hover" in accessible_via:
                is_compliant = True
                compliance_methods.append("survol (:hover)")

            # Condition 3: Activation ou survol d'un autre composant
            other_component_hover = False
            other_component_active = False

            for rule_sel in item.get("hover_selectors", []):
                if rule_sel != hidden_selector and not rule_sel.startswith(hidden_selector):
                    other_component_hover = True
                    break

            for rule_sel in item.get("active_selectors", []):
                if rule_sel != hidden_selector and not rule_sel.startswith(hidden_selector):
                    other_component_active = True
                    break

            if other_component_hover:
                is_compliant = True
                compliance_methods.append("survol d'un autre composant")
            if other_component_active:
                is_compliant = True
                compliance_methods.append("activation d'un autre composant")

            selector = hidden_selector

            if is_compliant:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel révélé au focus (méthode de masquage: {hide_method}) "
                            f"est également accessible via : {', '.join(compliance_methods)}."
                        ),
                        recommendation=(
                            "Conforme au critère 10.14.2. Le contenu additionnel est accessible "
                            "sans focus clavier exclusif."
                        ),
                        evidence={
                            "hide_method": hide_method,
                            "compliance_methods": compliance_methods,
                            "accessible_via": accessible_via,
                            "focus_selectors": item.get("focus_selectors", []),
                            "hover_selectors": item.get("hover_selectors", []),
                            "active_selectors": item.get("active_selectors", []),
                            "test_id": self.test_id,
                        },
                    )
                )
            else:
                non_compliant_count += 1
                accessible_str = ", ".join(accessible_via) if accessible_via else "aucun"
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu additionnel révélé uniquement au focus "
                            f"(méthode de masquage: {hide_method}) "
                            f"n'est pas accessible via activation, survol, "
                            f"ou survol/activation d'un autre composant. "
                            f"États d'accessibilité détectés : {accessible_str}."
                        ),
                        recommendation=(
                            "Rendre le contenu additionnel accessible : "
                            "1) L'afficher aussi au survol (:hover) du composant déclencheur ; "
                            "2) L'afficher aussi à l'activation (:active) du composant ; "
                            "3) Ou le rendre accessible via le survol/activation d'un autre composant "
                            "(ex: bouton 'Afficher l'aide')."
                        ),
                        evidence={
                            "hide_method": hide_method,
                            "accessible_via": accessible_via,
                            "focus_selectors": item.get("focus_selectors", []),
                            "hover_selectors": item.get("hover_selectors", []),
                            "active_selectors": item.get("active_selectors", []),
                            "needs_manual_check": True,
                            "test_id": self.test_id,
                        },
                    )
                )

        # 6. Déterminer le statut global
        tested_elements = len(focus_revealed)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) additionnel(s) révélé(s) au focus. "
                f"{non_compliant_count} non conforme(s) (accessible uniquement au focus), "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) additionnel(s) révélé(s) au focus. "
                f"Tous sont accessibles via d'autres moyens (survol, activation, ou autre composant)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "css_rules_found": len(css_rules),
                "focus_rules_found": len(focus_rules),
                "hidden_elements_found": len(hidden_elements),
                "focus_revealed_count": len(focus_revealed),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que le contenu au focus est aussi accessible au survol",
                    "vérifier que le contenu au focus est aussi accessible à l'activation",
                    "vérifier l'accessibilité via un bouton/lien explicite pour afficher le contenu",
                    "vérifier que le contenu ne disparaît pas immédiatement au déplacement de la souris",
                ],
                "manual_check_for": "critère 10.14.2 - contenus additionnels au focus",
            },
        )

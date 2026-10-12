from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from typing import Any, Set

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test711(RGAATest):
    test_id = "7.1.1"
    criterion_id = "7.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 7.1.1 nécessite un DOM.")

        soup = context.dom

        # Find elements that are likely script-controlled:
        # - Elements with event handlers (onclick, onchange, etc.)
        # - Elements with role attributes (indicating custom widgets)
        script_elements = self._find_script_controlled_elements(soup)

        if not script_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun composant d'interface généré ou contrôlé par script détecté.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, element in enumerate(script_elements):
            # Check 7.1.1: Component has accessibility API support or accessible alternative
            if self._has_accessibility_support(element, soup):
                compliant_count += 1
                continue

            # No accessibility support found
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "Le composant d'interface généré ou contrôlé par script ne possède "
                        "pas de support d'accessibilité via une API d'accessibilité, "
                        "ni de composant d'interface accessible équivalent, "
                        "ni d'alternative accessible."
                    ),
                    recommendation=(
                        "Ajouter un rôle ARIA approprié, un nom accessible via aria-label ou aria-labelledby, "
                        "ou fournir une alternative accessible permettant d'accéder aux mêmes fonctionnalités."
                    ),
                )
            )

        # Determine status based on findings
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(script_elements)} composant(s) d'interface généré(s) ou contrôlé(s) par script : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(script_elements),
            metadata={
                "script_controlled_elements": len(script_elements),
                "compliant_elements": compliant_count,
                "non_compliant_elements": len(findings),
            },
        )

    def _find_script_controlled_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find elements likely to be generated or controlled by scripts."""
        script_elements: set[Tag] = set()

        # Common event handler attributes
        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus"
        }

        # Find elements with event handlers
        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        # Find elements with role attribute (custom widgets)
        role_elements = soup.find_all(attrs={"role": True})
        script_elements.update(role_elements)

        return list(script_elements)

    def _has_accessibility_support(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if element has accessibility support per 7.1.1:
        - Has a role consistent with its usage via accessibility API
        - OR an accessible interface component providing same functionality exists
        - OR an accessible alternative allows same functionality
        """
        # Check if element has a role attribute
        role = element.get("role")
        if role and isinstance(role, str) and role.strip():
            # Has a role - check if it's appropriate for the element type
            # For simplicity, we consider any non-empty role as potentially valid
            # In a more complete implementation, we'd validate role appropriateness
            return True

        # Check for accessible name (aria-label or aria-labelledby)
        aria_label = element.get("aria-label")
        if aria_label and isinstance(aria_label, str) and aria_label.strip():
            return True

        aria_labelledby = element.get("aria-labelledby")
        if aria_labelledby and isinstance(aria_labelledby, str) and aria_labelledby.strip():
            # Check if the referenced element exists and has content
            labelled_element = soup.find(id=aria_labelledby)
            if labelled_element and labelled_element.get_text(strip=True):
                return True

        # Check for native accessibility (button, link, etc. with content)
        if element.name in ("button", "a", "textarea"):
            # Check if element has visible content
            if element.get_text(strip=True):
                return True
        elif element.name == "input":
            # Check for input types that can have inner content as label
            input_type = element.get("type", "").lower()
            if input_type in ("submit", "button", "reset", "image"):
                if element.get("value", "").strip():
                    return True
            elif input_type == "image":
                # Image button needs alt text
                alt = element.get("alt")
                if alt and isinstance(alt, str) and alt.strip():
                    return True

        # If we reach here, no obvious accessibility support found
        # In a real implementation, we might check for nearby accessible alternatives
        # but that's complex and beyond scope of this basic implementation
        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        # Fallback to index-based identifier
        return f"{element.name}[index={index}]"


class Test712(RGAATest):
    test_id = "7.1.2"
    criterion_id = "7.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 7.1.2 nécessite un DOM.")

        soup = context.dom

        # Find elements that are likely script-controlled
        script_elements = self._find_script_controlled_elements(soup)

        if not script_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun composant d'interface généré ou contrôlé par script détecté.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, element in enumerate(script_elements):
            # Check 7.1.2: Component correctly restituted by assistive technologies
            # OR accessible alternative exists
            if self._is_accessibly_restituted(element, soup):
                compliant_count += 1
                continue

            # No accessible restitution found
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "Le composant d'interface généré ou contrôlé par script n'est pas "
                        "correctement restitué par les technologies d'assistance, "
                        "et aucune alternative accessible ne permet d'accéder aux mêmes fonctionnalités."
                    ),
                    recommendation=(
                        "Assurer que le composant possède un rôle ARIA approprié et un nom accessible, "
                        "ou fournir une alternative accessible permettant d'accéder aux mêmes fonctionnalités."
                    ),
                )
            )

        # Determine status based on findings
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(script_elements)} composant(s) d'interface généré(s) ou contrôlé(s) par script : "
                f"{compliant_count} restitué(s) correctement, {len(findings)} non restitué(s)."
            ),
            findings=findings,
            tested_elements=len(script_elements),
            metadata={
                "script_controlled_elements": len(script_elements),
                "correctly_restituted": compliant_count,
                "not_restituted": len(findings),
            },
        )

    def _find_script_controlled_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find elements likely to be generated or controlled by scripts."""
        script_elements: set[Tag] = set()

        # Common event handler attributes
        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus"
        }

        # Find elements with event handlers
        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        # Find elements with role attribute (custom widgets)
        role_elements = soup.find_all(attrs={"role": True})
        script_elements.update(role_elements)

        return list(script_elements)

    def _is_accessibly_restituted(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if element is correctly restituted by assistive technologies
        OR if an accessible alternative exists.
        """
        # For now, we use the same check as in Test711
        # In a more complete implementation, we would check:
        # - Proper ARIA roles and properties
        # - Keyboard accessibility
        # - Visible focus indicator
        # But for this basic implementation, we check for basic accessibility support
        return self._has_basic_accessibility(element, soup)

    def _has_basic_accessibility(self, element: Tag, soup: BeautifulSoup) -> bool:
        """Check for basic accessibility support."""
        # Check if element has a role attribute
        role = element.get("role")
        if role and isinstance(role, str) and role.strip():
            return True

        # Check for accessible name (aria-label or aria-labelledby)
        aria_label = element.get("aria-label")
        if aria_label and isinstance(aria_label, str) and aria_label.strip():
            return True

        aria_labelledby = element.get("aria-labelledby")
        if aria_labelledby and isinstance(aria_labelledby, str) and aria_labelledby.strip():
            labelled_element = soup.find(id=aria_labelledby)
            if labelled_element and labelled_element.get_text(strip=True):
                return True

        # Check for native accessibility
        if element.name in ("button", "a", "textarea"):
            if element.get_text(strip=True):
                return True
        elif element.name == "input":
            input_type = element.get("type", "").lower()
            if input_type in ("submit", "button", "reset", "image"):
                if element.get("value", "").strip():
                    return True
            elif input_type == "image":
                alt = element.get("alt")
                if alt and isinstance(alt, str) and alt.strip():
                    return True

        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"


class Test713(RGAATest):
    test_id = "7.1.3"
    criterion_id = "7.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 7.1.3 nécessite un DOM.")

        soup = context.dom

        # Find elements that are likely script-controlled
        script_elements = self._find_script_controlled_elements(soup)

        if not script_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun composant d'interface généré ou contrôlé par script détecté.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, element in enumerate(script_elements):
            # Check 7.1.3: Component has relevant name and role
            if self._has_relevant_name_and_role(element, soup):
                compliant_count += 1
                continue

            # Name or role not relevant
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "Le composant d'interface généré ou contrôlé par script ne possède "
                        "pas de nom pertinent (contenant au moins l'intitulé visible) "
                        "ou pas de rôle pertinent."
                    ),
                    recommendation=(
                        "S'assurer que le composant possède un rôle ARIA approprié décrivant sa fonction, "
                        "et un nom accessible contenant au moins l'intitulé visible du composant."
                    ),
                )
            )

        # Determine status based on findings
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(script_elements)} composant(s) d'interface généré(s) ou contrôlé(s) par script : "
                f"{compliant_count} avec nom et rôle pertinent(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(script_elements),
            metadata={
                "script_controlled_elements": len(script_elements),
                "relevant_name_role": compliant_count,
                "irrelevant_name_role": len(findings),
            },
        )

    def _find_script_controlled_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find elements likely to be generated or controlled by scripts."""
        script_elements: set[Tag] = set()

        # Common event handler attributes
        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus"
        }

        # Find elements with event handlers
        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        # Find elements with role attribute (custom widgets)
        role_elements = soup.find_all(attrs={"role": True})
        script_elements.update(role_elements)

        return list(script_elements)

    def _has_relevant_name_and_role(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if element has:
        - A relevant role
        - An accessible name that contains at least the visible label
        """
        # Check role relevance
        role = element.get("role")
        if not (role and isinstance(role, str) and role.strip()):
            # No role specified - check if it's a native interactive element
            if element.name not in ("button", "a", "input", "select", "textarea"):
                # Not a native interactive element and no role - likely not relevant
                return False
            # For native interactive elements, we'll check the name below

        # Check accessible name
        accessible_name = self._get_accessible_name(element, soup)
        if not accessible_name:
            return False

        # Get visible label (what user sees)
        visible_label = self._get_visible_label(element)

        # For 7.1.3, accessible name must contain at least the visible label
        # Special cases:
        # 1. If visible label is empty (icon-only button), then accessible name just needs to be present
        # 2. If visible label is a symbol (single non-alphanumeric character),
        #    the accessible name should express the function, not contain the symbol literally
        if visible_label:
            # Check if visible label is a symbol (single non-alphanumeric character)
            if len(visible_label) == 1 and not visible_label.isalnum():
                # For symbols, we don't require the accessible name to contain the symbol
                # The accessible name should express the function (already validated by being present)
                pass
            else:
                # For text labels, accessible name must contain the visible label
                if visible_label.lower() not in accessible_name.lower():
                    return False

        return True

    def _get_accessible_name(self, element: Tag, soup: BeautifulSoup) -> str | None:
        """Get the accessible name of an element."""
        # aria-label takes precedence
        aria_label = element.get("aria-label")
        if aria_label and isinstance(aria_label, str) and aria_label.strip():
            return aria_label.strip()

        # aria-labelledby
        aria_labelledby = element.get("aria-labelledby")
        if aria_labelledby and isinstance(aria_labelledby, str) and aria_labelledby.strip():
            labelled_element = soup.find(id=aria_labelledby)
            if labelled_element:
                label_text = labelled_element.get_text(strip=True)
                if label_text:
                    return label_text

        # For certain elements, use inner text or value/alt
        if element.name in ("button", "a"):
            text = element.get_text(strip=True)
            if text:
                return text
        elif element.name == "textarea":
            text = element.get_text(strip=True)
            if text:
                return text
        elif element.name == "input":
            input_type = element.get("type", "").lower()
            if input_type in ("submit", "button", "reset"):
                value = element.get("value")
                if value and isinstance(value, str) and value.strip():
                    return value.strip()
            elif input_type == "image":
                alt = element.get("alt")
                if alt and isinstance(alt, str) and alt.strip():
                    return alt.strip()

        return None

    def _get_visible_label(self, element: Tag) -> str:
        """Get the visible label of an element (what the user sees)."""
        # For most elements, visible label is the inner text
        if element.name in ("button", "a", "span", "div", "label"):
            text = element.get_text(strip=True)
            if text:
                return text

        # For form elements with associated label, we could check for label element
        # but that's complex - for simplicity, we'll rely on inner text above
        # and aria-label/aria-labelledby for accessible name

        # If no inner text, there might be no visible label (e.g., icon-only button)
        return ""

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"
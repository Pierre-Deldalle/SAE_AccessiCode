from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from typing import Any, Set, List

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test731(RGAATest):
    test_id = "7.3.1"
    criterion_id = "7.3"

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
            raise ValueError("Le test 7.3.1 nécessite un DOM.")

        soup = context.dom

        # Find elements with script event handlers
        script_elements = self._find_script_controlled_elements(soup)

        if not script_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun élément avec gestionnaire d'événement script détecté.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, element in enumerate(script_elements):
            # Check 7.3.1: Element is keyboard accessible OR has accessible equivalent
            if self._is_keyboard_accessible_or_has_equivalent(element, soup):
                compliant_count += 1
                continue

            # Not keyboard accessible and no accessible equivalent
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "L'élément possédant un gestionnaire d'événement script n'est pas "
                        "accessible au clavier et aucun élément accessible permettant de "
                        "réaliser la même action n'est présent dans la page."
                    ),
                    recommendation=(
                        "Rendre l'élément accessible au clavier (via tabindex, gestionnaires "
                        "d'événement clavier appropriés) ou fournir un élément accessible "
                        "permettant d'accéder aux mêmes fonctionnalités."
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
                f"{len(script_elements)} élément(s) avec gestionnaire d'événement script : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(script_elements),
            metadata={
                "script_controlled_elements": len(script_elements),
                "keyboard_accessible_or_equivalent": compliant_count,
                "not_keyboard_accessible_no_equivalent": len(findings),
            },
        )

    def _find_script_controlled_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find elements with script event handlers."""
        script_elements: set[Tag] = set()

        # Common event handler attributes
        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus",
            "ontouchstart", "ontouchend", "ontouchmove", "ontouchcancel",
            "onpointerdown", "onpointerup", "onpointerover", "onpointerout",
            "onpointermove", "onpointerenter", "onpointerleave", "ongotpointercapture",
            "onlostpointercapture"
        }

        # Find elements with event handlers
        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        return list(script_elements)

    def _is_keyboard_accessible_or_has_equivalent(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if element is keyboard accessible per 7.3.1:
        - Is reachable by tab
        - If simple action, activable by Enter
        - If complex action, usable with arrow keys
        - OR an accessible element providing same functionality exists in the page
        """
        # Check if element is focusable and keyboard operable
        if self._is_element_keyboard_accessible(element):
            return True

        # Check if there's an accessible equivalent in the page
        if self._has_accessible_equivalent(element, soup):
            return True

        return False

    def _is_element_keyboard_accessible(self, element: Tag) -> bool:
        """
        Check if element is keyboard accessible:
        - Can receive focus (is not disabled, not hidden, etc.)
        - For simple actions: activable with Enter
        - For complex actions: usable with arrow keys
        """
        # Check if element is focusable
        if not self._can_receive_focus(element):
            return False

        # Get the element's role or type to determine action complexity
        role = element.get("role")
        tag_name = element.name.lower() if element.name else ""
        input_type = element.get("type", "").lower() if element.name == "input" else ""

        # Determine if this is a simple or complex action
        is_simple_action = self._is_simple_action(element, role, tag_name, input_type)

        if is_simple_action:
            # Simple action: should be activable with Enter
            return self._can_be_activated_with_enter(element)
        else:
            # Complex action: should be usable with arrow keys
            return self._is_usable_with_arrow_keys(element)

    def _can_receive_focus(self, element: Tag) -> bool:
        """Check if element can receive focus."""
        # Check if explicitly not focusable
        if element.get("tabindex") == "-1":
            return False

        # Check if disabled
        if element.get("disabled") is not None:
            return False

        # Check if hidden (aria-hidden="true" or CSS display:none/visibility:hidden)
        # For simplicity, we'll check aria-hidden
        if element.get("aria-hidden") == "true":
            return False

        # Certain elements are naturally focusable
        tag_name = element.name.lower() if element.name else ""
        naturally_focusable = {"a", "button", "input", "select", "textarea", "iframe"}
        if tag_name in naturally_focusable:
            return True

        # Elements with tabindex >= 0 are focusable
        tabindex = element.get("tabindex")
        if tabindex is not None:
            try:
                tabindex_val = int(tabindex)
                return tabindex_val >= 0
            except ValueError:
                pass

        # Elements with role that makes them focusable
        role = element.get("role")
        focusable_roles = {
            "button", "link", "checkbox", "radio", "textbox", "combobox", "listbox",
            "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar",
            "scrollbar", "slider", "spinbutton", "switch", "tab", "textbox", "treeitem"
        }
        if role and role in focusable_roles:
            return True

        # By default, most elements are not focusable unless specified
        return False

    def _is_simple_action(self, element: Tag, role: str | None, tag_name: str, input_type: str) -> bool:
        """Determine if the element's action is simple (activable with Enter) or complex (needs arrow keys)."""
        # Simple actions: buttons, links, checkboxes, radio buttons
        simple_tags = {"a", "button", "input"}
        simple_input_types = {"submit", "button", "reset", "checkbox", "radio", "image"}
        simple_roles = {"button", "link", "checkbox", "radio", "menuitem", "menuitemcheckbox", "menuitemradio"}

        if tag_name in simple_tags:
            if tag_name == "input":
                return input_type in simple_input_types
            return True

        if role in simple_roles:
            return True

        # Most other interactive elements are complex actions
        return False

    def _can_be_activated_with_enter(self, element: Tag) -> bool:
        """Check if element can be activated with Enter key."""
        # Most standard HTML controls activate with Enter by default
        tag_name = element.name.lower() if element.name else ""
        input_type = element.get("type", "").lower() if element.name == "input" else ""

        if tag_name in {"a", "button", "input"}:
            if tag_name == "input":
                # Most input types activate with Enter except text-like inputs
                non_activating_types = {"text", "password", "search", "email", "tel", "url"}
                return input_type not in non_activating_types
            return True

        # For custom elements with role, they should support Enter if they're activable
        role = element.get("role")
        activable_roles = {
            "button", "link", "checkbox", "radio", "menuitem", "menuitemcheckbox",
            "menuitemradio", "switch"
        }
        if role in activable_roles:
            return True

        # Check for keyboard event handlers that might handle Enter
        # This is a simplification - in reality we'd need to check JS
        keyboard_handlers = {"onkeydown", "onkeyup", "onkeypress"}
        for handler in keyboard_handlers:
            if element.get(handler):
                return True  # Assume it might handle Enter

        return False

    def _is_usable_with_arrow_keys(self, element: Tag) -> bool:
        """Check if element is usable with arrow keys (for complex actions)."""
        # Complex actions that should work with arrow keys:
        # - Menus, menubars, tablists, treegrids, grids, listboxes
        role = element.get("role")
        arrow_key_roles = {
            "menu", "menubar", "menuitem", "tablist", "tab", "treegrid", "grid",
            "listbox", "combobox", "slider", "spinbutton", "scrollbar"
        }
        if role in arrow_key_roles:
            return True

        # Check for keyboard event handlers that might handle arrow keys
        keyboard_handlers = {"onkeydown", "onkeyup", "onkeypress"}
        for handler in keyboard_handlers:
            if element.get(handler):
                return True  # Assume it might handle arrow keys

        return False

    def _has_accessible_equivalent(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if there's an accessible element in the page that provides the same functionality.
        This is a simplified check - in reality we'd need to understand what the script does.
        """
        # For now, we'll look for elements with similar purpose/functionality
        # This is complex to implement fully, so we'll use heuristics

        tag_name = element.name.lower() if element.name else ""
        # Get potential alternatives based on element characteristics
        role = element.get("role")
        aria_label = element.get("aria-label")
        aria_labelledby = element.get("aria-labelledby")
        title = element.get("title")
        role = element.get("role")
        aria_label = element.get("aria-label")
        aria_labelledby = element.get("aria-labelledby")
        title = element.get("title")

        # Collect text content and attributes that might help identify equivalent
        element_text = element.get_text(strip=True)
        element_id = element.get("id")
        element_class = element.get("class")

        # Look for similar elements in the document
        # This is a simplified approach - real implementation would need deeper analysis
        all_elements = soup.find_all()

        for other in all_elements:
            # Skip the same element
            if other is element:
                continue

            # Check if other element is accessible (not disabled, focusable, etc.)
            if not self._can_receive_focus(other):
                continue

            # Check if other element has similar characteristics
            other_tag = other.name.lower() if other.name else ""
            other_role = other.get("role")
            other_text = other.get_text(strip=True)

            # Simple similarity check - in reality would be more sophisticated
            similarity_score = 0

            # Tag match
            if tag_name == other_tag:
                similarity_score += 1

            # Role match
            if role and role == other_role:
                similarity_score += 2

            # Text similarity (simple)
            if element_text and other_text:
                if element_text.lower() == other_text.lower():
                    similarity_score += 2
                elif element_text.lower() in other_text.lower() or other_text.lower() in element_text.lower():
                    similarity_score += 1

            # If we found a reasonably similar accessible element, consider it an equivalent
            if similarity_score >= 2:
                # Additional check: make sure the equivalent is actually accessible
                if self._is_element_keyboard_accessible(other):
                    return True

        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"


class Test732(RGAATest):
    test_id = "7.3.2"
    criterion_id = "7.3"

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
            raise ValueError("Le test 7.3.2 nécessite un DOM.")

        soup = context.dom

        # Find all focusable elements
        focusable_elements = self._find_focusable_elements(soup)

        if not focusable_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun élément focusable détecté.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, element in enumerate(focusable_elements):
            # Check 7.3.2: Script does not remove focus from element that receives it
            if self._does_not_remove_focus(element, soup):
                compliant_count += 1
                continue

            # Script removes or might remove focus
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "Un script supprime le focus d'un élément qui le reçoit, "
                        "ce qui peut désorienter les utilisateurs utilisant le clavier "
                        "ou des technologies d'assistance."
                    ),
                    recommendation=(
                        "Supprimer toute logique qui enlève le focus d'un élément lorsque "
                        "celui-ci le reçoit, sauf si cela est absolument nécessaire "
                        "et qu'un mécanisme de retour de focus approprié est fourni."
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
                f"{len(focusable_elements)} élément(s) focusable : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(focusable_elements),
            metadata={
                "focusable_elements": len(focusable_elements),
                "does_not_remove_focus": compliant_count,
                "removes_focus": len(findings),
            },
        )

    def _find_focusable_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find all elements that can receive focus."""
        focusable: set[Tag] = set()

        # Naturally focusable elements
        naturally_focusable = soup.find_all(["a", "button", "input", "select", "textarea", "iframe"])
        focusable.update(naturally_focusable)

        # Elements with tabindex >= 0 or tabindex="0"
        tabindex_elements = soup.find_all(attrs={"tabindex": True})
        for elem in tabindex_elements:
            tabindex = elem.get("tabindex")
            if tabindex is not None:
                try:
                    # tabindex="-1" means not focusable, but reachable via script
                    # tabindex="0" means focusable
                    # positive tabindex means focusable with tab order
                    tabindex_val = int(tabindex)
                    if tabindex_val >= -1:  # -1 or greater can receive focus via script
                        focusable.add(elem)
                except ValueError:
                    pass

        # Elements with ARIA roles that make them focusable
        focusable_roles = {
            "button", "link", "checkbox", "radio", "textbox", "combobox", "listbox",
            "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar",
            "scrollbar", "slider", "spinbutton", "switch", "tab", "textbox", "treeitem"
        }
        for role in focusable_roles:
            role_elements = soup.find_all(attrs={"role": role})
            focusable.update(role_elements)

        return list(focusable)

    def _does_not_remove_focus(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if there's no script that removes focus from this element when it receives focus.
        This is a heuristic check - we look for patterns that might indicate focus removal.
        """
        # Check for explicit focus removal in inline event handlers
        blur_handlers = ["onblur", "onfocusout"]
        for handler in blur_handlers:
            handler_value = element.get(handler)
            if handler_value and isinstance(handler_value, str):
                # Look for patterns that might indicate focus removal
                focus_removal_patterns = [
                    "blur()", "focusout()",
                    "document.activeElement.blur()",
                    "$(document.activeElement).blur()",
                    "element.blur()",
                    "this.blur()",
                    "setTimeout.*blur",
                    "requestAnimationFrame.*blur"
                ]
                for pattern in focus_removal_patterns:
                    if pattern in handler_value.lower():
                        return False  # Found potential focus removal

        # Check for focus removal in nearby scripts (simplified)
        # In a real implementation, we'd need to analyze JavaScript more thoroughly
        # For now, we'll check for common patterns in script tags near the element

        # Look for script tags that might contain focus removal logic
        scripts = soup.find_all("script")
        for script in scripts:
            script_content = ""
            if script.string:
                script_content = script.string
            elif script.get("src"):
                # For external scripts, we can't check content easily
                # In a real implementation, we'd fetch and analyze
                continue

            # Check for focus removal patterns in script content
            focus_removal_patterns = [
                r"\.blur\s*\(",
                r"\.focusout\s*\(",
                r"activeElement\s*\.\s*blur\s*\(",
                r"setTimeout\s*\([^)]*blur",
                r"requestAnimationFrame\s*\([^)]*blur"
            ]

            import re
            for pattern in focus_removal_patterns:
                if re.search(pattern, script_content, re.IGNORECASE):
                    # Check if this script might be associated with our element
                    # This is very simplified - real implementation would need scope analysis
                    if self._might_be_associated_with_element(script, element):
                        return False

        return True

    def _might_be_associated_with_element(self, script: Tag, element: Tag) -> bool:
        """Check if a script might be associated with a specific element (simplified)."""
        # Check if script is in the same parent container
        if script.parent == element.parent:
            return True

        # Check if script is near the element in the DOM
        # Find positions in parent's children
        if element.parent:
            parent_children = list(element.parent.children)
            try:
                element_index = parent_children.index(element)
                script_index = parent_children.index(script)
                # If they're close in the DOM, they might be related
                if abs(element_index - script_index) <= 5:
                    return True
            except ValueError:
                pass

        # Check if element has an ID that might be referenced in the script
        element_id = element.get("id")
        if element_id and isinstance(element_id, str) and element_id.strip():
            script_content = ""
            if script.string:
                script_content = script.string
            if element_id in script_content:
                return True

        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"
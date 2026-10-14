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
            if self._is_keyboard_accessible_or_has_equivalent(element, soup):
                compliant_count += 1
                continue

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
        script_elements: set[Tag] = set()

        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus",
            "ontouchstart", "ontouchend", "ontouchmove", "ontouchcancel",
            "onpointerdown", "onpointerup", "onpointerover", "onpointerout",
            "onpointermove", "onpointerenter", "onpointerleave", "ongotpointercapture",
            "onlostpointercapture"
        }

        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        return list(script_elements)

    def _is_keyboard_accessible_or_has_equivalent(self, element: Tag, soup: BeautifulSoup) -> bool:
        if self._is_element_keyboard_accessible(element):
            return True

        if self._has_accessible_equivalent(element, soup):
            return True

        return False

    def _is_element_keyboard_accessible(self, element: Tag) -> bool:
        if not self._can_receive_focus(element):
            return False

        role = element.get("role")
        tag_name = element.name.lower() if element.name else ""
        input_type = element.get("type", "").lower() if element.name == "input" else ""

        is_simple_action = self._is_simple_action(element, role, tag_name, input_type)

        if is_simple_action:
            return self._can_be_activated_with_enter(element)
        else:
            return self._is_usable_with_arrow_keys(element)

    def _can_receive_focus(self, element: Tag) -> bool:
        if element.get("tabindex") == "-1":
            return False

        if element.get("disabled") is not None:
            return False

        if element.get("aria-hidden") == "true":
            return False

        tag_name = element.name.lower() if element.name else ""
        naturally_focusable = {"a", "button", "input", "select", "textarea", "iframe"}
        if tag_name in naturally_focusable:
            return True

        tabindex = element.get("tabindex")
        if tabindex is not None:
            try:
                tabindex_val = int(tabindex)
                return tabindex_val >= 0
            except ValueError:
                pass

        role = element.get("role")
        focusable_roles = {
            "button", "link", "checkbox", "radio", "textbox", "combobox", "listbox",
            "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar",
            "scrollbar", "slider", "spinbutton", "switch", "tab", "textbox", "treeitem"
        }
        if role and role in focusable_roles:
            return True

        return False

    def _is_simple_action(self, element: Tag, role: str | None, tag_name: str, input_type: str) -> bool:
        simple_tags = {"a", "button", "input"}
        simple_input_types = {"submit", "button", "reset", "checkbox", "radio", "image"}
        simple_roles = {"button", "link", "checkbox", "radio", "menuitem", "menuitemcheckbox", "menuitemradio"}

        if tag_name in simple_tags:
            if tag_name == "input":
                return input_type in simple_input_types
            return True

        if role in simple_roles:
            return True

        return False

    def _can_be_activated_with_enter(self, element: Tag) -> bool:
        tag_name = element.name.lower() if element.name else ""
        input_type = element.get("type", "").lower() if element.name == "input" else ""

        if tag_name in {"a", "button", "input"}:
            if tag_name == "input":
                non_activating_types = {"text", "password", "search", "email", "tel", "url"}
                return input_type not in non_activating_types
            return True

        role = element.get("role")
        activable_roles = {
            "button", "link", "checkbox", "radio", "menuitem", "menuitemcheckbox",
            "menuitemradio", "switch"
        }
        if role in activable_roles:
            return True

        keyboard_handlers = {"onkeydown", "onkeyup", "onkeypress"}
        for handler in keyboard_handlers:
            if element.get(handler):
                return True

        return False

    def _is_usable_with_arrow_keys(self, element: Tag) -> bool:
        role = element.get("role")
        arrow_key_roles = {
            "menu", "menubar", "menuitem", "tablist", "tab", "treegrid", "grid",
            "listbox", "combobox", "slider", "spinbutton", "scrollbar"
        }
        if role in arrow_key_roles:
            return True

        keyboard_handlers = {"onkeydown", "onkeyup", "onkeypress"}
        for handler in keyboard_handlers:
            if element.get(handler):
                return True

        return False

    def _has_accessible_equivalent(self, element: Tag, soup: BeautifulSoup) -> bool:
        tag_name = element.name.lower() if element.name else ""
        role = element.get("role")
        aria_label = element.get("aria-label")
        aria_labelledby = element.get("aria-labelledby")
        title = element.get("title")

        element_text = element.get_text(strip=True)
        element_id = element.get("id")
        element_class = element.get("class")

        all_elements = soup.find_all()

        for other in all_elements:
            if other is element:
                continue

            if not self._can_receive_focus(other):
                continue

            other_tag = other.name.lower() if other.name else ""
            other_role = other.get("role")
            other_text = other.get_text(strip=True)

            similarity_score = 0

            if tag_name == other_tag:
                similarity_score += 1

            if role and role == other_role:
                similarity_score += 2

            if element_text and other_text:
                if element_text.lower() == other_text.lower():
                    similarity_score += 2
                elif element_text.lower() in other_text.lower() or other_text.lower() in element_text.lower():
                    similarity_score += 1

            if similarity_score >= 2:
                if self._is_element_keyboard_accessible(other):
                    return True

        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
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
            if self._does_not_remove_focus(element, soup):
                compliant_count += 1
                continue

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
        focusable: set[Tag] = set()

        naturally_focusable = soup.find_all(["a", "button", "input", "select", "textarea", "iframe"])
        focusable.update(naturally_focusable)

        tabindex_elements = soup.find_all(attrs={"tabindex": True})
        for elem in tabindex_elements:
            tabindex = elem.get("tabindex")
            if tabindex is not None:
                try:
                    tabindex_val = int(tabindex)
                    if tabindex_val >= -1:
                        focusable.add(elem)
                except ValueError:
                    pass

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
        blur_handlers = ["onblur", "onfocusout"]
        for handler in blur_handlers:
            handler_value = element.get(handler)
            if handler_value and isinstance(handler_value, str):
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
                        return False

        scripts = soup.find_all("script")
        for script in scripts:
            script_content = ""
            if script.string:
                script_content = script.string
            elif script.get("src"):
                continue

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
                    if self._might_be_associated_with_element(script, element):
                        return False

        return True

    def _might_be_associated_with_element(self, script: Tag, element: Tag) -> bool:
        if script.parent == element.parent:
            return True

        if element.parent:
            parent_children = list(element.parent.children)
            try:
                element_index = parent_children.index(element)
                script_index = parent_children.index(script)
                if abs(element_index - script_index) <= 5:
                    return True
            except ValueError:
                pass

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
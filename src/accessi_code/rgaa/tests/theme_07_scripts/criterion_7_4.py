from __future__ import annotations

import re
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


class Test741(RGAATest):
    test_id = "7.4.1"
    criterion_id = "7.4"

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
            raise ValueError("Le test 7.4.1 nécessite un DOM.")

        soup = context.dom

        # Find elements that are likely script-controlled:
        # - Elements with event handlers (onclick, onchange, etc.)
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
            # Check 7.4.1: Either explicit button/link OR warning text present
            if self._is_explicit_button_or_link(element) or self._has_warning_text(element, soup):
                compliant_count += 1
                continue

            # Neither explicit button/link nor warning text found
            findings.append(
                Finding(
                    element=self._get_element_identifier(element, index),
                    message=(
                        "Le script d'ouverture n'avertit pas l'utilisateur de l'ouverture d'une nouvelle "
                        "fenêtre et n'est pas initié par un bouton ou un lien explicite."
                    ),
                    recommendation=(
                        "Ajouter un texte d'avertissement (ex: [ouvre nouvelle fenêtre]) près du composant, "
                        "ou remplacer l'élément par un bouton ou un lien explicite."
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

        # Common event handler attributes that indicate script control
        event_handlers: Set[str] = {
            "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
            "onmousemove", "onmouseout", "onkeypress", "onkeydown", "onkeyup",
            "onchange", "onsubmit", "onreset", "onselect", "onblur", "onfocus"
        }

        # Find elements with event handlers
        for handler in event_handlers:
            elements = soup.find_all(attrs={handler: True})
            script_elements.update(elements)

        return list(script_elements)

    def _is_explicit_button_or_link(self, element: Tag) -> bool:
        """
        Check if element is an explicit button or link.
        Returns True for:
        - <button> elements
        - <input type="button|submit|image"> elements
        - <a> elements (links)
        """
        name = element.name.lower()

        if name == "button":
            return True
        elif name == "input":
            input_type = element.get("type", "").lower()
            return input_type in ("button", "submit", "image")
        elif name == "a":
            # All <a> elements are considered explicit links
            return True

        return False

    def _has_warning_text(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if element has warning text indicating it opens a new window/context.
        Warning text can be:
        1. Text enclosed in brackets: [Cliquez ici pour ouvrir une nouvelle fenêtre]
        2. Text starting with warning prefixes: "Attention : cette action..."
        3. Text containing bracketed warnings: "Page 1 [ouvre nouvel onglet]"
        4. In title attribute
        5. In aria-label attribute
        6. In nearby elements (within same parent)
        """
        # Check element's own text content
        if self._element_text_contains_warning(element.get_text()):
            return True

        # Check title attribute
        title = element.get("title")
        if title and self._element_text_contains_warning(title):
            return True

        # Check aria-label attribute
        aria_label = element.get("aria-label")
        if aria_label and self._element_text_contains_warning(aria_label):
            return True

        # Check nearby elements (siblings, parent's children)
        return self._has_nearby_warning_text(element, soup)

    def _element_text_contains_warning(self, text: str | None) -> bool:
        """Check if text contains warning indicators."""
        if not text or not isinstance(text, str):
            return False

        text = text.strip()
        if not text:
            return False

        # Check for text enclosed in brackets
        if re.search(r'\[[^\]]*\]', text):
            # Extract bracketed content and check if it contains warning indicators
            bracketed_matches = re.findall(r'\[([^\]]*)\]', text)
            for match in bracketed_matches:
                if self._contains_warning_indicators(match):
                    return True

        # Check for text starting with warning prefixes
        if self._starts_with_warning_prefix(text):
            return True

        # Check if text contains warning indicators anywhere
        return self._contains_warning_indicators(text)

    def _starts_with_warning_prefix(self, text: str) -> bool:
        """Check if text starts with common warning prefixes."""
        text_lower = text.lower().strip()
        warning_prefixes = [
            "attention :",
            "attention !",
            "attention",
            "warning :",
            "warning !",
            "warning",
            "mise en garde :",
            "mise en garde !",
            "mise en garde",
            "note :",
            "note !",
            "note",
        ]

        for prefix in warning_prefixes:
            if text_lower.startswith(prefix):
                return True
        return False

    def _contains_warning_indicators(self, text: str) -> bool:
        """Check if text contains words/phrases indicating context change."""
        text_lower = text.lower().strip()

        # Words/phrases that indicate opening new window/context
        context_change_indicators = [
            "nouvelle fenêtre",
            "nouvel onglet",
            "nouvelle page",
            "popup",
            "boîte de dialogue",
            "dialogue",
            "fenêtre modale",
            "onglet externe",
            "site externe",
            "lien externe",
            "téléchargement",
            "download",
            "ouverture",
            "ouvre",
            "ouvrir",
            "ouvrira",
            "action irréversible",
            "external",
            "new window",
            "new tab",
            "external link"
        ]

        for indicator in context_change_indicators:
            if indicator in text_lower:
                return True

        return False

    def _has_nearby_warning_text(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if there's warning text in nearby elements.
        Looks at parent element's immediate children for warning text.
        """
        parent = element.parent
        if not parent:
            return False

        # Check all children of the parent
        for child in parent.children:
            if hasattr(child, 'get_text'):  # It's a Tag
                child_text = child.get_text()
                if self._element_text_contains_warning(child_text):
                    # Make sure it's not the element itself
                    if child != element:
                        return True

        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"
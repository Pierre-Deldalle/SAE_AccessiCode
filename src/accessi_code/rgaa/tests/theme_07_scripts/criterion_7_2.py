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


class Test721(RGAATest):
    test_id = "7.2.1"
    criterion_id = "7.2"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if context.html_source is None:
            raise ValueError("Le test 7.2.1 nécessite la source HTML.")

        # Parse HTML to find script tags and their alternatives
        soup = BeautifulSoup(context.html_source, "html.parser")

        # Find all script tags
        script_tags = soup.find_all("script")

        # Find scripts that have alternatives
        scripts_with_alternatives = [
            s for s in script_tags if self._script_has_alternative(s, soup)
        ]

        if not scripts_with_alternatives:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun script avec alternative trouvé.",
            )

        findings: list[Finding] = []
        compliant_count = 0

        for index, script in enumerate(scripts_with_alternatives):
            # Check if the alternative is relevant/pertinent
            if self._is_alternative_pertinent(script, soup):
                compliant_count += 1
            else:
                findings.append(
                    Finding(
                        element=self._get_script_identifier(script, index),
                        message=(
                            "L'alternative du script ne permet pas d'accéder à des "
                            "contenus et des fonctionnalités similaires."
                        ),
                        recommendation=(
                            "Fournir une alternative permettant d'accéder aux mêmes "
                            "contenus et fonctionnalités lorsque le script n'est pas "
                            "disponible ou exécuté."
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
                f"{len(scripts_with_alternatives)} script(s) avec alternative(s) : "
                f"{compliant_count} pertinent(s), {len(findings)} non pertinent(s)."
            ),
            findings=findings,
            tested_elements=len(scripts_with_alternatives),
            metadata={
                "total_scripts": len(script_tags),
                "scripts_with_alternatives": len(scripts_with_alternatives),
                "pertinent_alternatives": compliant_count,
                "non_pertinent_alternatives": len(findings),
            },
        )

    def _script_has_alternative(self, script: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if a script has an alternative according to RGAA 7.2.1:
        - Alternative between <noscript> and </noscript>
        - Alternative page when JS is disabled
        - Server-side scripting alternative
        - Alternative present in the page
        """
        # Check for noscript element associated with or near this script
        # Look for noscript elements that could be alternatives to this script
        noscript_elements = soup.find_all("noscript")
        for noscript in noscript_elements:
            # Simple heuristic: if noscript is in the same parent or nearby,
            # it might be an alternative for this script
            if self._is_related_to_script(noscript, script):
                # Found a related noscript element - the script has an alternative
                # (we'll check if it's pertinent later)
                return True

        # Check for server-side scripting indicators (this is heuristic)
        # In a real implementation, we'd need to know what server-side tech is used
        script_src = script.get("src")
        if script_src:
            # Check if there's a non-JS version indicated
            # For example, checking for data-noscript or similar attributes
            pass

        # Check for alternative content in the page that might serve as fallback
        # This is complex and would require understanding what the script does

        # For now, we'll use a simplified approach: if there's a noscript element
        # associated with this script, we consider it as having an alternative
        # In a more complete implementation, we'd do deeper analysis

        return len([n for n in soup.find_all("noscript") if self._is_related_to_script(n, script)]) > 0

    def _is_alternative_pertinent(self, script: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if the alternative for a script is pertinent/relevant.
        This is a simplified check - in reality, we'd need to verify that
        the alternative provides similar content and functionality.
        """
        # Find the noscript alternative associated with this script
        noscript_elements = soup.find_all("noscript")
        for noscript in noscript_elements:
            if self._is_related_to_script(noscript, script):
                alternative_content = noscript.get_text(strip=True)
                if alternative_content:
                    # In a real implementation, we would compare the script's functionality
                    # with the alternative content to see if they provide similar
                    # content and functionality.
                    # For now, we'll consider any non-empty noscript content as
                    # a potentially pertinent alternative.
                    # This is a simplification but follows the pragmatic approach
                    # used in the 7.1 implementation.
                    return True

        # If we found a noscript but it was empty, or no noscript was found
        # but the script was considered to have an alternative, then it's not pertinent
        return False

    def _is_related_to_script(self, element: Tag, script: Tag) -> bool:
        """
        Check if an element (like noscript) is related to a script tag.
        This is a heuristic to associate alternatives with their scripts.
        """
        # Check if they share the same parent and the element is close to the script
        if element.parent == script.parent:
            # Get indices of both elements in their parent's children list
            script_children = list(script.parent.children)
            element_children = list(element.parent.children)

            try:
                script_index = script_children.index(script)
                element_index = element_children.index(element)

                # Consider them related if they are close siblings (within 2 positions)
                # This handles cases like:
                # <script>...</script><noscript>...</noscript>
                # or
                # <script>...</script>\n\n<noscript>...</noscript>
                if abs(script_index - element_index) <= 2:
                    return True
            except ValueError:
                # One of the elements is not in the parent's children list (unlikely but possible)
                pass

        # Check if one is directly inside the other's parent container with no intervening elements
        # This handles cases like:
        # <div>
        #   <script>...</script>
        #   <noscript>...</noscript>
        # </div>
        if script.parent and element.parent:
            # Check if script's parent contains element as a direct child
            if element.parent == script.parent:
                try:
                    script_children = list(script.parent.children)
                    element_children = list(element.parent.children)
                    script_index = script_children.index(script)
                    element_index = element_children.index(element)
                    if abs(script_index - element_index) <= 2:
                        return True
                except ValueError:
                    pass

            # Check if element's parent contains script as a direct child
            # (This is redundant with the above check but kept for clarity)
            if script.parent == element.parent:
                try:
                    script_children = list(script.parent.children)
                    element_children = list(element.parent.children)
                    script_index = script_children.index(script)
                    element_index = element_children.index(element)
                    if abs(script_index - element_index) <= 2:
                        return True
                except ValueError:
                    pass

        return False

    def _get_script_identifier(self, script: Tag, index: int) -> str:
        """Generate a unique identifier for the script element."""
        script_id = script.get("id")
        if isinstance(script_id, str) and script_id.strip():
            return f"script#{script_id}"

        script_src = script.get("src")
        if isinstance(script_src, str) and script_src.strip():
            # Truncate long src values for readability
            if len(script_src) > 50:
                src_display = script_src[:47] + "..."
            else:
                src_display = script_src
            return f"script[src='{src_display}'][index={index}]"

        return f"script[index={index}]"


class Test722(RGAATest):
    test_id = "7.2.2"
    criterion_id = "7.2"

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
            raise ValueError("Le test 7.2.2 nécessite un DOM.")

        soup = context.dom

        # Find non-textual elements updated by scripts
        # This is extremely complex to implement fully as it would require:
        # 1. Detecting which elements are updated by scripts
        # 2. Tracking changes over time
        # 3. Identifying their alternatives
        # 4. Checking if alternatives are updated accordingly

        # Given the complexity, we'll implement a simplified version that
        # looks for common patterns of script-updated non-textual elements
        # and checks if they have accessible alternatives that would need
        # to be updated in sync.

        # For now, we'll return NOT_APPLICABLE as a placeholder, indicating
        # that this test requires more sophisticated implementation
        # that would need runtime DOM change tracking.

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NOT_APPLICABLE,
            summary="Le test 7.2.2 nécessite un suivi des changements DOM en temps réel qui n'est pas encore implémenté.",
            tested_elements=0,
        )

        # The following is a skeleton of what a full implementation might look like:
        #
        # non_textual_elements = self._find_non_textual_elements_updated_by_scripts(soup)
        #
        # if not non_textual_elements:
        #     return TestResult(
        #         test_id=self.test_id,
        #         criterion_id=self.criterion_id,
        #         status=TestStatus.NOT_APPLICABLE,
        #         summary="Aucun élément non textuel mis à jour par un script détecté.",
        #     )
        #
        # findings: list[Finding] = []
        # compliant_count = 0
        #
        # for index, element in enumerate(non_textual_elements):
        #     if self._has_updated_alternative(element, soup):
        #         compliant_count += 1
        #     else:
        #         findings.append(
        #             Finding(
        #                 element=self._get_element_identifier(element, index),
        #                 message=(
        #                     "L'alternative de l'élément non textuel mis à jour par un script "
        #                     "n'est pas mise à jour lorsqu'élément est modifié."
        #                 ),
        #                 recommendation=(
        #                     "Assurer que l'alternative de l'élément non textuel est mise à jour "
        #                     "lorsque l'élément est modifié par le script."
        #                 ),
        #             )
        #         )
        #         )
        #
        # # Determine status based on findings
        # if findings:
        #     status = TestStatus.FAIL
        # else:
        #     status = TestStatus.PASS
        #
        # return TestResult(
        #     test_id=self.test_id
        #     criterion_id=self.criterion_id
        #     status=status
        #     summary=(
        #         f"{len(non_textual_elements)} élément(s) non textuel(s) mis à jour par script : "
        #         f"{compliant_count} avec alternative mise à jour, {len(findings)} sans."
        #     )
        #     findings=findings
        #     tested_elements=len(non_textual_elements)
        #     metadata={
        #         "non_textual_updated_elements": len(non_textual_elements)
        #         "elements_with_updated_alternative": compliant_count
        #         "elements_without_updated_alternative": len(findings)
        #     }
        # )

    # Placeholder methods that would be needed for a full implementation
    def _find_non_textual_elements_updated_by_scripts(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Find non-textual elements that are updated by scripts.
        This would require detecting script-induced DOM changes over time.
        """
        # This is a placeholder - full implementation would be much more complex
        return []

    def _has_updated_alternative(self, element: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if a non-textual element updated by script has an alternative
        that is also updated when the element changes.
        """
        # Placeholder
        return False

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"
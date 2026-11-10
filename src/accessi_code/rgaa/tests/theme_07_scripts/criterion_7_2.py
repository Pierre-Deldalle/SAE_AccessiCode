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

        soup = BeautifulSoup(context.html_source, "html.parser")

        script_tags = soup.find_all("script")

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
        noscript_elements = soup.find_all("noscript")
        for noscript in noscript_elements:
            if self._is_related_to_script(noscript, script):
                return True

        script_src = script.get("src")
        if script_src:
            pass

        return len([n for n in soup.find_all("noscript") if self._is_related_to_script(n, script)]) > 0

    def _is_alternative_pertinent(self, script: Tag, soup: BeautifulSoup) -> bool:
        noscript_elements = soup.find_all("noscript")
        for noscript in noscript_elements:
            if self._is_related_to_script(noscript, script):
                alternative_content = noscript.get_text(strip=True)
                if alternative_content:
                    return True

        return False

    def _is_related_to_script(self, element: Tag, script: Tag) -> bool:
        if element.parent == script.parent:
            script_children = list(script.parent.children)
            element_children = list(element.parent.children)

            try:
                script_index = script_children.index(script)
                element_index = element_children.index(element)

                if abs(script_index - element_index) <= 2:
                    return True
            except ValueError:
                pass

        if script.parent and element.parent:
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
        script_id = script.get("id")
        if isinstance(script_id, str) and script_id.strip():
            return f"script#{script_id}"

        script_src = script.get("src")
        if isinstance(script_src, str) and script_src.strip():
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

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NOT_APPLICABLE,
            summary="Le test 7.2.2 nécessite un suivi des changements DOM en temps réel qui n'est pas encore implémenté.",
            tested_elements=0,
        )

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"
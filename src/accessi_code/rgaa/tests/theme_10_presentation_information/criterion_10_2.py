from __future__ import annotations

from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test1021(RGAATest):
    test_id = "10.2.1"
    criterion_id = "10.2"

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
        """
        Test 10.2.1: Vérifie que l'information reste présente lorsque les feuilles de styles sont désactivées.
        Plus spécifiquement, vérifie que le CSS n'est pas utilisé pour générer du contenu informatif
        via les pseudo-éléments :before et :after.
        """
        if not hasattr(context, "html_source") or not context.html_source:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible.",
            )

        import re

        html_source = context.html_source
        findings = []

        # Pattern to find CSS in style tags
        style_pattern = r"<style[^>]*>(.*?)</style>"
        style_matches = re.findall(style_pattern, html_source, re.DOTALL | re.IGNORECASE)

        # Also check for inline styles
        inline_style_pattern = r'style=["\']([^"\']*)["\']'
        inline_style_matches = re.findall(inline_style_pattern, html_source, re.IGNORECASE)

        all_css_content = []

        # Extract content from style tags
        for style_content in style_matches:
            all_css_content.append(style_content)

        # Extract content from inline styles
        for inline_style in inline_style_matches:
            all_css_content.append(inline_style)

        # Check each CSS block for :before/:after with content property that might convey information
        for css_index, css_content in enumerate(all_css_content):
            # Look for :before and :after selectors
            pseudo_element_pattern = r":[:\s]*(before|after)[^{]*{([^}]*)}"
            pseudo_matches = re.findall(pseudo_element_pattern, css_content, re.IGNORECASE | re.DOTALL)

            for pseudo_type, pseudo_content in pseudo_matches:
                # Check if the pseudo-element has a content property
                content_pattern = r"content\s*:\s*[^;]+;"
                content_matches = re.findall(content_pattern, pseudo_content, re.IGNORECASE)

                for content_match in content_matches:
                    # Extract the content value
                    content_value_match = re.search(r"content\s*:\s*([^;]+);", content_match, re.IGNORECASE)
                    if content_value_match:
                        content_value = content_value_match.group(1).strip()

                        # Check if the content is not just decorative (empty, quotes, or URI for decorative images)
                        # We consider it informative if it contains text that's not just whitespace
                        # and is not a URI that likely points to a decorative image
                        is_likely_decorative = (
                            content_value in ('""', "''", '""', "''")  # Empty quotes
                            or content_value.startswith("url(")
                            and any(
                                ext in content_value.lower()
                                for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]
                                and not any(
                                    word in content_value.lower() for word in ["icon", "logo", "bullet", "decoration"]
                                )
                            )
                        )

                        # If it's not clearly decorative, flag it for review
                        if not is_likely_decorative and len(content_value) > 2:
                            # Try to determine which element this applies to
                            # This is complex without full CSS parsing, so we'll note it generally
                            findings.append(
                                Finding(
                                    element=f"CSS block {css_index + 1}",
                                    message=f"Le pseudo-element :{pseudo_type} utilise la propriété 'content' avec une valeur qui pourrait transmettre de l'information : '{content_value[:50]}...'.",
                                    recommendation=(
                                        "Vérifier que l'information transmise par ce pseudo-element est également disponible sans CSS, ou utiliser du contenu HTML à la place."
                                    ),
                                    evidence={
                                        "pseudo_element": f":{pseudo_type}",
                                        "content_value": content_value,
                                        "css_source": css_content[:200],  # Limit length
                                    },
                                )
                            )

        # Also check for background-image usage that might convey information
        # Look for background-image properties in CSS
        background_pattern = r"background-image\s*:\s*[^;]+;"
        background_matches = re.findall(background_pattern, html_source, re.IGNORECASE)

        informative_bg_keywords = [
            "chart",
            "graph",
            "diagram",
            "icon",
            "logo",
            "symbol",
            "warning",
            "alert",
            "error",
            "success",
            "info",
            "data",
            "map",
            "illustration",
        ]

        for bg_match in background_matches:
            # Extract the URL value
            url_match = re.search(r"background-image\s*:\s*url\(([^)]+)\)", bg_match, re.IGNORECASE)
            if url_match:
                url_value = url_match.group(1).strip()
                # Remove quotes if present
                if url_value.startswith('"') and url_value.endswith('"'):
                    url_value = url_value[1:-1]
                elif url_value.startswith("'") and url_value.endswith("'"):
                    url_value = url_value[1:-1]

                # Check if this looks like it could be informative content
                url_lower = url_value.lower()
                is_potentially_informative = any(
                    keyword in url_lower for keyword in informative_bg_keywords
                ) and not any(
                    decorative in url_lower for decorative in ["bullet", "icon-decoration", "divider", "separator"]
                )

                if is_potentially_informative:
                    findings.append(
                        Finding(
                            element="CSS background-image",
                            message=f"Une image d'arrière-plan potentiellement informative est utilisée : '{url_value}'.",
                            recommendation=(
                                "Vérifier que l'information transmise par cette image est également disponible sans CSS, ou utiliser un élément <img> avec un attribut alt approprié."
                            ),
                            evidence={
                                "background_image_url": url_value,
                                "css_source": bg_match[:200],
                            },
                        )
                    )

        if not findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun usage détecté de CSS pour transmettre de l'information essentiel.",
                tested_elements=0,
            )

        # If we found potential issues, we need to determine the status
        # Based on RGAA principles, if CSS is used to convey essential information, it's a failure
        # However, without being able to definitively determine if the information is essential,
        # we'll flag it as NEEDS_REVIEW for manual verification
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=f"{len(findings)} instance(s) détectée(s) où CSS pourrait être utilisé pour transmettre de l'information.",
            findings=findings,
            tested_elements=len(findings),
            metadata={
                "potential_css_issues": len(findings),
                "pseudo_element_issues": len(
                    [
                        f
                        for f in findings
                        if "pseudo-element" in f.element or ":before" in f.message or ":after" in f.message
                    ]
                ),
                "background_image_issues": len([f for f in findings if "background-image" in f.element]),
            },
        )

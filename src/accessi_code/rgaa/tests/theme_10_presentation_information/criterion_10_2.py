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
                            or content_value.startswith("url(") and any(
                                ext in content_value.lower()
                                for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]
                                and not any(
                                    word in content_value.lower()
                                    for word in ["icon", "logo", "bullet", "decoration"]
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
                                    recommendation=("Vérifier que l'information transmise par ce pseudo-element est également disponible sans CSS, ou utiliser du contenu HTML à la place."),
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
            "chart", "graph", "diagram", "icon", "logo", "symbol", "warning", "alert",
            "error", "success", "info", "data", "map", "illustration"
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
                            recommendation=("Vérifier que l'information transmise par cette image est également disponible sans CSS, ou utiliser un élément <img> avec un attribut alt approprié."),
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
                "pseudo_element_issues": len([f for f in findings if "pseudo-element" in f.element or ":before" in f.message or ":after" in f.message]),
                "background_image_issues": len([f for f in findings if "background-image" in f.element]),
            },
        )


class Test1022(RGAATest):
    test_id = "10.2.2"
    criterion_id = "10.2"

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
        """
        Test 10.2.2: Vérifie que les relations et la structure de l'information sont préservées
        lorsque les feuilles de styles sont désactivées.
        Cela inclut la vérification que les titres, listes, tableaux, etc. sont correctement structurés
        dans le HTML indépendamment de leur présentation visuelle.
        """
        if not isinstance(
            context.dom,
            __import__("bs4").BeautifulSoup,
        ):
            raise ValueError("Le test 10.2.2 nécessite un DOM.")

        soup = context.dom
        findings = []

        # Check for heading structure - headings should be used hierarchically, not just for visual styling
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        heading_tags = [h.name for h in headings]

        # Check if we have heading tags that are used out of order (might indicate visual styling only)
        if heading_tags:
            # Convert to numbers for easier checking
            heading_levels = []
            for tag in heading_tags:
                try:
                    level = int(tag[1])  # Get the number from h1, h2, etc.
                    heading_levels.append(level)
                except (ValueError, IndexError):
                    pass

            # Check for skipped levels (e.g., h1 followed by h3 without h2)
            # This might indicate headings are used for visual styling only
            for i in range(1, len(heading_levels)):
                if heading_levels[i] > heading_levels[i-1] + 1:
                    findings.append(
                        Finding(
                            element=f"heading {headings[i].name}",
                            message=f"Niveau de titre sauté : {headings[i-1].name} suivi de {headings[i].name}. Cela pourrait indiquer une utilisation des titres uniquement pour la présentation visuelle.",
                            recommendation=("Utiliser une hiérarchie de titres cohérente qui reflète la structure du contenu, indépendamment de la présentation visuelle."),
                            evidence={
                                "previous_heading": headings[i-1].name,
                                "current_heading": headings[i].name,
                                "heading_text": headings[i].get_text().strip()[:100],
                            },
                        )
                    )

        # Check for lists - ensure they're used for actual lists, not just indentation
        # This is harder to determine automatically, but we can check for common patterns
        lists = soup.find_all(["ul", "ol", "dl"])
        for lst in lists:
            # Check if list items have meaningful content
            items = lst.find_all(["li", "dt", "dd"])
            if items:
                # Check if all items are empty or contain only whitespace/non-informative content
                empty_items = 0
                for item in items:
                    text = item.get_text().strip()
                    if not text or len(text) < 2:  # Arbitrary threshold
                        empty_items += 1

                # If most items are empty, the list might be used for visual spacing only
                if len(items) > 0 and (empty_items / len(items)) > 0.7:
                    findings.append(
                        Finding(
                            element=f"{lst.name}[index={len(findings)}]",
                            message=f"La liste {lst.name} contient principalement des éléments vides ou quasi-vides, ce qui pourrait indiquer une utilisation pour l'espacement visuel plutôt que pour structurer de l'information.",
                            recommendation=("Utiliser des listes uniquement pour regrouper des éléments liés sémantiquement, et utiliser CSS pour l'espacement si nécessaire."),
                            evidence={
                                "list_type": lst.name,
                                "total_items": len(items),
                                "empty_items": empty_items,
                            },
                        )
                    )

        # Check for tables used for layout rather than data
        tables = soup.find_all("table")
        for table in tables:
            # Simple heuristic: if a table has no<th> elements and very little text content,
            # it might be used for layout
            th_elements = table.find_all("th")
            td_elements = table.find_all("td")
            all_cells = th_elements + td_elements

            if all_cells:
                # Count cells with meaningful content
                meaningful_cells = 0
                for cell in all_cells:
                    text = cell.get_text().strip()
                    # Consider it meaningful if it has more than just a few characters
                    # and isn't just whitespace or common spacer characters
                    if text and len(text) > 1 and not all(c in " \t\n\r.-_" for c in text):
                        meaningful_cells += 1

                # If very few cells have meaningful content, it might be a layout table
                if len(all_cells) > 0 and (meaningful_cells / len(all_cells)) < 0.3:
                    findings.append(
                        Finding(
                            element=f"table[index={len(findings)}]",
                            message=f"Le tableau contient principalement des cellules vides ou quasi-vides ({meaningful_cells}/{len(all_cells)} avec contenu significatif), ce qui pourrait indiquer une utilisation pour la mise en page plutôt que pour présenter des données tabulaires.",
                            recommendation=("Utiliser des tableaux uniquement pour présenter des données tabulaires réelles. Pour la mise en page, utiliser des éléments sémantiques comme <div>, <section>, <article> avec CSS."),
                            evidence={
                                "total_cells": len(all_cells),
                                "meaningful_cells": meaningful_cells,
                                "has_th_elements": len(th_elements) > 0,
                            },
                        )
                    )

        if not findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun problème de structure ou de relation d'information détecté.",
                tested_elements=0,
            )

        # For structural issues, we'll be more definite about failures
        # These are clearer violations of the principle that structure should be in HTML, not CSS
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.FAIL,
            summary=f"{len(findings)} problème(s) de structure ou de relation d'information détecté(s).",
            findings=findings,
            tested_elements=len(findings),
            metadata={
                "structural_issues": len(findings),
                "heading_issues": len([f for f in findings if "heading" in f.element.lower()]),
                "list_issues": len([f for f in findings if "list" in f.element.lower()]),
                "table_issues": len([f for f in findings if "table" in f.element.lower()]),
            },
        )


class Test1023(RGAATest):
    test_id = "10.2.3"
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
        Test 10.2.3: Vérifie que le CSS n'est pas utilisé pour masquer du contenu informatif
        qui devrait être accessible.
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

        # Check for inline styles that hide content
        # Pattern for style attributes with visibility/display properties
        inline_style_pattern = r'style=["\']([^"\']*)["\']'
        inline_styles = re.findall(inline_style_pattern, html_source, re.IGNORECASE)

        hiding_properties = [
            r"display\s*:\s*none",
            r"visibility\s*:\s*hidden",
            r"position\s*:\s*absolute\s*;.*?(?:left\s*:\s*-\d+|right\s*:\s*-\d+|top\s*:\s*-\d+|bottom\s*:\s*-\d+)",
            r"width\s*:\s*0\s*;.*?height\s*:\s*0\s*",
            r"overflow\s*:\s*hidden\s*;.*?(?:width\s*:\s*0\s*|height\s*:\s*0\s*)",
            r"text-indent\s*:\s*-\d+",
            r"font-size\s*:\s*0",
            r"color\s*:\s*transparent",
        ]

        for style_string in inline_styles:
            for hiding_pattern in hiding_properties:
                if re.search(hiding_pattern, style_string, re.IGNORECASE | re.DOTALL):
                    # Try to find which element this style belongs to
                    # We'll look for the element with this style attribute
                    pattern = fr'<([^>]*)\s+style=["\']{re.escape(style_string)}["\'][^>]*>'
                    element_match = re.search(pattern, html_source, re.IGNORECASE)

                    element_info = "unknown element"
                    if element_match:
                        # Try to get more context about the element
                        full_match = element_match.group(0)
                        element_info = full_match[:100]  # Limit length

                    findings.append(
                        Finding(
                            element=element_info,
                            message=f"Un style en ligne masque potentiellement du contenu : '{style_string[:50]}...'.",
                            recommendation=("Vérifier que le contenu masqué n'est pas essentiel à l'information ou à la compréhension de la page. Si c'est de l'information essentielle, elle devrait être visible ou accessible par d'autres moyens."),
                            evidence={
                                "hiding_style": style_string,
                                "hiding_pattern_matched": hiding_pattern,
                            },
                        )
                    )
                    break  # Only flag each style once

        # Check for CSS in style tags that hides content
        style_pattern = r"<style[^>]*>(.*?)</style>"
        style_matches = re.findall(style_pattern, html_source, re.DOTALL | re.IGNORECASE)

        for style_index, style_content in enumerate(style_matches):
            for hiding_pattern in hiding_properties:
                if re.search(hiding_pattern, style_content, re.IGNORECASE | re.DOTALL):
                    findings.append(
                        Finding(
                            element=f"style block {style_index + 1}",
                            message=f"Une règle CSS masque potentiellement du contenu : '{style_content[:100]}...'.",
                            recommendation=("Vérifier que le contenu masqué n'est pas essentiel à l'information ou à la compréhension de la page. Si c'est de l'information essentielle, elle devrait être visible ou accessible par d'autres moyens."),
                            evidence={
                                "style_block_index": style_index,
                                "hiding_pattern_matched": hiding_pattern,
                                "css_content": style_content[:200],
                            },
                        )
                    )
                    break  # Only flag each style block once

        if not findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun usage détecté de CSS pour masquer du contenu informatif.",
                tested_elements=0,
            )

        # For content hiding, we need to be careful - not all hiding is bad
        # Some hiding is for accessibility (skip links, screen-reader only text, etc.)
        # We'll flag these as NEEDS_REVIEW since we can't automatically determine
        # if the hidden content is essential information
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=f"{len(findings)} instance(s) détectée(s) où CSS pourrait masquer du contenu informatif.",
            findings=findings,
            tested_elements=len(findings),
            metadata={
                "potential_hiding_issues": len(findings),
                "inline_style_hiding": len([f for f in findings if "style en ligne" in f.message]),
                "css_block_hiding": len([f for f in findings if "règle CSS" in f.message]),
            },
        )
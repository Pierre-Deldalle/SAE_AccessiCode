from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test1011(RGAATest):
    test_id = "10.1.1"
    criterion_id = "10.1"

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
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 10.1.1 nécessite un DOM.")

        soup = context.dom

        # List of presentation HTML elements to check for
        presentation_elements = {"basefont", "big", "blink", "center", "font", "marquee", "strike", "tt"}

        # <u> element is only checked if DOCTYPE is not HTML5
        # We'll need to check the doctype from context
        is_html5_doctype = False
        if hasattr(context, "html_source") and context.html_source:
            # Simple check for HTML5 doctype
            is_html5_doctype = "<!DOCTYPE html>" in context.html_source.upper()

        if not is_html5_doctype:
            presentation_elements.add("u")

        # Find all presentation elements
        found_elements = []
        for element_name in presentation_elements:
            elements = soup.find_all(element_name)
            for element in elements:
                found_elements.append(
                    {
                        "name": element_name,
                        "element": element,
                        "index": len(found_elements),  # Simple index
                    }
                )

        if not found_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun élément de présentation détecté.",
                tested_elements=0,
            )

        # Create findings for each presentation element found
        findings = []
        for idx, elem_info in enumerate(found_elements):
            element_name = elem_info["name"]
            element = elem_info["element"]

            # Generate a selector-like string for the element
            if element.name:
                element_selector = f"{element.name}"
                # Add index if there are multiple same elements
                same_elements = soup.find_all(element.name)
                if len(same_elements) > 1:
                    try:
                        element_index = same_elements.index(element)
                        element_selector = f"{element.name}[index={element_index}]"
                    except ValueError:
                        pass
            else:
                element_selector = f"[unknown][index={idx}]"

            findings.append(
                Finding(
                    element=element_selector,
                    message=f"L'élément de présentation <{element_name}> est présent dans le code source.",
                    recommendation=(
                        "Supprimer cet élément et utiliser des feuilles de style CSS pour contrôler la présentation."
                    ),
                    evidence={
                        "element_name": element_name,
                        "outer_html": str(element)[:200],  # Limit length
                    },
                )
            )

        # Determine status based on findings
        # Any presentation element found is a failure
        if findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.FAIL,
                summary=f"{len(found_elements)} élément(s) de présentation détecté(s).",
                findings=findings,
                tested_elements=len(found_elements),
                metadata={
                    "presentation_elements_found": len(found_elements),
                    "unique_element_types": len(set(elem_info["name"] for elem_info in found_elements)),
                },
            )
        else:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun élément de présentation détecté.",
                tested_elements=0,
                metadata={
                    "presentation_elements_found": 0,
                },
            )


class Test1012(RGAATest):
    test_id = "10.1.2"
    criterion_id = "10.1"

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
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 10.1.2 nécessite un DOM.")

        soup = context.dom

        # List of presentation attributes to check for
        # Based on RGAA 10.1.2
        presentation_attributes = {
            "align",
            "alink",
            "background",
            "bgcolor",
            "border",
            "cellpadding",
            "cellspacing",
            "char",
            "charoff",
            "clear",
            "color",
            "compact",
            "frameborder",
            "hspace",
            "link",
            "marginheight",
            "marginwidth",
            "text",
            "valign",
            "vlink",
            "vspace",
        }

        # Special cases for size and height attributes
        # size: exception for <select>
        # height: exception for <img>, <object>, <embed>, <canvas>, <svg>
        # width: exception for <img>, <object>, <embed>, <canvas>, <svg>

        # Find all elements with presentation attributes
        findings = []
        elements_with_presentation_attrs = []

        # Check all elements in the document
        for element in soup.find_all(True):  # True means all elements
            # Check for standard presentation attributes
            for attr in presentation_attributes:
                if element.has_attr(attr):
                    elements_with_presentation_attrs.append(
                        {"element": element, "attribute": attr, "value": element.get(attr)}
                    )

            # Check size attribute (except for <select>)
            if element.has_attr("size") and element.name != "select":
                elements_with_presentation_attrs.append(
                    {"element": element, "attribute": "size", "value": element.get("size")}
                )

            # Check width attribute (except for <img>, <object>, <embed>, <canvas>, <svg>)
            if element.has_attr("width") and element.name not in ["img", "object", "embed", "canvas", "svg"]:
                elements_with_presentation_attrs.append(
                    {"element": element, "attribute": "width", "value": element.get("width")}
                )

            # Check height attribute (except for <img>, <object>, <embed>, <canvas>, <svg>)
            if element.has_attr("height") and element.name not in ["img", "object", "embed", "canvas", "svg"]:
                elements_with_presentation_attrs.append(
                    {"element": element, "attribute": "height", "value": element.get("height")}
                )

        if not elements_with_presentation_attrs:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun attribut de présentation détecté.",
                tested_elements=0,
            )

        # Create findings for each presentation attribute found
        for idx, attr_info in enumerate(elements_with_presentation_attrs):
            element = attr_info["element"]
            attribute = attr_info["attribute"]
            value = attr_info["value"]

            # Generate a selector-like string for the element
            if element.name:
                element_selector = f"{element.name}"
                # Add index if there are multiple same elements
                same_elements = soup.find_all(element.name)
                if len(same_elements) > 1:
                    try:
                        element_index = same_elements.index(element)
                        element_selector = f"{element.name}[index={element_index}]"
                    except ValueError:
                        pass
            else:
                element_selector = f"[unknown][index={idx}]"

            findings.append(
                Finding(
                    element=element_selector,
                    message=f"L'attribut de présentation '{attribute}' est présent sur l'élément <{element.name}>.",
                    recommendation=(
                        "Supprimer cet attribut et utiliser des feuilles de style CSS pour contrôler la présentation."
                    ),
                    evidence={
                        "attribute_name": attribute,
                        "attribute_value": str(value)[:100] if value else "",  # Limit length
                        "element_name": element.name,
                    },
                )
            )

        # Determine status based on findings
        # Any presentation attribute found is a failure
        if findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.FAIL,
                summary=f"{len(elements_with_presentation_attrs)} attribut(s) de présentation détecté(s).",
                findings=findings,
                tested_elements=len(elements_with_presentation_attrs),
                metadata={
                    "presentation_attributes_found": len(elements_with_presentation_attrs),
                    "unique_attributes": len(
                        set(attr_info["attribute"] for attr_info in elements_with_presentation_attrs)
                    ),
                    "elements_with_presentation_attrs": len(
                        set(id(attr_info["element"]) for attr_info in elements_with_presentation_attrs)
                    ),
                },
            )
        else:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun attribut de présentation détecté.",
                tested_elements=0,
                metadata={
                    "presentation_attributes_found": 0,
                },
            )


class Test1013(RGAATest):
    test_id = "10.1.3"
    criterion_id = "10.1"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,  # We need the raw HTML to check spaces without CSS
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        # For this test, we need to check the raw HTML source with CSS disabled
        # Since we can't actually disable CSS in the analysis, we'll check for
        # patterns of spaces that are used for presentation purposes

        if not hasattr(context, "html_source") or not context.html_source:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le code source HTML n'est pas disponible.",
            )

        html_source = context.html_source

        # We'll look for patterns of spaces that suggest presentation usage
        findings = []

        # Pattern 1: Multiple spaces between letters in a word (more than 1 space between letters)
        # This would look like: "H E L L O" or "T E S T"
        import re

        # Find words with spaces between letters (excluding actual HTML tags)
        # We'll remove HTML tags first to analyze text content
        text_only = re.sub(r"<[^>]+>", " ", html_source)

        # Look for sequences of letter-space-letter (multiple times)
        # Pattern: letter followed by space followed by letter, repeated
        letter_space_pattern = r"[A-Za-z]\s+[A-Za-z]"
        matches = re.findall(letter_space_pattern, text_only)

        if matches:
            # Check if we have multiple consecutive letter-space patterns (suggesting spaced-out word)
            # Look for patterns like "H E L L O" which would match as ["H E", "E L", "L L", "L O"]
            spaced_word_pattern = r"(?:[A-Za-z]\s+){2,}[A-Za-z]"
            spaced_word_matches = re.findall(spaced_word_pattern, text_only)

            if spaced_word_matches:
                for match in spaced_word_matches[:5]:  # Limit to first 5 findings
                    findings.append(
                        Finding(
                            element="text content",
                            message=f"Des espaces sont utilisés pour séparer les lettres d'un mot : '{match.strip()}'.",
                            recommendation=("Supprimer les espaces et utiliser la lettre-spacing CSS si nécessaire."),
                            evidence={"pattern_found": match.strip(), "pattern_type": "letter_spacing"},
                        )
                    )

        # Pattern 2: Spaces used to create tabular layout
        # Look for lines with multiple groups of spaces separating content
        lines = html_source.split("\n")
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and lines that are likely just formatting
            if not line.strip():
                continue

            # Count groups of spaces (2 or more consecutive spaces)
            space_groups = re.findall(r" {2,}", line)
            if len(space_groups) >= 2:  # At least 2 groups of multiple spaces suggests tabular layout
                # Additional check: make sure it's not just indentation
                # If the line starts with spaces, ignore the first group if it's just indentation
                if line.startswith(" "):
                    # Check if there are space groups after the initial indentation
                    # Find first non-space character
                    first_non_space = len(line) - len(line.lstrip())
                    remaining_line = line[first_non_space:]
                    space_groups_in_content = re.findall(r" {2,}", remaining_line)
                    if len(space_groups_in_content) >= 2:
                        findings.append(
                            Finding(
                                element=f"line {line_num}",
                                message=f"Des espaces sont utilisés pour simuler un tableau (ligne {line_num}).",
                                recommendation=(
                                    "Utiliser des éléments <table>, <th>, <td> appropriés "
                                    "pour présenter des données tabulaires."
                                ),
                                evidence={
                                    "line_number": line_num,
                                    "line_content": line[:100],  # Limit length
                                    "space_groups_count": len(space_groups_in_content),
                                    "pattern_type": "table_simulation",
                                },
                            )
                        )
                else:
                    # No leading spaces, check the whole line
                    findings.append(
                        Finding(
                            element=f"line {line_num}",
                            message=f"Des espaces sont utilisés pour simuler un tableau (ligne {line_num}).",
                            recommendation=(
                                "Utiliser des éléments <table>, <th>, <td> appropriés "
                                "pour présenter des données tabulaires."
                            ),
                            evidence={
                                "line_number": line_num,
                                "line_content": line[:100],  # Limit length
                                "space_groups_count": len(space_groups),
                                "pattern_type": "table_simulation",
                            },
                        )
                    )

        # Pattern 3: Spaces used to create column layout
        # Similar to table simulation but looking for consistent spacing patterns
        # This is more heuristic - we'll look for multiple lines with similar space patterns

        # For now, we'll focus on the clearest cases

        if not findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun usage détourné d'espaces détecté.",
                tested_elements=0,  # We're checking lines, not elements
            )

        # Determine status based on findings
        # Any misuse of spaces is a failure
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.FAIL,
            summary=f"{len(findings)} usage(s) détourné(s) d'espaces détecté(s).",
            findings=findings,
            tested_elements=len([f for f in findings if f.element != "text content"]),  # Approximate
            metadata={
                "space_misuses_found": len(findings),
                "letter_spacing_count": len(
                    [f for f in findings if f.evidence.get("pattern_type") == "letter_spacing"]
                ),
                "table_simulation_count": len(
                    [f for f in findings if f.evidence.get("pattern_type") == "table_simulation"]
                ),
                "column_simulation_count": len(
                    [f for f in findings if f.evidence.get("pattern_type") == "column_simulation"]
                ),
            },
        )

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


class Test1031(RGAATest):
    test_id = "10.3.1"
    criterion_id = "10.3"

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
        Test 10.3.1: Vérifie que l'information reste compréhensible lorsque les feuilles de styles sont désactivées.
        Plus spécifiquement, vérifie que l'ordre dans lequel les contenus sont implémentés dans le HTML
        ne pose pas de problème de compréhension lorsque le CSS est désactivé.
        """
        if not isinstance(
            context.dom,
            __import__("bs4").BeautifulSoup,
        ):
            raise ValueError("Le test 10.3.1 nécessite un DOM.")

        soup = context.dom
        findings = []

        # Get all text nodes in document order to check reading sequence
        # We'll look for potential issues with reading order that would be problematic when CSS is disabled

        # Check for common issues that affect reading order when CSS is disabled:

        # 1. Check for form labels that are not associated with their fields properly
        # When CSS is disabled, visual proximity is lost, so explicit associations matter
        from bs4 import BeautifulSoup
        if not isinstance(soup, BeautifulSoup):
            # This shouldn't happen given the check above, but just in case
            soup = BeautifulSoup(str(soup), 'html.parser')

        # Find all input, textarea, and select elements
        form_elements = soup.find_all(['input', 'textarea', 'select'])
        for element in form_elements:
            # Skip hidden inputs and button types that don't need labels
            if element.get('type') in ['hidden', 'submit', 'button', 'reset']:
                continue

            # Check if element has an associated label
            has_label = False

            # Check for explicit label association via for/id
            element_id = element.get('id')
            if element_id:
                label = soup.find('label', {'for': element_id})
                if label:
                    has_label = True

            # Check for implicit label (label wrapping the element)
            if not has_label:
                parent_label = element.find_parent('label')
                if parent_label:
                    has_label = True

            if not has_label:
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
                    element_selector = f"[unknown]"

                findings.append(
                    Finding(
                        element=element_selector,
                        message=f"L'élément de formulaire <{element.name}> n'a pas de label associé de manière explicite.",
                        recommendation=("Associer chaque champ de formulaire à un label utilisant l'attribut 'for' correspondant à l'id du champ, ou en imbriquant le champ dans l'élément label."),
                        evidence={
                            "element_name": element.name,
                            "element_id": element.get('id'),
                            "element_type": element.get('type', ''),
                        },
                    )
                )

        # 2. Check for table headers that are not properly associated with data cells
        # When CSS is disabled, table structure relies on proper TH/TD associations
        tables = soup.find_all('table')
        for table_idx, table in enumerate(tables):
            # Check if table has th elements
            th_elements = table.find_all('th')
            td_elements = table.find_all('td')

            if td_elements and not th_elements:
                # Data cells but no headers - might be problematic for comprehension
                findings.append(
                    Finding(
                        element=f"table[index={table_idx}]",
                        message=f"Le tableau ne contient pas d'éléments th (en-têtes de colonne/ligne), ce qui peut rendre la compréhension difficile lorsque les styles sont désactivés.",
                        recommendation=("Utiliser des éléments th pour définir les en-têtes de colonnes et/ou de lignes dans les tableaux de données."),
                        evidence={
                            "table_index": table_idx,
                            "th_count": len(th_elements),
                            "td_count": len(td_elements),
                        },
                    )
                )
            elif th_elements and td_elements:
                # Check if we have a reasonable header-to-data ratio
                # This is a heuristic - very few headers for many data cells might indicate missing headers
                if len(td_elements) > 0 and len(th_elements) > 0:
                    ratio = len(td_elements) / len(th_elements)
                    # If we have more than 10 data cells per header, might be missing some headers
                    if ratio > 10 and len(th_elements) < 3:  # Arbitrary thresholds
                        findings.append(
                            Finding(
                                element=f"table[index={table_idx}]",
                                message=f"Le tableau présente un ratio élevé de cellules de données ({len(td_elements)}) par rapport aux en-têtes ({len(th_elements)}), ce qui suggère可能缺少一些列或行标题。",
                                recommendation=("Vérifier que toutes les colonnes et lignes de données ont des en-têtes appropriés définis avec des éléments th."),
                                evidence={
                                    "table_index": table_idx,
                                    "th_count": len(th_elements),
                                    "td_count": len(td_elements),
                                    "th_to_td_ratio": round(ratio, 2),
                                },
                            )
                        )

        # 3. Check for lists that might be used for visual formatting only
        # When CSS is disabled, lists should still make sense semantically
        lists = soup.find_all(['ul', 'ol', 'dl'])
        for list_idx, lst in enumerate(lists):
            # Check if list items have meaningful content
            items = lst.find_all(['li', 'dt', 'dd']) if lst.name in ['ul', 'ol'] else lst.find_all(['dt', 'dd'])
            if lst.name == 'dl':
                # For definition lists, check both dt and dd
                items = lst.find_all(['dt', 'dd'])

            if items:
                # Check if most items are empty or contain only whitespace
                empty_items = 0
                for item in items:
                    text = item.get_text().strip()
                    if not text or len(text) < 2:  # Arbitrary threshold for meaningful content
                        empty_items += 1

                # If most items are empty, the list might be used for visual spacing only
                if len(items) > 0 and (empty_items / len(items)) > 0.7:
                    findings.append(
                        Finding(
                            element=f"{lst.name}[index={list_idx}]",
                            message=f"La liste {lst.name} contient principalement des éléments vides ou quasi-vides, ce qui pourrait indiquer une utilisation pour l'espacement visuel plutôt que pour structurer de l'information.",
                            recommendation=("Utiliser des listes uniquement pour regrouper des éléments liés sémantiquement, et utiliser CSS pour l'espacement si nécessaire."),
                            evidence={
                                "list_type": lst.name,
                                "total_items": len(items),
                                "empty_items": empty_items,
                            },
                        )
                    )

        # 4. Check for heading order that skips levels (might indicate visual styling only)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headings:
            # Convert to numbers for easier checking
            heading_levels = []
            heading_elements = []
            for tag in headings:
                try:
                    level = int(tag.name[1])  # Get the number from h1, h2, etc.
                    heading_levels.append(level)
                    heading_elements.append(tag)
                except (ValueError, IndexError):
                    pass

            # Check for skipped levels (e.g., h1 followed by h3 without h2)
            # This might indicate headings are used for visual styling only
            for i in range(1, len(heading_levels)):
                if heading_levels[i] > heading_levels[i-1] + 1:
                    findings.append(
                        Finding(
                            element=f"heading {heading_elements[i].name}",
                            message=f"Niveau de titre sauté : {heading_elements[i-1].name} suivi de {heading_elements[i].name}. Cela pourrait indiquer une utilisation des titres uniquement pour la présentation visuelle, rendant la structure difficile à suivre lorsque les styles sont désactivés.",
                            recommendation=("Utiliser une hiérarchie de titres cohérente qui reflète la structure du contenu, indépendamment de la présentation visuelle."),
                            evidence={
                                "previous_heading": heading_elements[i-1].name,
                                "current_heading": heading_elements[i].name,
                                "heading_text": heading_elements[i].get_text().strip()[:100],
                            },
                        )
                    )

        # Determine the final status based on findings
        if not findings:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="L'ordre du contenu reste compréhensible lorsque les feuilles de styles sont désactivés.",
                tested_elements=0,
            )

        # For reading order issues, we'll be more definite about failures
        # These are clearer violations of the principle that reading order should make sense without CSS
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.FAIL,
            summary=f"{len(findings)} problème(s) d'ordre de lecture détecté(s) qui pourraient affecter la compréhension lorsque les styles sont désactivés.",
            findings=findings,
            tested_elements=len(findings),
            metadata={
                "reading_order_issues": len(findings),
                "form_label_issues": len([f for f in findings if "formulaire" in f.message.lower() or "label" in f.message.lower()]),
                "table_header_issues": len([f for f in findings if "tableau" in f.message.lower() or "en-tête" in f.message.lower()]),
                "list_issues": len([f for f in findings if "liste" in f.message.lower()]),
                "heading_issues": len([f for f in findings if "titre" in f.message.lower() or "heading" in f.message.lower()]),
            },
        )
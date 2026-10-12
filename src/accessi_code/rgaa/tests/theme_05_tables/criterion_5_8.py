from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.tables import (
    find_tables,
    get_table_rows,
    get_row_cells,
    is_header_cell,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test581(RGAATest):
    test_id = "5.8.1"
    criterion_id = "5.8"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.8.1 nécessite un DOM.")

        soup = context.dom

        # Find all tables (including role="table")
        tables = find_tables(soup)

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        # Identify layout tables (non-data tables)
        layout_tables = []
        for table in tables:
            if not self._is_data_table(table):
                layout_tables.append(table)

        if not layout_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de mise en forme détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        findings: list[Finding] = []
        compliant_layout_tables = 0

        for table_index, table in enumerate(layout_tables):
            # Check if this layout table is compliant
            is_compliant, violations = self._check_layout_table_compliance(table)

            if is_compliant:
                compliant_layout_tables += 1
            else:
                # Generate element identifier
                table_id = table.get("id")
                if isinstance(table_id, str) and table_id.strip():
                    element = f"#{table_id}"
                else:
                    element = f"table[index={table_index}]"

                # Create a finding for this non-compliant layout table
                findings.append(
                    Finding(
                        element=element,
                        message=self._format_violations_message(violations),
                        recommendation=self._get_recommendation(violations),
                    )
                )

        if compliant_layout_tables == len(layout_tables):
            status = TestStatus.PASS
            summary = f"{len(layout_tables)} tableau(x) de mise en forme, tous conformes."
        else:
            status = TestStatus.FAIL
            summary = f"{len(layout_tables)} tableau(x) de mise en forme, {len(findings)} non conforme(s)."

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            summary,
            findings=findings,
            tested_elements=len(layout_tables),
            metadata={
                "total_tables": len(tables),
                "layout_tables": len(layout_tables),
                "compliant_layout_tables": compliant_layout_tables,
            },
        )

    def _is_data_table(self, table: Tag) -> bool:
        """
        Détermine si un tableau est un tableau de données (au sens large).
        Un tableau de données contient au moins une cellule d'en-tête.
        """
        # Vérifier si le tableau contient des cellules d'en-tête
        for element in table.find_all(["th", "td"]):
            if isinstance(element, Tag) and is_header_cell(element):
                return True
        return False

    def _check_layout_table_compliance(self, table: Tag) -> tuple[bool, list[str]]:
        """
        Vérifie la conformité d'un tableau de mise en forme selon le critère 5.8.
        Retourne un tuple (est_conforme, liste_des_violations).
        """
        violations = []

        # Vérifier l'attribut summary du tableau
        summary = table.get("summary")
        if summary is not None and isinstance(summary, str) and summary.strip() != "":
            violations.append("l'attribut summary n'est pas vide")

        # Vérifier la présence d'éléments interdits dans le tableau
        forbidden_selectors = [
            "caption",
            "th",
            "thead",
            "tfoot",
            '[role="rowheader"]',
            '[role="columnheader"]'
        ]

        for selector in forbidden_selectors:
            if table.select_one(selector):
                if selector == "caption":
                    violations.append("contient un élément <caption>")
                elif selector == "th":
                    violations.append("contient un élément <th>")
                elif selector == "thead":
                    violations.append("contient un élément <thead>")
                elif selector == "tfoot":
                    violations.append("contient un élément <tfoot>")
                elif selector == '[role="rowheader"]':
                    violations.append("contient un élément avec role='rowheader'")
                elif selector == '[role="columnheader"]':
                    violations.append("contient un élément avec role='columnheader'")

        # Vérifier les attributs interdits sur les cellules td
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if cell.name == "td":
                    # Vérifier l'attribut scope
                    scope = cell.get("scope")
                    if scope is not None and isinstance(scope, str) and scope.strip() != "":
                        violations.append(f"une cellule <td> possède l'attribut scope")
                        break  # Une seule violation de ce type suffit

                    # Vérifier l'attribut headers
                    headers = cell.get("headers")
                    if headers is not None:
                        if isinstance(headers, str) and headers.strip() != "":
                            violations.append(f"une cellule <td> possède l'attribut headers")
                            break
                        elif isinstance(headers, list) and len(headers) > 0:
                            violations.append(f"une cellule <td> possède l'attribut headers")
                            break

                    # Vérifier l'attribut axis
                    axis = cell.get("axis")
                    if axis is not None and isinstance(axis, str) and axis.strip() != "":
                        violations.append(f"une cellule <td> possède l'attribut axis")
                        break

            # Sortir de la boucle externe si on a déjà trouvé une violation
            if violations:
                break

        return len(violations) == 0, violations

    def _format_violations_message(self, violations: list[str]) -> str:
        """Formate la liste des violations en un message lisible."""
        if not violations:
            return ""

        if len(violations) == 1:
            return violations[0]

        # Pour plusieurs violations, les lister avec des points-virgules
        return " ; ".join(violations)

    def _get_recommendation(self, violations: list[str]) -> str:
        """Génère une recommandation basée sur les violations trouvées."""
        if not violations:
            return ""

        # Recommandations spécifiques selon le type de violation
        specific_recos = []

        # Vérifier les violations liées au tableau lui-même
        table_violations = [v for v in violations if not v.startswith("une cellule <td>")]
        if table_violations:
            specific_recos.append("Supprimer les éléments et attributs interdits du tableau de mise en forme")

        # Vérifier les violations liées aux cellules
        cell_violations = [v for v in violations if v.startswith("une cellule <td>")]
        if cell_violations:
            specific_recos.append("Supprimer les attributs scope, headers et axis des cellules <td>")

        if specific_recos:
            return " ; ".join(specific_recos)

        # Recommandation générique
        return "Supprimer tous les éléments et attributs propres aux tableaux de données du tableau de mise en forme"
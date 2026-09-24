
from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.tables import (
    find_tables,
    get_table_summary_evidence,
    has_complex_header_structure,
)
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)


class Criterion511:
    """
    RGAA 5.1.1

    Pour chaque tableau de données complexe, vérifier
    qu'un résumé permettant de comprendre la nature
    et la structure du tableau est disponible.

    Cette version utilise une détection heuristique
    des tableaux complexes.
    """

    test_id = "5.1.1"
    criterion_id = "5.1"

    def run(self, html: str) -> TestResult:
        # Le document est analysé comme un arbre HTML pour repérer les tableaux.
        soup = BeautifulSoup(html, "html.parser")

        tables = find_tables(soup)

        if not tables:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun tableau détecté.",
                tested_elements=0,
            )

        complex_tables: list[Tag] = []
        findings: list[Finding] = []

        for index, table in enumerate(tables):
            # Les tableaux simples ne sont pas concernés par ce test.
            if not has_complex_header_structure(table):
                continue

            complex_tables.append(table)

            evidence = get_table_summary_evidence(table, soup)

            # La présence d'au moins un mécanisme de résumé valide suffit ici.
            if evidence:
                continue

            table_identifier = table.get("id")

            if isinstance(table_identifier, str) and table_identifier.strip():
                element_name = f"table#{table_identifier}"
            else:
                element_name = f"table[index={index}]"

            findings.append(
                Finding(
                    element=element_name,
                    message=(
                        "Tableau potentiellement complexe sans "
                        "résumé détecté."
                    ),
                    recommendation=(
                        "Ajouter un résumé permettant de comprendre "
                        "la nature et la structure du tableau, "
                        "par exemple via caption ou aria-describedby."
                    ),
                    evidence={
                        "tag": table.name,
                        "attributes": dict(table.attrs),
                        "detected_summary_mechanisms": evidence,
                    },
                )
            )

        # Un document contenant des tableaux, mais aucun tableau complexe,
        # est hors du périmètre fonctionnel de ce test.
        if not complex_tables:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun tableau complexe détecté "
                    "par les vérifications heuristiques."
                ),
                tested_elements=len(tables),
                metadata={
                    "total_tables": len(tables),
                    "complex_tables": 0,
                    "detection_method": "heuristic",
                },
            )

        # Le statut global dépend uniquement des tableaux complexes détectés.
        if findings:
            status = TestStatus.FAIL
            summary = (
                f"{len(findings)} tableau(x) complexe(s) "
                "sans résumé détecté."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Un résumé a été détecté pour les "
                f"{len(complex_tables)} tableau(x) complexe(s)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(complex_tables),
            metadata={
                "total_tables": len(tables),
                "complex_tables": len(complex_tables),
                "detection_method": "heuristic",
                "summary_mechanisms": [
                    "caption",
                    "summary",
                    "aria-describedby",
                ],
                "limitations": [
                    "La complexité du tableau est détectée "
                    "par heuristique.",
                    "La pertinence du résumé n'est pas évaluée "
                    "par cette version.",
                    "Les tableaux dynamiques nécessitent "
                    "une analyse du DOM rendu.",
                ],
            },
        )
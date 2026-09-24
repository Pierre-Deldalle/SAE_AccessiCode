
from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_labeling_evidence,
)
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)


class Criterion111:
    """
    RGAA 11.1.1

    Chaque champ de formulaire doit posséder une étiquette
    via l'un des mécanismes prévus par le test.

    Cette version couvre les contrôles structurels suivants :
    - aria-labelledby
    - aria-label
    - label[for] associé au champ
    - title

    La situation particulière du bouton adjacent nécessite
    une analyse complémentaire.
    """

    test_id = "11.1.1"
    criterion_id = "11.1"

    def run(self, html: str) -> TestResult:
        # Le HTML est converti en arbre pour rechercher les champs du formulaire.
        soup = BeautifulSoup(html, "html.parser")

        fields = find_form_fields(soup)

        if not fields:
            # Sans champ à évaluer, le test ne s'applique pas à la page.
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun champ de formulaire détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        labelled_fields = 0

        for index, field in enumerate(fields):
            # Chaque champ est vérifié indépendamment afin d'identifier les
            # éléments précis qui ne disposent d'aucun nom accessible.
            identifier = get_element_identifier(field, index)

            evidence = get_labeling_evidence(field, soup)

            if evidence:
                # Plusieurs mécanismes peuvent être valides pour un même champ.
                labelled_fields += 1

                continue

            findings.append(
                Finding(
                    element=identifier,
                    message=(
                        "Aucun mécanisme d'étiquetage détecté "
                        "par les vérifications structurelles."
                    ),
                    recommendation=(
                        "Associer une balise label au champ ou fournir "
                        "un nom accessible via aria-label, "
                        "aria-labelledby ou title, selon le contexte."
                    ),
                    evidence={
                        "tag": field.name,
                        "attributes": dict(field.attrs),
                        "detected_labeling_mechanisms": evidence,
                    },
                )
            )

        # Un seul champ sans étiquette suffit à faire échouer le test.
        if findings:
            status = TestStatus.FAIL
            summary = (
                f"{len(findings)} champ(s) sans étiquette détectée "
                f"sur {len(fields)}."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Une étiquette a été détectée pour les "
                f"{len(fields)} champ(s) analysés."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(fields),
            metadata={
                "labelled_fields": labelled_fields,
                "unlabelled_fields": len(findings),
                "structural_checks": [
                    "aria-labelledby",
                    "aria-label",
                    "label-for",
                    "title",
                ],
                "limitations": [
                    "Le cas du bouton adjacent n'est pas automatisé "
                    "dans cette version.",
                    "La pertinence sémantique du nom accessible "
                    "nécessite une analyse complémentaire.",
                    "Les vérifications de visibilité et de proximité "
                    "ne sont pas toutes couvertes.",
                ],
            },
        )
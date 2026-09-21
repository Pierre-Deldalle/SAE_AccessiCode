"""Contrôle DOM RGAA 1.1.3 des boutons image ``input[type="image"]``.

Le contrôle ignore les autres types de champs et vérifie, pour chaque bouton
image, ``aria-labelledby``, ``aria-label``, ``alt`` et ``title``. Une seule
alternative textuelle non vide suffit à valider l'élément.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import (
    get_labelledby_text,
    get_non_empty_attribute,
)
from accessi_code.models.result import (
    Finding,
    TestResult as Result,
    TestStatus as ResultStatus,
)


class Criterion113:
    """RGAA 1.1.3 : vérifie les alternatives des input type=image."""

    test_id = "1.1.3"
    criterion_id = "1.1"

    def run(self, html: str) -> Result:
        """Analyse les boutons image et retourne les éventuelles anomalies."""
        soup = BeautifulSoup(html, "html.parser")
        image_inputs = [
            element
            for element in soup.find_all("input")
            if str(element.get("type", "text")).lower() == "image"
        ]

        if not image_inputs:
            return Result(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=ResultStatus.NOT_APPLICABLE,
                summary="Aucun élément input type=image détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        valid_inputs = 0

        for index, image_input in enumerate(image_inputs):
            evidence = self._get_alternative_evidence(image_input, soup)

            if evidence:
                valid_inputs += 1
                continue

            findings.append(
                Finding(
                    element=f"input[type='image'][index={index}]",
                    message="Aucune alternative textuelle valide détectée.",
                    recommendation=(
                        "Ajouter aria-labelledby, aria-label, alt ou title "
                        "non vide à l'élément input type=image."
                    ),
                    evidence={
                        "tag": image_input.name,
                        "attributes": dict(image_input.attrs),
                        "allowed_attributes": [
                            "aria-labelledby",
                            "aria-label",
                            "alt",
                            "title",
                        ],
                        "detected_alternatives": evidence,
                    },
                )
            )

        status = ResultStatus.FAIL if findings else ResultStatus.PASS
        summary = (
            f"{len(findings)} input(s) type=image sans alternative textuelle "
            f"sur {len(image_inputs)}."
            if findings
            else f"Une alternative textuelle a été détectée pour les "
            f"{valid_inputs} input(s) type=image analysés."
        )

        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(image_inputs),
            metadata={
                "valid_inputs": valid_inputs,
                "invalid_inputs": len(findings),
                "checked_elements": ["input[type='image']"],
                "allowed_attributes": [
                    "aria-labelledby",
                    "aria-label",
                    "alt",
                    "title",
                ],
            },
        )

    @staticmethod
    def _get_alternative_evidence(
        image_input: Tag,
        soup: BeautifulSoup,
    ) -> list[str]:
        evidence: list[str] = []

        labelledby_valid, _ = get_labelledby_text(image_input, soup)
        if labelledby_valid:
            evidence.append("aria-labelledby")

        for attribute in ("aria-label", "alt", "title"):
            if get_non_empty_attribute(image_input, attribute) is not None:
                evidence.append(attribute)

        return evidence

"""Contrôle DOM RGAA 1.1.2 des zones réactives ``area``.

Chaque élément ``area`` est vérifié individuellement. Le contrôle est validé
si l'élément possède une valeur non vide dans ``aria-label`` ou ``alt``.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.dom import get_non_empty_attribute
from accessi_code.models.result import (
	Finding,
	TestResult as Result,
	TestStatus as ResultStatus,
)


class Criterion112:
	"""RGAA 1.1.2 : vérifie les alternatives textuelles des éléments area."""

	test_id = "1.1.2"
	criterion_id = "1.1"

	def run(self, html: str) -> Result:
		"""Analyse les éléments ``area`` présents dans le document HTML."""
		soup = BeautifulSoup(html, "html.parser")
		areas = soup.find_all("area")

		if not areas:
			return Result(
				test_id=self.test_id,
				criterion_id=self.criterion_id,
				status=ResultStatus.NOT_APPLICABLE,
				summary="Aucune zone réactive <area> détectée.",
				tested_elements=0,
			)

		findings: list[Finding] = []
		valid_areas = 0

		for index, area in enumerate(areas):
			evidence = [
				attribute
				for attribute in ("aria-label", "alt")
				if get_non_empty_attribute(area, attribute) is not None
			]

			if evidence:
				valid_areas += 1
				continue

			findings.append(
				Finding(
					element=f"area[index={index}]",
					message="Aucune alternative textuelle valide détectée.",
					recommendation=(
						"Ajouter un attribut aria-label ou alt non vide à "
						"l'élément <area>."
					),
					evidence={
						"tag": area.name,
						"attributes": dict(area.attrs),
						"allowed_attributes": ["aria-label", "alt"],
						"detected_alternatives": evidence,
					},
				)
			)

		status = ResultStatus.FAIL if findings else ResultStatus.PASS
		summary = (
			f"{len(findings)} zone(s) réactive(s) sans alternative textuelle "
			f"sur {len(areas)}."
			if findings
			else f"Une alternative textuelle a été détectée pour les "
			f"{valid_areas} zone(s) réactive(s) analysées."
		)

		return Result(
			test_id=self.test_id,
			criterion_id=self.criterion_id,
			status=status,
			summary=summary,
			findings=findings,
			tested_elements=len(areas),
			metadata={
				"valid_areas": valid_areas,
				"invalid_areas": len(findings),
				"checked_elements": ["area"],
				"allowed_attributes": ["aria-label", "alt"],
			},
		)

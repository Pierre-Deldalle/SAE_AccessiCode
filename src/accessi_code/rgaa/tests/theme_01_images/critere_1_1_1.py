"""Contrôle DOM RGAA 1.1.1 des alternatives textuelles des images.

Le critère analyse les éléments ``img`` et les éléments portant
``role="img"``. Une image est considérée conforme dès qu'une alternative
textuelle autorisée et non vide est détectée. Les éléments ``role="img"``
n'acceptent que ``aria-labelledby`` et ``aria-label`` ; les éléments ``img``
acceptent également ``alt`` et ``title``.
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


class Criterion111:
	"""RGAA 1.1.1 : vérifie les alternatives textuelles des images."""

	test_id = "1.1.1"
	criterion_id = "1.1"

	def run(self, html: str) -> Result:
		"""Analyse le HTML et retourne un résultat structuré du critère."""
		soup = BeautifulSoup(html, "html.parser")
		images = soup.select("img, [role='img']")

		if not images:
			return Result(
				test_id=self.test_id,
				criterion_id=self.criterion_id,
				status=ResultStatus.NOT_APPLICABLE,
				summary="Aucune image détectée.",
				tested_elements=0,
			)

		findings: list[Finding] = []
		valid_images = 0

		for index, image in enumerate(images):
			is_role_image = image.get("role") == "img" and image.name != "img"
			allowed_attributes = (
				("aria-labelledby", "aria-label")
				if is_role_image
				else ("aria-labelledby", "aria-label", "alt", "title")
			)
			evidence = self._get_alternative_evidence(
				image, soup, allowed_attributes
			)

			if evidence:
				valid_images += 1
				continue

			element_type = "[role='img']" if is_role_image else "<img>"
			findings.append(
				Finding(
					element=f"{element_type}[index={index}]",
					message="Aucune alternative textuelle valide détectée.",
					recommendation=(
						"Ajouter aria-labelledby, aria-label, alt ou title "
						"pour un élément img, ou aria-labelledby ou aria-label "
						"pour un élément role=img."
					),
					evidence={
						"tag": image.name,
						"attributes": dict(image.attrs),
						"allowed_attributes": allowed_attributes,
						"detected_alternatives": evidence,
					},
				)
			)

		status = ResultStatus.FAIL if findings else ResultStatus.PASS
		summary = (
			f"{len(findings)} image(s) sans alternative textuelle sur "
			f"{len(images)}."
			if findings
			else f"Une alternative textuelle a été détectée pour les "
			f"{valid_images} image(s) analysées."
		)

		return Result(
			test_id=self.test_id,
			criterion_id=self.criterion_id,
			status=status,
			summary=summary,
			findings=findings,
			tested_elements=len(images),
			metadata={
				"valid_images": valid_images,
				"invalid_images": len(findings),
				"checked_elements": ["img", "[role='img']"],
			},
		)

	@staticmethod
	def _get_alternative_evidence(
		image: Tag,
		soup: BeautifulSoup,
		attributes: tuple[str, ...],
	) -> list[str]:
		evidence: list[str] = []

		labelledby_valid, _ = get_labelledby_text(image, soup)
		if "aria-labelledby" in attributes and labelledby_valid:
			evidence.append("aria-labelledby")

		for attribute in attributes:
			if attribute != "aria-labelledby" and get_non_empty_attribute(
				image, attribute
			) is not None:
				evidence.append(attribute)

		return evidence

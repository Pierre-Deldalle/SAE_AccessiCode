from __future__ import annotations

import re

from bs4 import BeautifulSoup, Doctype, Tag

from accessi_code.models.result import Finding, TestResult, TestStatus


class Criterion811:
	"""RGAA 8.1.1 : vérifie le type de document d'une page web."""

	test_id = "8.1.1"
	criterion_id = "8.1"

	def run(self, html: str) -> TestResult:
		soup = BeautifulSoup(html, "html.parser")
		doctypes = [node for node in soup.contents if isinstance(node, Doctype)]
		html_element = soup.find("html")

		valid_doctype = (
			len(doctypes) == 1
			and self._is_valid_doctype(str(doctypes[0]))
		)
		doctype_before_html = (
			valid_doctype
			and isinstance(html_element, Tag)
			and soup.contents.index(doctypes[0])
			< soup.contents.index(html_element)
		)

		if doctype_before_html:
			return TestResult(
				test_id=self.test_id,
				criterion_id=self.criterion_id,
				status=TestStatus.PASS,
				summary="Le type de document est présent, valide et placé avant html.",
				tested_elements=1,
				metadata={"doctype": str(doctypes[0]).strip()},
			)

		if not doctypes:
			message = "Aucune balise DOCTYPE détectée."
		elif len(doctypes) > 1:
			message = "Plusieurs balises DOCTYPE détectées."
		elif not self._is_valid_doctype(str(doctypes[0])):
			message = "Le type de document détecté n'est pas valide."
		else:
			message = "La balise DOCTYPE doit être placée avant html."

		return TestResult(
			test_id=self.test_id,
			criterion_id=self.criterion_id,
			status=TestStatus.FAIL,
			summary=message,
			findings=[
				Finding(
					element="document",
					message=message,
					recommendation="Ajouter <!DOCTYPE html> avant la balise <html>.",
					evidence={
						"doctypes": [str(doctype).strip() for doctype in doctypes],
						"html_element_present": isinstance(html_element, Tag),
					},
				)
			],
			tested_elements=1,
		)

	@staticmethod
	def _is_valid_doctype(doctype: str) -> bool:
		normalized = " ".join(doctype.split()).strip()
		return bool(
			re.fullmatch(r"html", normalized, flags=re.IGNORECASE)
			or re.fullmatch(
				r"html\s+public\s+\"[^\"]+\"(?:\s+\"[^\"]+\")?",
				normalized,
				flags=re.IGNORECASE,
			)
			or re.fullmatch(
				r"html\s+system\s+\"[^\"]+\"",
				normalized,
				flags=re.IGNORECASE,
			)
		)

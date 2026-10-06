from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test121(RGAATest):
    test_id = "1.2.1"
    criterion_id = "1.2"

    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None) -> TestResult:
        soup = self._get_dom(context)

        images = self._find_decorative_images_without_caption(soup)

        if not images:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune image décorative détectée.",
                tested_elements=0,
            )

        findings: list[Finding] = []

        for image in images:
            if self._is_conformant(image):
                continue

            findings.append(
                Finding(
                    element=str(image),
                    message=(
                        "L'image décorative possède un attribut permettant "
                        "de fournir une alternative textuelle alors qu'elle "
                        "doit être ignorée par les technologies d'assistance."
                    ),
                    recommendation=(
                        'Supprimer les attributs "aria-labelledby", '
                        '"aria-label" ou "title" de l’image décorative.'
                    ),
                )
            )

        status = (
            TestStatus.PASS
            if not findings
            else TestStatus.FAIL
        )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(images)} image(s) décorative(s) analysée(s), "
                f"{len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(images),
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 1.2.1 nécessite un DOM.")

        return context.dom

    @classmethod
    def _find_decorative_images_without_caption(
        cls,
        soup: BeautifulSoup,
    ) -> list[Tag]:
        return [
            image
            for image in soup.find_all("img")
            if not cls._has_caption(image)
            and cls._is_decorative_candidate(image)
        ]

    @staticmethod
    def _has_caption(image: Tag) -> bool:
        figure = image.find_parent("figure")

        if figure is None:
            return False

        return figure.find("figcaption") is not None

    @staticmethod
    def _is_decorative_candidate(image: Tag) -> bool:
        alt = image.get("alt")

        if alt == "":
            return True

        aria_hidden = image.get("aria-hidden")
        if isinstance(aria_hidden, str) and aria_hidden.strip().lower() == "true":
            return True

        role = image.get("role")
        if isinstance(role, str):
            roles = {value.strip().lower() for value in role.split()}
            if "presentation" in roles:
                return True

        return False

    @staticmethod
    def _is_conformant(image: Tag) -> bool:
        forbidden_attributes = (
            "aria-labelledby",
            "aria-label",
            "title",
        )

        if any(image.has_attr(attribute) for attribute in forbidden_attributes):
            return False

        alt_is_empty = image.get("alt") == ""

        aria_hidden = image.get("aria-hidden")
        aria_hidden_true = (
            isinstance(aria_hidden, str)
            and aria_hidden.strip().lower() == "true"
        )

        role = image.get("role")
        role_presentation = False

        if isinstance(role, str):
            roles = {value.strip().lower() for value in role.split()}
            role_presentation = "presentation" in roles

        return alt_is_empty or aria_hidden_true or role_presentation
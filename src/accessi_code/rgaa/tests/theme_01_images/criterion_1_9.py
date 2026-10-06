from __future__ import annotations

from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import ImageRoleAnalysis
from accessi_code.analysis.dom import (
    get_labelledby_text,
    get_non_empty_attribute,
)
from accessi_code.analysis.images import (
    ImageInfo,
    extract_image_map_areas,
    extract_images,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest

class Test191(RGAATest):
    test_id = "1.9.1"
    criterion_id = "1.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        images = self._find_images_with_caption(soup)

        if not images:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune image avec légende détectée.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        failed = 0

        for index, image in enumerate(images):
            identifier = self._identifier(image, index)
            figure = image.find_parent("figure")

            caption = self._find_adjacent_caption(image, figure)

            errors: list[str] = []

            # 1. Image et légende dans le même <figure>
            if figure is None:
                errors.append(
                    "L'image et sa légende ne sont pas contenues "
                    "dans une balise <figure>."
                )

            # 2. role="figure" ou role="group"
            if figure is not None:
                role = figure.get("role")

                if role not in {"figure", "group"}:
                    errors.append(
                        'La balise <figure> ne possède pas '
                        'role="figure" ou role="group".'
                    )

            # 3. aria-label identique à la légende
            if figure is not None and caption is not None:
                aria_label = figure.get("aria-label", "")
                caption_text = caption.get_text(" ", strip=True)

                if (
                    not isinstance(aria_label, str)
                    or not aria_label.strip()
                    or aria_label.strip() != caption_text.strip()
                ):
                    errors.append(
                        "L'attribut aria-label de <figure> "
                        "n'est pas identique au contenu de la légende."
                    )

            # 4. La légende doit être dans <figcaption>
            if caption is None or caption.name != "figcaption":
                errors.append(
                    "La légende n'est pas contenue dans une balise "
                    "<figcaption>."
                )

            if errors:
                failed += 1

                findings.append(
                    Finding(
                        element=identifier,
                        message="Image légendée non conforme au test 1.9.1.",
                        recommendation=(
                            "Placer l'image et sa légende dans un <figure>, "
                            'ajouter role="figure" ou role="group", '
                            "ajouter un aria-label identique au contenu "
                            "de la légende et utiliser <figcaption>."
                        ),
                        evidence={
                            "errors": errors,
                            "caption": (
                                caption.get_text(" ", strip=True)
                                if caption is not None
                                else None
                            ),
                        },
                    )
                )

        status = TestStatus.FAIL if failed else TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(images)} image(s) avec légende : "
                f"{failed} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(images),
            metadata={
                "candidate_images": len(images),
                "failed_images": failed,
            },
        )

    @staticmethod
    def _find_images_with_caption(
        soup: BeautifulSoup,
    ) -> list[Tag]:
        images: list[Tag] = []

        candidates = [
            *soup.find_all("img"),
            *soup.find_all(
                "input",
                attrs={"type": lambda value: value and value.lower() == "image"},
            ),
            *soup.find_all(
                attrs={"role": lambda value: value and value.lower() == "img"}
            ),
        ]

        for image in candidates:
            if Test191._find_adjacent_caption(
                image,
                image.find_parent("figure"),
            ) is not None:
                images.append(image)

        return images

    @staticmethod
    def _find_adjacent_caption(
        image: Tag,
        figure: Tag | None,
    ) -> Tag | None:
        # Cas conforme ou non conforme avec <figcaption>.
        if figure is not None:
            figcaptions = figure.find_all("figcaption")

            if figcaptions:
                return figcaptions[0]

        # Recherche d'une légende adjacente.
        previous = image.find_previous_sibling()
        if isinstance(previous, Tag) and previous.get_text(" ", strip=True):
            return previous

        following = image.find_next_sibling()
        if isinstance(following, Tag) and following.get_text(" ", strip=True):
            return following

        return None

    @staticmethod
    def _identifier(element: Tag, index: int) -> str:
        element_id = element.get("id")

        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 1.9.1 nécessite un DOM.")

        return context.dom
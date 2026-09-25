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


class Test111(RGAATest):
    test_id = "1.1.1"
    criterion_id = "1.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.IMAGES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        elements = list(soup.select("img, [role='img']"))

        if not elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune image concernée détectée.",
            )

        image_infos = extract_images(
            soup,
            base_dir=self._get_base_dir(context),
        )

        analyzer = (
            getattr(
                services,
                "image_analyzer",
                None,
            )
            if services is not None
            else None
        )

        native_index = 0

        findings: list[Finding] = []

        informative = 0
        compliant = 0
        non_informative = 0
        failed = 0
        needs_review = 0
        errors = 0

        for index, element in enumerate(elements):
            native = element.name == "img"

            image_info: ImageInfo | None = None

            if native:
                if native_index < len(image_infos):
                    image_info = image_infos[native_index]

                native_index += 1

            if analyzer is None:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._identifier(
                            element,
                            index,
                        ),
                        message=("Le rôle informationnel de l'image n'a pas pu être déterminé."),
                        recommendation=("Exécuter le test avec le service IA ou vérifier manuellement l'image."),
                    )
                )
                continue

            try:
                if native:
                    if image_info is None:
                        raise ValueError("ImageInfo introuvable.")

                    analysis = await analyzer.analyze_information_role(image_info)

                else:
                    parent = (
                        element.parent
                        if isinstance(
                            element.parent,
                            Tag,
                        )
                        else None
                    )

                    surrounding = (
                        parent.get_text(
                            " ",
                            strip=True,
                        )
                        if parent is not None
                        else ""
                    )

                    analysis = await analyzer.analyze_element_information_role(
                        str(element),
                        surrounding,
                    )

                if not isinstance(
                    analysis,
                    ImageRoleAnalysis,
                ):
                    raise TypeError("L'analyseur doit retourner ImageRoleAnalysis.")

            except Exception as error:
                errors += 1

                findings.append(
                    Finding(
                        element=self._identifier(
                            element,
                            index,
                        ),
                        message=("L'analyse du rôle informationnel de l'image a échoué."),
                        recommendation=("Relancer l'analyse ou vérifier manuellement."),
                        evidence={
                            "error": str(error),
                        },
                    )
                )
                continue

            if analysis.information_bearing is False:
                non_informative += 1
                continue

            if analysis.information_bearing is None:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._identifier(
                            element,
                            index,
                        ),
                        message=(analysis.explanation or "Le rôle informationnel reste incertain."),
                        recommendation=("Vérifier manuellement le rôle de l'image."),
                        evidence={
                            "analysis_confidence": analysis.confidence,
                            "uncertainties": analysis.uncertainties,
                        },
                    )
                )
                continue

            informative += 1

            allowed = (
                (
                    "aria-labelledby",
                    "aria-label",
                    "alt",
                    "title",
                )
                if native
                else (
                    "aria-labelledby",
                    "aria-label",
                )
            )

            evidence = self._get_alternative_evidence(
                element,
                soup,
                allowed,
            )

            if evidence:
                compliant += 1
                continue

            failed += 1

            findings.append(
                Finding(
                    element=self._identifier(
                        element,
                        index,
                    ),
                    message=(
                        "L'image est considérée porteuse d'information "
                        "mais aucune alternative textuelle autorisée "
                        "n'a été détectée."
                    ),
                    recommendation=("Ajouter une alternative textuelle adaptée."),
                    evidence={
                        "information_role": {
                            "explanation": analysis.explanation,
                            "confidence": analysis.confidence,
                            "uncertainties": analysis.uncertainties,
                        },
                    },
                )
            )

        if failed:
            status = TestStatus.FAIL

        elif errors:
            status = TestStatus.ERROR

        elif needs_review:
            status = TestStatus.NEEDS_REVIEW

        elif informative == 0:
            status = TestStatus.NOT_APPLICABLE

        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(elements)} image(s) candidate(s) : "
                f"{informative} porteuse(s) d'information, "
                f"{compliant} conforme(s), "
                f"{non_informative} hors périmètre, "
                f"{failed} non conforme(s), "
                f"{needs_review} à vérifier, "
                f"{errors} erreur(s)."
            ),
            findings=findings,
            tested_elements=informative,
            metadata={
                "candidate_images": len(elements),
                "informative_images": informative,
                "non_informative_images": non_informative,
                "compliant_images": compliant,
                "failed_images": failed,
                "needs_review": needs_review,
                "errors": errors,
            },
        )

    @staticmethod
    def _get_alternative_evidence(
        image: Tag,
        soup: BeautifulSoup,
        attributes: tuple[str, ...],
    ) -> list[str]:
        evidence: list[str] = []

        if "aria-labelledby" in attributes:
            valid, _ = get_labelledby_text(
                image,
                soup,
            )

            if valid:
                evidence.append("aria-labelledby")

        for attribute in attributes:
            if attribute == "aria-labelledby":
                continue

            if (
                get_non_empty_attribute(
                    image,
                    attribute,
                )
                is not None
            ):
                evidence.append(attribute)

        return evidence

    @staticmethod
    def _identifier(
        element: Tag,
        index: int,
    ) -> str:
        element_id = element.get("id")

        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        if element.name == "img":
            return f"img[index={index}]"

        return f"[role='img'][index={index}]"

    @staticmethod
    def _get_base_dir(
        context: AuditContext,
    ) -> Path | None:
        return context.html_path.parent if context.html_path is not None else None

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 1.1.1 nécessite un DOM.")

        return context.dom


class Test112(RGAATest):
    test_id = "1.1.2"
    criterion_id = "1.1"

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
        soup = self._get_dom(context)

        areas = [
            area
            for area in extract_image_map_areas(
                soup,
                base_dir=(context.html_path.parent if context.html_path else None),
            )
            if area.href is not None
        ]

        if not areas:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune zone réactive area détectée.",
            )

        analyzer = (
            getattr(
                services,
                "image_analyzer",
                None,
            )
            if services is not None
            else None
        )

        findings: list[Finding] = []

        informative = 0
        valid = 0
        outside_scope = 0
        failed = 0
        review = 0
        errors = 0

        for area in areas:
            if analyzer is None:
                review += 1
                continue

            try:
                analysis = await analyzer.analyze_area_information_role(area)

            except Exception as error:
                errors += 1

                findings.append(
                    Finding(
                        element=f"area[index={area.index}]",
                        message="L'analyse IA de la zone a échoué.",
                        evidence={
                            "error": str(error),
                        },
                    )
                )
                continue

            if analysis.information_bearing is False:
                outside_scope += 1
                continue

            if analysis.information_bearing is None:
                review += 1
                continue

            informative += 1

            alternatives = [
                name
                for name, value in (
                    (
                        "aria-label",
                        area.aria_label,
                    ),
                    (
                        "alt",
                        area.alt,
                    ),
                )
                if value
            ]

            if alternatives:
                valid += 1
                continue

            failed += 1

            findings.append(
                Finding(
                    element=f"area[index={area.index}]",
                    message=("La zone réactive semble porteuse d'information mais n'a pas d'alternative."),
                    recommendation=("Ajouter alt ou aria-label."),
                    evidence={
                        "href": area.href,
                        "shape": area.shape,
                        "coords": area.coords,
                    },
                )
            )

        if failed:
            status = TestStatus.FAIL
        elif errors:
            status = TestStatus.ERROR
        elif review:
            status = TestStatus.NEEDS_REVIEW
        elif informative == 0:
            status = TestStatus.NOT_APPLICABLE
        else:
            status = TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (
                f"{informative} zone(s) porteuse(s) d'information : "
                f"{valid} conforme(s), {failed} non conforme(s), "
                f"{review} à vérifier."
            ),
            findings=findings,
            tested_elements=informative,
            metadata={
                "candidate_areas": len(areas),
                "outside_scope": outside_scope,
                "errors": errors,
            },
        )

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 1.1.2 nécessite un DOM.")

        return context.dom


class Test113(RGAATest):
    test_id = "1.1.3"
    criterion_id = "1.1"

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
        soup = self._get_dom(context)

        image_inputs = [
            element
            for element in soup.find_all("input")
            if (
                str(
                    element.get(
                        "type",
                        "",
                    )
                ).lower()
                == "image"
            )
        ]

        if not image_inputs:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun input[type=image] détecté.",
            )

        findings: list[Finding] = []

        for index, element in enumerate(image_inputs):
            evidence: list[str] = []

            valid_labelledby, _ = get_labelledby_text(
                element,
                soup,
            )

            if valid_labelledby:
                evidence.append("aria-labelledby")

            for attribute in (
                "aria-label",
                "alt",
                "title",
            ):
                if (
                    get_non_empty_attribute(
                        element,
                        attribute,
                    )
                    is not None
                ):
                    evidence.append(attribute)

            if evidence:
                continue

            findings.append(
                Finding(
                    element=(f"input[type='image'][index={index}]"),
                    message=("Aucune alternative textuelle autorisée n'a été détectée."),
                    recommendation=("Ajouter aria-labelledby, aria-label, alt ou title."),
                )
            )

        status = TestStatus.FAIL if findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{len(image_inputs)} bouton(s) image analysé(s), {len(findings)} non conforme(s)."),
            findings=findings,
            tested_elements=len(image_inputs),
        )

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 1.1.3 nécessite un DOM.")

        return context.dom

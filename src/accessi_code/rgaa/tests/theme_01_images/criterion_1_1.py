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
    extract_images,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)


class Test111:
    """
    RGAA 1.1.1

    Vérifie que les images porteuses d'information disposent
    d'une alternative textuelle.

    Le DOM permet de détecter les alternatives disponibles.
    Lorsqu'une image img ne possède pas d'alternative exploitable,
    une analyse visuelle et sémantique peut aider à déterminer
    si elle est porteuse d'information.
    """

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
        soup = self._get_dom(
            context
        )

        elements = list(
            soup.select(
                "img, [role='img']"
            )
        )

        if not elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun élément img ou role=img détecté."
                ),
                tested_elements=0,
            )

        image_infos = extract_images(
            soup,
            base_dir=self._get_base_dir(
                context
            ),
        )

        image_info_index = 0

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

        valid_images = 0
        decorative_images = 0
        failed_images = 0
        needs_review = 0
        errors = 0

        for index, element in enumerate(
            elements
        ):
            is_native_image = (
                element.name == "img"
            )

            is_role_image = (
                not is_native_image
                and element.get("role")
                == "img"
            )

            image_info: ImageInfo | None = None

            if is_native_image:
                if image_info_index < len(
                    image_infos
                ):
                    image_info = image_infos[
                        image_info_index
                    ]

                image_info_index += 1

            allowed_attributes = (
                (
                    "aria-labelledby",
                    "aria-label",
                )
                if is_role_image
                else (
                    "aria-labelledby",
                    "aria-label",
                    "alt",
                    "title",
                )
            )

            alternative_evidence = (
                self._get_alternative_evidence(
                    element,
                    soup,
                    allowed_attributes,
                )
            )

            if alternative_evidence:
                valid_images += 1
                continue

            #
            # Pour un élément role=img qui n'est pas une vraie balise img,
            # nous ne disposons actuellement pas d'un fichier image précis
            # à transmettre au VLM.
            #
            if is_role_image:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            "Aucune alternative textuelle n'a été "
                            "détectée et le rôle informationnel de "
                            "cet élément role=img ne peut pas encore "
                            "être évalué automatiquement."
                        ),
                        recommendation=(
                            "Vérifier si l'élément est porteur "
                            "d'information et, si nécessaire, "
                            "ajouter aria-label ou aria-labelledby."
                        ),
                        evidence={
                            "tag": element.name,
                            "attributes": dict(
                                element.attrs
                            ),
                            "detected_alternatives": (
                                alternative_evidence
                            ),
                            "information_bearing": (
                                "unknown"
                            ),
                        },
                    )
                )

                continue

            if image_info is None:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            "Impossible de récupérer les informations "
                            "nécessaires à l'analyse de cette image."
                        ),
                        recommendation=(
                            "Vérifier manuellement si l'image est "
                            "porteuse d'information."
                        ),
                    )
                )

                continue

            if analyzer is None:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            "Aucune alternative textuelle n'a été "
                            "détectée et aucun analyseur visuel "
                            "n'est disponible pour déterminer si "
                            "l'image est porteuse d'information."
                        ),
                        recommendation=(
                            "Vérifier manuellement le rôle de l'image "
                            "ou exécuter le test avec le service IA."
                        ),
                        evidence={
                            "src": image_info.src,
                            "information_bearing": (
                                "unknown"
                            ),
                        },
                    )
                )

                continue

            try:
                analysis = (
                    await analyzer.analyze_information_role(
                        image_info
                    )
                )

                if not isinstance(
                    analysis,
                    ImageRoleAnalysis,
                ):
                    raise TypeError(
                        "L'analyseur doit retourner "
                        "un ImageRoleAnalysis."
                    )

            except Exception as error:
                errors += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            "L'analyse IA du rôle de l'image "
                            "a échoué."
                        ),
                        recommendation=(
                            "Relancer l'analyse ou vérifier "
                            "manuellement le rôle de l'image."
                        ),
                        evidence={
                            "src": image_info.src,
                            "error": str(error),
                        },
                    )
                )

                continue

            evidence = {
                "src": image_info.src,
                "information_bearing": (
                    analysis.information_bearing
                ),
                "analysis_explanation": (
                    analysis.explanation
                ),
                "analysis_confidence": (
                    analysis.confidence
                ),
                "analysis_uncertainties": (
                    analysis.uncertainties
                ),
            }

            if (
                analysis.information_bearing
                is True
            ):
                failed_images += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            "L'image semble porteuse d'information "
                            "mais aucune alternative textuelle "
                            "exploitable n'a été détectée."
                        ),
                        recommendation=(
                            "Ajouter une alternative textuelle "
                            "adaptée à l'information portée "
                            "par l'image."
                        ),
                        evidence=evidence,
                    )
                )

            elif (
                analysis.information_bearing
                is False
            ):
                decorative_images += 1

            else:
                needs_review += 1

                findings.append(
                    Finding(
                        element=self._element_identifier(
                            element,
                            index,
                        ),
                        message=(
                            analysis.explanation
                            or (
                                "L'analyse automatique ne permet "
                                "pas de déterminer si l'image "
                                "est porteuse d'information."
                            )
                        ),
                        recommendation=(
                            "Effectuer une vérification humaine "
                            "du rôle de l'image."
                        ),
                        evidence=evidence,
                    )
                )

        #
        # Priorité des statuts :
        #
        # FAIL : une non-conformité a été prouvée.
        # ERROR : aucune non-conformité certaine, mais une analyse a échoué.
        # NEEDS_REVIEW : certains cas restent indécidables.
        # PASS : tous les éléments évaluables sont satisfaisants.
        #
        if failed_images:
            status = TestStatus.FAIL

        elif errors:
            status = TestStatus.ERROR

        elif needs_review:
            status = TestStatus.NEEDS_REVIEW

        else:
            status = TestStatus.PASS

        summary = (
            f"{len(elements)} élément(s) analysé(s) : "
            f"{valid_images} avec alternative, "
            f"{decorative_images} image(s) considérée(s) décorative(s), "
            f"{failed_images} non conforme(s), "
            f"{needs_review} à vérifier, "
            f"{errors} erreur(s)."
        )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=len(elements),
            metadata={
                "valid_images": valid_images,
                "decorative_images": (
                    decorative_images
                ),
                "failed_images": failed_images,
                "needs_review": needs_review,
                "errors": errors,
                "analysis_method": (
                    "DOM + VLM + LLM"
                    if analyzer is not None
                    else "DOM"
                ),
            },
        )

    @staticmethod
    def _get_alternative_evidence(
        image: Tag,
        soup: BeautifulSoup,
        attributes: tuple[str, ...],
    ) -> list[str]:
        evidence: list[str] = []

        if (
            "aria-labelledby"
            in attributes
        ):
            labelledby_valid, _ = (
                get_labelledby_text(
                    image,
                    soup,
                )
            )

            if labelledby_valid:
                evidence.append(
                    "aria-labelledby"
                )

        for attribute in attributes:
            if (
                attribute
                == "aria-labelledby"
            ):
                continue

            if (
                get_non_empty_attribute(
                    image,
                    attribute,
                )
                is not None
            ):
                evidence.append(
                    attribute
                )

        return evidence

    @staticmethod
    def _get_base_dir(
        context: AuditContext,
    ) -> Path | None:
        if context.html_path is None:
            return None

        return context.html_path.parent

    @staticmethod
    def _element_identifier(
        element: Tag,
        index: int,
    ) -> str:
        element_id = element.get(
            "id"
        )

        if (
            isinstance(
                element_id,
                str,
            )
            and element_id.strip()
        ):
            return (
                f"{element.name}"
                f"#{element_id}"
            )

        if (
            element.name != "img"
            and element.get("role")
            == "img"
        ):
            return (
                f"[role='img']"
                f"[index={index}]"
            )

        return (
            f"img[index={index}]"
        )

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError(
                "Le test 1.1.1 nécessite un DOM HTML."
            )

        return context.dom


class Test112:
    """
    RGAA 1.1.2

    Vérifie les alternatives textuelles des zones area.
    """

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
        soup = self._get_dom(
            context
        )

        areas = list(
            soup.find_all("area")
        )

        if not areas:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucune zone réactive area détectée."
                ),
                tested_elements=0,
            )

        findings: list[Finding] = []

        valid_areas = 0
        needs_review = 0

        for index, area in enumerate(
            areas
        ):
            evidence = [
                attribute
                for attribute in (
                    "aria-label",
                    "alt",
                )
                if (
                    get_non_empty_attribute(
                        area,
                        attribute,
                    )
                    is not None
                )
            ]

            if evidence:
                valid_areas += 1
                continue

            #
            # Le caractère porteur d'information d'une zone area
            # dépend de la carte image associée.
            # Sans analyse complète de la carte, on ne transforme
            # pas automatiquement l'absence d'alt en FAIL.
            #
            needs_review += 1

            findings.append(
                Finding(
                    element=f"area[index={index}]",
                    message=(
                        "Aucune alternative textuelle n'a été "
                        "détectée. Le rôle informationnel de "
                        "cette zone doit être vérifié."
                    ),
                    recommendation=(
                        "Si la zone est porteuse d'information, "
                        "ajouter aria-label ou alt."
                    ),
                    evidence={
                        "attributes": dict(
                            area.attrs
                        ),
                        "information_bearing": (
                            "unknown"
                        ),
                    },
                )
            )

        status = (
            TestStatus.NEEDS_REVIEW
            if needs_review
            else TestStatus.PASS
        )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{valid_areas} zone(s) avec alternative, "
                f"{needs_review} zone(s) à vérifier."
            ),
            findings=findings,
            tested_elements=len(areas),
            metadata={
                "valid_areas": valid_areas,
                "needs_review": needs_review,
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
            raise ValueError(
                "Le test 1.1.2 nécessite un DOM HTML."
            )

        return context.dom


class Test113:
    """
    RGAA 1.1.3

    Vérifie l'alternative textuelle des boutons input[type=image].
    """

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
        soup = self._get_dom(
            context
        )

        image_inputs = [
            element
            for element in soup.find_all(
                "input"
            )
            if (
                str(
                    element.get(
                        "type",
                        "text",
                    )
                ).lower()
                == "image"
            )
        ]

        if not image_inputs:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun input[type=image] détecté."
                ),
                tested_elements=0,
            )

        findings: list[Finding] = []

        valid_inputs = 0

        for index, image_input in enumerate(
            image_inputs
        ):
            evidence = (
                self._get_alternative_evidence(
                    image_input,
                    soup,
                )
            )

            if evidence:
                valid_inputs += 1
                continue

            findings.append(
                Finding(
                    element=(
                        "input[type='image']"
                        f"[index={index}]"
                    ),
                    message=(
                        "Aucune alternative textuelle "
                        "valide n'a été détectée."
                    ),
                    recommendation=(
                        "Ajouter aria-labelledby, aria-label, "
                        "alt ou title avec une alternative "
                        "permettant d'identifier le bouton."
                    ),
                    evidence={
                        "attributes": dict(
                            image_input.attrs
                        ),
                        "detected_alternatives": (
                            evidence
                        ),
                    },
                )
            )

        status = (
            TestStatus.FAIL
            if findings
            else TestStatus.PASS
        )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{valid_inputs} bouton(s) image avec alternative, "
                f"{len(findings)} sans alternative."
            ),
            findings=findings,
            tested_elements=len(
                image_inputs
            ),
            metadata={
                "valid_inputs": valid_inputs,
                "invalid_inputs": len(
                    findings
                ),
            },
        )

    @staticmethod
    def _get_alternative_evidence(
        image_input: Tag,
        soup: BeautifulSoup,
    ) -> list[str]:
        evidence: list[str] = []

        labelledby_valid, _ = (
            get_labelledby_text(
                image_input,
                soup,
            )
        )

        if labelledby_valid:
            evidence.append(
                "aria-labelledby"
            )

        for attribute in (
            "aria-label",
            "alt",
            "title",
        ):
            if (
                get_non_empty_attribute(
                    image_input,
                    attribute,
                )
                is not None
            ):
                evidence.append(
                    attribute
                )

        return evidence

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError(
                "Le test 1.1.3 nécessite un DOM HTML."
            )

        return context.dom
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import (
    DescriptionAnalysis,
)
from accessi_code.analysis.images import (
    extract_images,
    get_images_with_detailed_descriptions,
)
from accessi_code.models.audit_context import (
    AuditContext,
)
from accessi_code.models.capabilities import (
    Capability,
)
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)


class Test171:
    """
    RGAA 1.7.1

    Vérifie la pertinence des descriptions détaillées
    associées aux images.
    """

    test_id = "1.7.1"
    criterion_id = "1.7"

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

        images = (
            get_images_with_detailed_descriptions(
                extract_images(
                    soup,
                    base_dir=self._get_base_dir(
                        context
                    ),
                )
            )
        )

        if not images:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucune image avec description "
                    "détaillée détectée."
                ),
                tested_elements=0,
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

        relevant = 0
        irrelevant = 0
        needs_review = 0
        errors = 0

        for image in images:
            for description in (
                image.descriptions
            ):
                evidence: dict[str, Any] = {
                    "src": image.src,
                    "description_source": (
                        description.source
                    ),
                    "description_reference": (
                        description.reference
                    ),
                    "description": (
                        description.content
                    ),
                }

                if not description.available:
                    needs_review += 1

                    findings.append(
                        Finding(
                            element=(
                                f"img[index={image.index}]"
                            ),
                            message=(
                                "La description détaillée "
                                "est inaccessible ou vide."
                            ),
                            recommendation=(
                                "Rendre la description accessible "
                                "puis vérifier sa pertinence."
                            ),
                            evidence={
                                **evidence,
                                "error": description.error,
                            },
                        )
                    )

                    continue

                if analyzer is None:
                    needs_review += 1

                    findings.append(
                        Finding(
                            element=(
                                f"img[index={image.index}]"
                            ),
                            message=(
                                "La description existe mais "
                                "sa pertinence n'a pas été évaluée."
                            ),
                            recommendation=(
                                "Effectuer une vérification humaine "
                                "ou utiliser le service d'analyse IA."
                            ),
                            evidence=evidence,
                        )
                    )

                    continue

                try:
                    analysis = await analyzer.analyze(
                        image,
                        description,
                    )

                    if not isinstance(
                        analysis,
                        DescriptionAnalysis,
                    ):
                        raise TypeError(
                            "L'analyseur doit retourner "
                            "un DescriptionAnalysis."
                        )

                except Exception as error:
                    errors += 1

                    findings.append(
                        Finding(
                            element=(
                                f"img[index={image.index}]"
                            ),
                            message=(
                                "L'analyse de la description "
                                "détaillée a échoué."
                            ),
                            recommendation=(
                                "Relancer l'analyse ou effectuer "
                                "une vérification humaine."
                            ),
                            evidence={
                                **evidence,
                                "error": str(error),
                            },
                        )
                    )

                    continue

                evidence["analysis"] = asdict(
                    analysis
                )

                if analysis.relevant is True:
                    relevant += 1

                elif analysis.relevant is False:
                    irrelevant += 1

                    findings.append(
                        Finding(
                            element=(
                                f"img[index={image.index}]"
                            ),
                            message=(
                                analysis.explanation
                                or (
                                    "La description détaillée "
                                    "n'est pas pertinente."
                                )
                            ),
                            recommendation=(
                                "Corriger ou compléter la description "
                                "afin qu'elle restitue les informations "
                                "importantes portées par l'image."
                            ),
                            evidence=evidence,
                        )
                    )

                else:
                    needs_review += 1

                    findings.append(
                        Finding(
                            element=(
                                f"img[index={image.index}]"
                            ),
                            message=(
                                analysis.explanation
                                or (
                                    "La pertinence de la description "
                                    "ne peut pas être déterminée."
                                )
                            ),
                            recommendation=(
                                "Effectuer une vérification humaine."
                            ),
                            evidence=evidence,
                        )
                    )

        if irrelevant:
            status = TestStatus.FAIL

        elif errors:
            status = TestStatus.ERROR

        elif needs_review:
            status = TestStatus.NEEDS_REVIEW

        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(images)} image(s) concernée(s) : "
                f"{relevant} description(s) pertinente(s), "
                f"{irrelevant} non pertinente(s), "
                f"{needs_review} à vérifier, "
                f"{errors} erreur(s)."
            ),
            findings=findings,
            tested_elements=len(
                images
            ),
            metadata={
                "relevant_descriptions": relevant,
                "irrelevant_descriptions": (
                    irrelevant
                ),
                "needs_review": needs_review,
                "errors": errors,
                "analysis_method": (
                    "VLM + LLM"
                    if analyzer is not None
                    else "manual_review_required"
                ),
            },
        )

    @staticmethod
    def _get_base_dir(
        context: AuditContext,
    ) -> Path | None:
        if context.html_path is None:
            return None

        return context.html_path.parent

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError(
                "Le test 1.7.1 nécessite un DOM HTML."
            )

        return context.dom
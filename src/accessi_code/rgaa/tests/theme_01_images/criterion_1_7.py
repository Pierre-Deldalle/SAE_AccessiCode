from __future__ import annotations

from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import (
    DescriptionAnalysis,
    ImageRoleAnalysis,
)
from accessi_code.analysis.images import (
    extract_images,
    get_images_with_description_candidates,
    make_local_resource_loader,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test171(RGAATest):
    test_id = "1.7.1"
    criterion_id = "1.7"

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

        base_dir = context.html_path.parent if context.html_path else None

        loader = make_local_resource_loader(base_dir) if base_dir is not None else None

        images = get_images_with_description_candidates(
            extract_images(
                soup,
                base_dir=base_dir,
                resource_loader=loader,
            )
        )

        if not images:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun candidat à une description détaillée détecté.",
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
        non_detailed = 0
        outside_scope = 0
        review = 0
        errors = 0
        detailed_descriptions = 0

        for image in images:
            if analyzer is None:
                review += 1
                continue

            try:
                role = await analyzer.analyze_information_role(image)

                if not isinstance(
                    role,
                    ImageRoleAnalysis,
                ):
                    raise TypeError("ImageRoleAnalysis attendu.")

            except Exception as error:
                errors += 1

                findings.append(
                    Finding(
                        element=f"img[index={image.index}]",
                        message="L'analyse du rôle de l'image a échoué.",
                        evidence={
                            "error": str(error),
                        },
                    )
                )
                continue

            # Une réponse IA à faible confiance ne doit jamais produire
            # un verdict RGAA ferme.
            if role.confidence == "low":
                review += 1

                findings.append(
                    Finding(
                        element=f"img[index={image.index}]",
                        message=(role.explanation or "Le rôle informationnel de l'image reste incertain."),
                        recommendation=("Vérifier manuellement le rôle de l'image."),
                        evidence={
                            "analysis_confidence": role.confidence,
                            "uncertainties": role.uncertainties,
                        },
                    )
                )
                continue

            if role.information_bearing is False:
                outside_scope += 1
                continue

            if role.information_bearing is None:
                review += 1

                findings.append(
                    Finding(
                        element=f"img[index={image.index}]",
                        message=(role.explanation or "Le rôle informationnel de l'image reste incertain."),
                        recommendation=("Vérifier manuellement le rôle de l'image."),
                        evidence={
                            "analysis_confidence": role.confidence,
                            "uncertainties": role.uncertainties,
                        },
                    )
                )
                continue

            for description in image.descriptions:
                if not description.available:
                    review += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message=("Un mécanisme de description existe mais son contenu n'est pas accessible."),
                            evidence={
                                "source": description.source,
                                "reference": description.reference,
                                "error": description.error,
                            },
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
                        raise TypeError("DescriptionAnalysis attendu.")

                except Exception as error:
                    errors += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message="L'analyse de la description a échoué.",
                            evidence={
                                "error": str(error),
                            },
                        )
                    )
                    continue

                evidence = {
                    "source": description.source,
                    "reference": description.reference,
                    "description": description.content,
                    "analysis": asdict(analysis),
                }

                # Même garde-fou pour la décision sur la description.
                if analysis.confidence == "low":
                    review += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message=(
                                analysis.explanation
                                or ("La description détaillée n'a pas pu être évaluée avec une confiance suffisante.")
                            ),
                            recommendation=("Vérifier manuellement la pertinence de la description détaillée."),
                            evidence=evidence,
                        )
                    )
                    continue

                if analysis.is_detailed_description is False:
                    non_detailed += 1
                    continue

                if analysis.is_detailed_description is None:
                    review += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message=("La nature détaillée de la description n'a pas pu être déterminée."),
                            recommendation=("Vérifier manuellement si ce contenu constitue une description détaillée."),
                            evidence=evidence,
                        )
                    )
                    continue

                detailed_descriptions += 1

                if analysis.relevant is True:
                    relevant += 1

                elif analysis.relevant is False:
                    irrelevant += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message=(analysis.explanation or ("La description détaillée n'est pas pertinente.")),
                            recommendation=("Compléter ou corriger la description."),
                            evidence=evidence,
                        )
                    )

                else:
                    review += 1

                    findings.append(
                        Finding(
                            element=f"img[index={image.index}]",
                            message=(
                                analysis.explanation
                                or ("La pertinence de la description détaillée n'a pas pu être déterminée.")
                            ),
                            recommendation=("Vérifier manuellement la pertinence de la description détaillée."),
                            evidence=evidence,
                        )
                    )

        if irrelevant:
            status = TestStatus.FAIL
        elif errors:
            status = TestStatus.ERROR
        elif review:
            status = TestStatus.NEEDS_REVIEW
        elif detailed_descriptions == 0:
            status = TestStatus.NOT_APPLICABLE
        else:
            status = TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (
                f"{detailed_descriptions} description(s) détaillée(s) : "
                f"{relevant} pertinente(s), "
                f"{irrelevant} non pertinente(s), "
                f"{review} à vérifier."
            ),
            findings=findings,
            tested_elements=detailed_descriptions,
            metadata={
                "candidate_images": len(images),
                "outside_scope_images": outside_scope,
                "non_detailed_candidates": non_detailed,
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
            raise ValueError("Le test 1.7.1 nécessite un DOM.")

        return context.dom

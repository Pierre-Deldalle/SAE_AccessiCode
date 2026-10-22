from __future__ import annotations

from typing import Any
from dataclasses import asdict

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test891(RGAATest):
    """Test 8.9.1 - Utilisation appropriée des balises sémantiques (pas uniquement pour présentation)."""

    test_id = "8.9.1"
    criterion_id = "8.9"

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
        """
        Exécute le test 8.9.1 : vérifie que les balises ne sont pas utilisées uniquement à des fins de présentation.

        Vérifie que les balises sémantiques (à l'exception de <div>, <span> et <table>) ne sont pas utilisées
        uniquement à des fins de présentation, sauf si justifiées par un role="presentation".
        """
        # Vérifier que le DOM est disponible
        if not hasattr(context, 'dom') or context.dom is None:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.ERROR,
                summary="Le DOM n'est pas disponible.",
                tested_elements=0,
            )

        # Vérifier si un service d'analyse de présentation sémantique est disponible
        if services and getattr(services, 'semantic_presentation_analyzer', None) is not None:
            analyzer = services.semantic_presentation_analyzer

            try:
                # Utiliser l'analyseur pour détecter l'utilisation inappropriée de balises sémantiques à des fins de présentation
                analysis_result = await analyzer.analyze_semantic_presentation(
                    context.dom,
                    context.html_source if hasattr(context, 'html_source') else None
                )

                # Vérifier le niveau de confiance de l'analyse
                if hasattr(analysis_result, 'confidence') and analysis_result.confidence == "low":
                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.NEEDS_REVIEW,
                        summary=getattr(analysis_result, 'explanation',
                                      "L'analyse automatique de l'utilisation sémantique des balises n'est pas suffisamment fiable."),
                        tested_elements=getattr(analysis_result, 'total_elements_checked', 0),
                        findings=self._convert_findings(getattr(analysis_result, 'findings', [])),
                        metadata=getattr(analysis_result, 'metadata', {})
                    )

                # S'il y a des violations (balises sémantiques utilisées pour présentation sans justification)
                
                if getattr(analysis_result, "has_violations", False):
                    findings = self._convert_findings(
                        getattr(analysis_result, "findings", [])
                    )

                    # Un FAIL exige des anomalies identifiables
                    # et des recommandations exploitables.
                    valid_findings = [
                        finding
                        for finding in findings
                        if isinstance(finding.element, str)
                        and finding.element.strip()
                        and finding.element.strip().lower() != "unknown"
                        and isinstance(finding.message, str)
                        and finding.message.strip()
                        and isinstance(finding.recommendation, str)
                        and finding.recommendation.strip()
                    ]

                    if not findings or len(valid_findings) != len(findings):
                        return TestResult(
                            test_id=self.test_id,
                            criterion_id=self.criterion_id,
                            status=TestStatus.NEEDS_REVIEW,
                            summary=(
                                "Une utilisation potentiellement incorrecte "
                                "des balises sémantiques a été signalée, "
                                "mais l'analyse ne fournit pas une anomalie "
                                "précise et une correction pour chaque élément."
                            ),
                            tested_elements=getattr(
                                analysis_result,
                                "total_elements_checked",
                                0,
                            ),
                            findings=valid_findings,
                            metadata=getattr(
                                analysis_result, "metadata", {}
                            ),
                        )

                    details = " ".join(
                        f"{finding.element} : {finding.message} "
                        f"Correction : {finding.recommendation}"
                        for finding in valid_findings
                    )

                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.FAIL,
                        summary=(
                            f"{len(valid_findings)} utilisation(s) "
                            f"sémantique(s) incorrecte(s) détectée(s). "
                            f"{details}"
                        ),
                        tested_elements=getattr(
                            analysis_result,
                            "total_elements_checked",
                            0,
                        ),
                        findings=valid_findings,
                        metadata=getattr(
                            analysis_result, "metadata", {}
                        ),
                    )

                else:
                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.PASS,
                        summary=(
                            "L'analyse automatique n'a pas détecté "
                            "d'utilisation inappropriée des balises "
                            "sémantiques."
                        ),
                        tested_elements=getattr(
                            analysis_result,
                            "total_elements_checked",
                            0,
                        ),
                        findings=[],
                        metadata=getattr(
                            analysis_result, "metadata", {}
                        ),
                    )
            
            except ValueError as error:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NEEDS_REVIEW,
                    summary=(
                        "La réponse de l'IA est incomplète ou invalide. "
                        "Vérification manuelle de l'utilisation "
                        "sémantique des balises nécessaire."
                    ),
                    tested_elements=0,
                    metadata={"analysis_error": str(error)},
                )

            except Exception as error:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.ERROR,
                    summary=f"L'analyse de l'utilisation sémantique des balises a échoué : {str(error)}",
                    tested_elements=0,
                    metadata={"error": str(error)}
                )
        else:
            # Pas de service d'analyse de présentation sémantique disponible
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Service d'analyse de l'utilisation sémantique des balises non disponible.",
                tested_elements=0,
            )

    def _convert_findings(self, findings):
        """
        Convertit les findings de l'analyseur en objets Finding du projet.
        Cette méthode doit être adaptée selon le format réel retourné par l'analyseur.
        """
        converted_findings = []
        for finding in findings:
            if isinstance(finding, dict):
                converted_findings.append(
                    Finding(
                        element=finding.get('element', 'unknown'),
                        message=finding.get('message', ''),
                        recommendation=finding.get('recommendation'),
                        evidence=finding.get('evidence', {})
                    )
                )
            else:
                # Si c'est déjà un objet Finding ou un format similaire
                converted_findings.append(finding)
        return converted_findings
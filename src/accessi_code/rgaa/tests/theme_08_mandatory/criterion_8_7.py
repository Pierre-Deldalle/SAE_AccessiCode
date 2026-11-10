from __future__ import annotations

from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.tests.theme_08_mandatory._ai_findings import (
    convert_findings,
    fail_summary,
    is_precise,
    with_default_recommendation,
)

# Recommandation utilisée si l'analyseur n'en fournit pas.
DEFAULT_RECOMMENDATION = (
    "Ajouter un attribut lang avec le code de langue approprié sur le passage concerné."
)


class Test871(RGAATest):
    """Test 8.7.1 - Indication des changements de langue."""

    test_id = "8.7.1"
    criterion_id = "8.7"

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
        Exécute le test 8.7.1 : indication des changements de langue.

        Vérifie que chaque texte écrit dans une langue différente de la langue par défaut
        possède une indication de langue (sur l'élément contenant le texte ou un parent),
        hors cas particuliers (noms propres, mots du dictionnaire, etc.).
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

        # Vérifier si un service d'analyse de langue est disponible
        if services and getattr(services, 'language_change_analyzer', None) is not None:
            analyzer = services.language_change_analyzer

            try:
                # Utiliser l'analyseur pour détecter les changements de langue manquants
                analysis_result = await analyzer.analyze_language_changes(
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
                                      "La détection des changements de langue nécessite une vérification manuelle."),
                        tested_elements=getattr(analysis_result, 'total_elements_checked', 0),
                        findings=self._convert_findings(getattr(analysis_result, 'findings', [])),
                        metadata=getattr(analysis_result, 'metadata', {})
                    )

                # Retourner le résultat basé sur l'analyse

                if getattr(analysis_result, "has_violations", False):
                    findings = self._convert_findings(
                        getattr(analysis_result, "findings", [])
                    )

                    # Un FAIL doit être justifié par des anomalies précises.
                    findings = with_default_recommendation(findings, DEFAULT_RECOMMENDATION)
                    if not findings or not all(is_precise(finding) for finding in findings):
                        return TestResult(
                            test_id=self.test_id,
                            criterion_id=self.criterion_id,
                            status=TestStatus.NEEDS_REVIEW,
                            summary=(
                                "Une anomalie de changement de langue a été "
                                "signalée, mais les preuves sont insuffisantes "
                                "pour établir une non-conformité précise."
                            ),
                            tested_elements=getattr(
                                analysis_result, "total_elements_checked", 0
                            ),
                            findings=findings,
                            metadata=getattr(analysis_result, "metadata", {}),
                        )

                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.FAIL,
                        summary=fail_summary(
                            analysis_result,
                            f"{len(findings)} passage(s) avec une indication de langue manquante ou inappropriée.",
                            findings,
                        ),
                        tested_elements=getattr(
                            analysis_result, "total_elements_checked", 0
                        ),
                        findings=findings,
                        metadata=getattr(analysis_result, "metadata", {}),
                    )
                else:
                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.PASS,
                        summary=getattr(analysis_result, 'explanation',
                                      "L'analyse automatique n'a pas signalé de code de langue invalide ou inadapté."),
                        tested_elements=getattr(analysis_result, 'total_elements_checked', 0),
                        findings=[],  # Pas d'erreurs
                        metadata=getattr(analysis_result, 'metadata', {})
                    )

            except Exception as error:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.ERROR,
                    summary=f"L'analyse des changements de langue a échoué : {str(error)}",
                    tested_elements=0,
                    metadata={"error": str(error)}
                )
        else:
            # Pas de service d'analyse de langue disponible
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Service d'analyse des changements de langue non disponible.",
                tested_elements=0,
            )

    def _convert_findings(self, findings):
        """Convertit les observations de l'analyseur en objets Finding du projet."""
        return convert_findings(findings)

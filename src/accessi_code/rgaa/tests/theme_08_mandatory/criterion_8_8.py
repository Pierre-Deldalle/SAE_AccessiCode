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
    "Utiliser un code de langue valide (ISO 639) et pertinent pour le contenu du passage."
)


class Test881(RGAATest):
    """Test 8.8.1 - Validité et pertinence des codes de langue des changements de langue."""

    test_id = "8.8.1"
    criterion_id = "8.8"

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
        Exécute le test 8.8.1 : validité et pertinence des codes de langue des changements de langue.

        Pour chaque passage de texte identifié comme étant en langue étrangère (via le test 8.7.1),
        vérifie que :
        - Le code de langue utilisé est valide (format ISO correct)
        - Le code de langue utilisé est pertinent par rapport au contenu
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

        # Vérifier que le DOM est disponible
        if not hasattr(context, 'dom') or context.dom is None:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.ERROR,
                summary="Le DOM n'est pas disponible.",
                tested_elements=0,
            )

        # AJOUT : vérifier s'il existe des déclarations
        # de changement de langue dans le HTML.
        language_declarations = [
            element
            for element in context.dom.find_all(True)
            if element.name != "html"
            and (
                element.has_attr("lang")
                or element.has_attr("xml:lang")
            )
        ]

        if not language_declarations:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune déclaration de changement de langue à vérifier.",
                tested_elements=0,
            )

        # Vérifier si un service d'analyse de langue pour les changements est disponible
        if services and getattr(services, 'language_validity_analyzer', None) is not None:
            analyzer = services.language_validity_analyzer

            try:
                # Utiliser l'analyseur pour vérifier la validité et la pertinence des codes de langue
                # utilisés pour les changements de langue
                analysis_result = await analyzer.analyze_language_validity(
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
                                      "La validité ou la pertinence des codes de langue nécessite une vérification manuelle."),
                        tested_elements=getattr(analysis_result, 'total_changes_checked', 0),
                        findings=self._convert_findings(getattr(analysis_result, 'findings', [])),
                        metadata=getattr(analysis_result, 'metadata', {})
                    )

                # S'il y a des erreurs (codes de langue invalides ou non pertinents)
                if getattr(analysis_result, "has_errors", False):
                    findings = self._convert_findings(
                        getattr(analysis_result, "findings", [])
                    )

                    # Ne pas déclarer FAIL sans anomalie précise.
                    findings = with_default_recommendation(findings, DEFAULT_RECOMMENDATION)
                    if not findings or not all(is_precise(finding) for finding in findings):
                        return TestResult(
                            test_id=self.test_id,
                            criterion_id=self.criterion_id,
                            status=TestStatus.NEEDS_REVIEW,
                            summary=(
                                "Des codes de langue potentiellement invalides "
                                "ou inadaptés ont été signalés, mais les "
                                "anomalies ne sont pas suffisamment détaillées."
                            ),
                            tested_elements=getattr(
                                analysis_result, "total_changes_checked", 0
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
                            f"{len(findings)} anomalie(s) de code de langue détectée(s).",
                            findings,
                        ),
                        tested_elements=getattr(
                            analysis_result, "total_changes_checked", 0
                        ),
                        findings=findings,
                        metadata=getattr(analysis_result, "metadata", {}),
                    )
                else:
                    # Tous les codes de langue sont valides et pertinents
                    return TestResult(
                        test_id=self.test_id,
                        criterion_id=self.criterion_id,
                        status=TestStatus.PASS,
                        summary=getattr(analysis_result, 'explanation',
                                      "L'analyse automatique n'a pas signalé de code de langue invalide ou inadapté."),
                        tested_elements=getattr(analysis_result, 'total_changes_checked', 0),
                        findings=[],  # Pas d'erreurs
                        metadata=getattr(analysis_result, 'metadata', {})
                    )

            except Exception as error:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.ERROR,
                    summary=f"L'analyse de validité/pertinence des codes de langue a échoué : {str(error)}",
                    tested_elements=0,
                    metadata={"error": str(error)}
                )
        else:
            # Pas de service d'analyse de validité des codes de langue disponible
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Service d'analyse de validité des codes de langue non disponible.",
                tested_elements=0,
            )

    def _convert_findings(self, findings):
        """Convertit les observations de l'analyseur en objets Finding du projet."""
        return convert_findings(findings)

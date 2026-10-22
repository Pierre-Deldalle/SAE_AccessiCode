from __future__ import annotations

from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test821(RGAATest):
    """Test 8.2.1 - Validation du code source selon le type de document."""

    test_id = "8.2.1"
    criterion_id = "8.2"

    required_capabilities = frozenset(
        {
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """
        Exécute le test 8.2.1 : validation du code source HTML.

        Vérifie que le code source généré est valide selon le type de document spécifié :
        - Les balises, attributs et valeurs d'attributs respectent les règles d'écriture
        - L'imbrication des balises est conforme
        - L'ouverture et la fermeture des balises sont conformes
        - Les valeurs d'attribut id sont uniques dans la page
        - Les attributs ne sont pas doublés sur un même élément
        """
        # Utiliser le service de validation HTML si disponible
        if services and getattr(services, 'html_validator', None) is not None:
            validator = services.html_validator
            validation_result = await validator.validate_html(context.html_source)

            if validation_result.is_valid:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.PASS,
                    summary="Le code source HTML est valide selon le type de document spécifié.",
                    tested_elements=1,
                )
            else:
                # Construire un message d'erreur détaillé
                errors = validation_result.errors
                error_count = len(errors)

                # Limiter le nombre d'erreurs affichées pour éviter un message trop long
                max_errors_to_show = 5
                displayed_errors = errors[:max_errors_to_show]

                error_messages = []
                for error in displayed_errors:
                    error_messages.append(f"Ligne {error.line}: {error.message}")

                summary = f"Le code source HTML contient {error_count} erreur(s) de validation :\n" + "\n".join(error_messages)
                if error_count > max_errors_to_show:
                    summary += f"\n... et {error_count - max_errors_to_show} autre(s) erreur(s)."

                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.FAIL,
                    summary=summary,
                    tested_elements=1,
                )
        else:
            # Si pas de service de validation disponible, retourner NOT_TESTED
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Service de validation HTML non disponible.",
                tested_elements=0,
            )
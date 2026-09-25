from __future__ import annotations

import argparse
import asyncio
from typing import Any

from debug_context import build_debug_context

from accessi_code.models.result import Finding, TestResult
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.service.audit_service import AuditService
from accessi_code.service.audit_services import AuditServices
from accessi_code.service.default_services import (
    build_default_audit_services,
)
from accessi_code.config import settings


def print_separator(
    title: str,
) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def print_finding(
    finding: Finding,
) -> None:
    print(
        f"      Élément : {finding.element}"
    )

    print(
        f"      Message : {finding.message}"
    )

    if finding.recommendation:
        print(
            f"      Recommandation : "
            f"{finding.recommendation}"
        )

    if finding.evidence:
        print(
            f"      Preuves : "
            f"{finding.evidence}"
        )


def print_test_result(
    result: TestResult,
) -> None:
    print(
        f"  {result.test_id:<8} "
        f"{result.status.value:<16} "
        f"{result.summary}"
    )

    if result.tested_elements:
        print(
            f"      Éléments testés : "
            f"{result.tested_elements}"
        )

    for finding in result.findings:
        print_finding(
            finding
        )

    if result.metadata:
        print(
            f"      Métadonnées : "
            f"{result.metadata}"
        )


def build_services(
    *,
    use_ai: bool,
) -> AuditServices:
    """
    Construit les services utilisés par l'audit.

    Le mode sans IA reste disponible pour vérifier les vrais tests RGAA
    sans dépendre d'Ollama.
    """
    if not use_ai:
        return AuditServices()

    return build_default_audit_services(
        ollama_host=settings.OLLAMA_HOST,
        llm_model=settings.LLM_MODEL,
        vlm_model=settings.VLM_MODEL,
    )


async def run_debug(
    *,
    use_ai: bool,
) -> None:
    # ---------------------------------------------------------
    # US 0.0.1 : construction du vrai AuditContext
    # ---------------------------------------------------------

    context = build_debug_context()

    print_separator(
        "AUDIT CONTEXT"
    )

    print(
        f"Audit ID  : {context.audit_id}"
    )

    print(
        f"Workspace : {context.workspace_path}"
    )

    print(
        f"HTML      : {context.html_path}"
    )

    print(
        f"DOCTYPE   : {context.doctype}"
    )

    print()
    print("Capabilities :")

    for capability in sorted(
        context.get_capabilities(),
        key=lambda item: item.value,
    ):
        print(
            f"- {capability.value}"
        )

    # ---------------------------------------------------------
    # US 0.0.2 : vrais tests RGAA
    # ---------------------------------------------------------

    registry = build_default_registry()

    print_separator(
        "REGISTRE RGAA"
    )

    print(
        f"{len(registry)} test(s) enregistré(s)"
    )

    for test in registry:
        required = sorted(
            capability.value
            for capability
            in test.required_capabilities
        )

        optional = sorted(
            capability.value
            for capability
            in test.optional_capabilities
        )

        print(
            f"- {test.test_id}"
            f" | critère {test.criterion_id}"
            f" | requis={required}"
            f" | optionnel={optional}"
        )

    # ---------------------------------------------------------
    # Services IA
    # ---------------------------------------------------------

    print_separator(
        "SERVICES"
    )

    print(
        f"IA activée : "
        f"{'oui' if use_ai else 'non'}"
    )

    services = build_services(
        use_ai=use_ai
    )

    print(
        "Image analyzer : "
        f"{type(services.image_analyzer).__name__}"
        if services.image_analyzer is not None
        else "Image analyzer : indisponible"
    )

    print(
        "Page analyzer  : "
        f"{type(services.page_analyzer).__name__}"
        if services.page_analyzer is not None
        else "Page analyzer  : indisponible"
    )

    # ---------------------------------------------------------
    # US 0.0.3 : moteur réel
    # ---------------------------------------------------------

    service = AuditService(
        registry=registry,
        services=services,
    )

    print_separator(
        "EXÉCUTION DE L'AUDIT"
    )

    print(
        "Exécution des tests..."
    )

    result = await service.audit(
        context
    )

    # ---------------------------------------------------------
    # Résultat global
    # ---------------------------------------------------------

    print_separator(
        "RÉSULTAT GLOBAL"
    )

    print(
        f"Statut : {result.status.value}"
    )

    stats = result.statistics

    print()
    print(
        f"Critères           : {stats.total_criteria}"
    )
    print(
        f"Tests              : {stats.total_tests}"
    )
    print(
        f"PASS               : {stats.passed_tests}"
    )
    print(
        f"FAIL               : {stats.failed_tests}"
    )
    print(
        f"NOT_APPLICABLE     : "
        f"{stats.not_applicable_tests}"
    )
    print(
        f"NOT_TESTED         : "
        f"{stats.not_tested_tests}"
    )
    print(
        f"NEEDS_REVIEW       : "
        f"{stats.needs_review_tests}"
    )
    print(
        f"ERROR              : "
        f"{stats.error_tests}"
    )

    # ---------------------------------------------------------
    # Résultats détaillés
    # ---------------------------------------------------------

    print_separator(
        "RÉSULTATS RGAA"
    )

    for criterion in result.criteria:
        print()
        print(
            f"Critère {criterion.criterion_id} "
            f"→ {criterion.status.value}"
        )

        print(
            f"  {criterion.summary}"
        )

        for test in criterion.tests:
            print_test_result(
                test
            )

    print_separator(
        "FIN DE L'AUDIT"
    )


def parse_arguments() -> Any:
    parser = argparse.ArgumentParser(
        description=(
            "Exécute les vrais tests RGAA AccessiCode "
            "sur test_files/basic_site."
        )
    )

    parser.add_argument(
        "--no-ai",
        action="store_true",
        help=(
            "Exécute les vrais tests RGAA sans "
            "les services Ollama."
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    asyncio.run(
        run_debug(
            use_ai=not arguments.no_ai,
        )
    )


if __name__ == "__main__":
    main()
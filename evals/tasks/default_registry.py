from __future__ import annotations

from accessi_code.ai.analyzers.page_analyzer import OllamaPageAnalyzer
from accessi_code.service.audit_services import AuditServices

from evals.tasks.registry import EvalTaskRegistry
from evals.tasks.title import TitleEvalTask


def build_default_eval_registry(
    services: AuditServices,
) -> EvalTaskRegistry:
    """
    Construit le registre des fonctionnalités IA évaluables.
    """
    if services.page_analyzer is None:
        raise RuntimeError(
            "Impossible de construire les évaluations de page : "
            "aucun page_analyzer n'est disponible."
        )

    if not isinstance(
        services.page_analyzer,
        OllamaPageAnalyzer,
    ):
        raise TypeError(
            "Le page_analyzer doit être une instance de OllamaPageAnalyzer."
        )

    registry = EvalTaskRegistry()

    registry.register(
        TitleEvalTask(
            page_analyzer=services.page_analyzer,
        )
    )

    return registry
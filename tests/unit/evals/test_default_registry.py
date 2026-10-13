import pytest

from accessi_code.ai.analyzers.page_analyzer import OllamaPageAnalyzer
from accessi_code.service.audit_services import AuditServices
from evals.tasks.default_registry import build_default_eval_registry
from evals.tasks.title import TitleEvalTask


def test_default_registry_registers_title_task():
    page_analyzer = OllamaPageAnalyzer(
        llm=object(),
    )

    services = AuditServices(
        page_analyzer=page_analyzer,
    )

    registry = build_default_eval_registry(
        services,
    )

    assert registry.names() == [
        "title",
    ]

    assert isinstance(
        registry.get("title"),
        TitleEvalTask,
    )


def test_default_registry_requires_page_analyzer():
    services = AuditServices(
        page_analyzer=None,
    )

    with pytest.raises(
        RuntimeError,
        match="aucun page_analyzer",
    ):
        build_default_eval_registry(
            services,
        )


def test_default_registry_rejects_wrong_page_analyzer_type():
    services = AuditServices(
        page_analyzer=object(),
    )

    with pytest.raises(
        TypeError,
        match="OllamaPageAnalyzer",
    ):
        build_default_eval_registry(
            services,
        )

from types import SimpleNamespace
from unittest.mock import AsyncMock

from accessi_code.ai.schemas import TitleAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_6 import (
    Test861 as RGAA861,
)
from accessi_code.service.audit_services import AuditServices


def analysis(
    relevant: bool | None,
    *,
    confidence: str = "high",
) -> TitleAnalysis:
    return TitleAnalysis(
        relevant=relevant,
        explanation="Analyse du titre simulée.",
        contradictions=[],
        uncertainties=[],
        confidence=confidence,
    )


def page_services(result=None, *, error: Exception | None = None):
    method = AsyncMock(side_effect=error) if error is not None else AsyncMock(return_value=result)
    analyzer = SimpleNamespace(analyze_title=method)
    return AuditServices(page_analyzer=analyzer), method


def page(title: str, heading: str = "Accueil", content: str = "Bienvenue") -> str:
    return (
        f"<html><head><title>{title}</title></head><body><main><h1>{heading}</h1><p>{content}</p></main></body></html>"
    )


def test_861_relevant_title_with_high_confidence_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Inscription au service", "Inscription au service", "Créez votre compte."))
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.PASS
    method.assert_awaited_once()
    title, heading, content = method.await_args.args
    assert title == "Inscription au service"
    assert heading == "Inscription au service"
    assert "Créez votre compte." in content


def test_861_irrelevant_title_with_high_confidence_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        page(
            "Recette de crêpes",
            "Réinitialiser son mot de passe",
            "Choisissez un nouveau mot de passe.",
        )
    )
    services, _ = page_services(analysis(False))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.FAIL
    assert result.findings[0].element == "title"


def test_861_missing_title_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body><h1>Accueil</h1><p>Bienvenue.</p></body></html>")

    result = run_rgaa(RGAA861(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE


def test_861_empty_title_fails_without_calling_ai(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<html><head><title>   </title></head><body><h1>Accueil</h1><p>Bienvenue.</p></body></html>"
    )
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.FAIL
    method.assert_not_awaited()


def test_861_without_page_analyzer_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Accueil"))

    result = run_rgaa(RGAA861(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_861_low_confidence_requires_review_even_when_relevant_is_true(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Accueil"))
    services, _ = page_services(analysis(True, confidence="low"))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_861_low_confidence_requires_review_even_when_relevant_is_false(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Recette de crêpes"))
    services, _ = page_services(analysis(False, confidence="low"))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_861_unknown_relevance_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Accueil"))
    services, _ = page_services(analysis(None, confidence="medium"))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_861_page_without_meaningful_content_requires_review_without_ai(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><head><title>Accueil</title></head><body></body></html>")
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.NEEDS_REVIEW
    method.assert_not_awaited()


def test_861_ai_error_is_reported(
    context_factory,
    run_rgaa,
):
    context = context_factory(page("Accueil"))
    services, _ = page_services(error=RuntimeError("LLM indisponible"))

    result = run_rgaa(RGAA861(), context, services)

    assert result.status == Status.ERROR

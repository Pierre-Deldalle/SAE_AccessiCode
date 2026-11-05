from types import SimpleNamespace
from unittest.mock import AsyncMock

from accessi_code.ai.schemas import LanguageAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_4 import (
    Test841 as RGAA841,
)
from accessi_code.service.audit_services import AuditServices


def analysis(
    relevant: bool | None,
    *,
    detected_language: str | None = "fr",
    confidence: str = "high",
) -> LanguageAnalysis:
    return LanguageAnalysis(
        relevant=relevant,
        detected_language=detected_language,
        explanation="Analyse de langue simulée.",
        uncertainties=[],
        confidence=confidence,
    )


def page_services(result=None, *, error: Exception | None = None):
    method = AsyncMock(side_effect=error) if error is not None else AsyncMock(return_value=result)
    analyzer = SimpleNamespace(analyze_language=method)
    return AuditServices(page_analyzer=analyzer), method


def test_841_matching_language_with_high_confidence_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><body>Bienvenue sur notre service.</body></html>')
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.PASS
    method.assert_awaited_once()
    lang, content = method.await_args.args
    assert lang == "fr"
    assert "Bienvenue" in content


def test_841_wrong_language_with_high_confidence_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><body>Welcome to our service.</body></html>')
    services, _ = page_services(analysis(False, detected_language="en"))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.FAIL
    assert result.findings[0].evidence["analysis"]["detected_language"] == "en"


def test_841_missing_default_language_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body>Bienvenue.</body></html>")

    result = run_rgaa(RGAA841(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE


def test_841_invalid_language_code_fails_without_calling_ai(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="123"><body>Bienvenue.</body></html>')
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.FAIL
    method.assert_not_awaited()


def test_841_regional_language_code_can_be_analyzed(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr-FR"><body>Bienvenue.</body></html>')
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.PASS
    assert method.await_args.args[0] == "fr-FR"


def test_841_xml_lang_can_be_used_when_lang_is_absent(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html xml:lang="fr"><body>Bienvenue.</body></html>')
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.PASS
    assert method.await_args.args[0] == "fr"


def test_841_without_page_analyzer_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><body>Bienvenue.</body></html>')

    result = run_rgaa(RGAA841(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_841_low_confidence_requires_review_even_with_boolean_verdict(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="en"><body>Bienvenue.</body></html>')
    services, _ = page_services(
        analysis(
            False,
            detected_language="fr",
            confidence="low",
        )
    )

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_841_unknown_relevance_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><body>Bienvenue.</body></html>')
    services, _ = page_services(analysis(None, confidence="medium"))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_841_empty_page_content_requires_review_without_calling_ai(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><head></head><body></body></html>')
    services, method = page_services(analysis(True))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.NEEDS_REVIEW
    method.assert_not_awaited()


def test_841_ai_error_is_reported(
    context_factory,
    run_rgaa,
):
    context = context_factory('<html lang="fr"><body>Bienvenue.</body></html>')
    services, _ = page_services(error=RuntimeError("LLM indisponible"))

    result = run_rgaa(RGAA841(), context, services)

    assert result.status == Status.ERROR

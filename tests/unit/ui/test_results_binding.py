"""Tests du pont interface -> moteur et du rendu des résultats (sans navigateur)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from accessi_code.models.audit_result import CriterionResult
from accessi_code.models.result import Finding, TestStatus
from accessi_code.models.result import TestResult as Result
from accessi_code.rgaa.themes import THEMES_BY_NUMBER
from accessi_code.service.audit_orchestrator import AuditRequestError
from accessi_code.service.theme_summary import ThemeState, ThemeSummary
from accessi_code.ui.audit_bridge import build_audit_request, run_audit_from_ui, uploaded_paths
from accessi_code.ui.results_view import SCORE_CSS, build_theme_detail, card_classes


def test_uploaded_paths_accepts_gradio_formats():
    assert uploaded_paths(None) == ()
    assert uploaded_paths("a.html") == (Path("a.html"),)
    assert uploaded_paths(["a.html", None, SimpleNamespace(name="b.css")]) == (Path("a.html"), Path("b.css"))


def test_build_audit_request_parses_labels_and_url():
    request = build_audit_request("  ", ["a.html"], ["1. Images", "6. Liens", "inconnu"])
    assert request.themes == {1, 6}
    assert request.url is None
    assert request.files == (Path("a.html"),)


class FakeOrchestrator:
    def __init__(self, error: Exception):
        self.error = error

    async def run(self, request, on_progress=None):
        raise self.error


@pytest.mark.asyncio
async def test_request_error_is_returned_as_message():
    outcome = await run_audit_from_ui(None, [], ["1. Images"], FakeOrchestrator(AuditRequestError("Importez un HTML")))
    assert outcome.error == "Importez un HTML"
    assert outcome.summaries == ()


@pytest.mark.asyncio
async def test_unexpected_error_does_not_crash_ui():
    outcome = await run_audit_from_ui(None, [], ["1. Images"], FakeOrchestrator(OSError("disque plein")))
    assert "disque plein" in outcome.error


def test_card_classes_score_and_states():
    theme = THEMES_BY_NUMBER[6]
    scored = ThemeSummary(theme, ThemeState.SCORED, score=81)
    assert "theme-score-81" in card_classes(scored)
    assert "theme-status-success" in card_classes(scored)

    review = ThemeSummary(theme, ThemeState.NEEDS_REVIEW)
    assert "theme-score-needs_review" in card_classes(review)
    assert "theme-status-review" in card_classes(review)

    # Toutes les classes utilisées ont une règle CSS générée.
    for state in ThemeState:
        summary = ThemeSummary(theme, state, score=0 if state == ThemeState.SCORED else None)
        score_class = next(c for c in card_classes(summary) if c.startswith("theme-score-") and c != "theme-score-word")
        assert f".{score_class} " in SCORE_CSS


def test_detail_lists_tests_findings_and_escapes_html():
    finding = Finding(
        element='<a href="/x">*clic*</a>',
        message="Lien sans intitulé $x$",
        recommendation="Ajouter un intitulé.",
    )
    test = Result("6.2.1", "6.2", TestStatus.FAIL, "1 lien vide", findings=[finding], tested_elements=3)
    review = Result("6.1.1", "6.1", TestStatus.NEEDS_REVIEW, "Pertinence à juger")
    summary = ThemeSummary(
        THEMES_BY_NUMBER[6],
        ThemeState.SCORED,
        score=0,
        criteria=(
            CriterionResult("6.1", TestStatus.NEEDS_REVIEW, "", [review]),
            CriterionResult("6.2", TestStatus.FAIL, "", [test]),
        ),
        criteria_counts={TestStatus.FAIL: 1, TestStatus.NEEDS_REVIEW: 1},
    )

    detail = build_theme_detail(summary)

    assert "Test 6.2.1" in detail and "Non conforme" in detail
    assert "Ajouter un intitulé." in detail
    assert "Contrôles à vérifier manuellement" in detail
    assert "<a href" not in detail  # HTML de la page auditée neutralisé.
    assert "$x$" not in detail  # Pas d'interprétation LaTeX.


def test_detail_for_not_implemented_theme_says_not_audited():
    detail = build_theme_detail(ThemeSummary(THEMES_BY_NUMBER[2], ThemeState.NOT_IMPLEMENTED))
    assert "pas encore de test automatisé" in detail
    assert "%" not in detail

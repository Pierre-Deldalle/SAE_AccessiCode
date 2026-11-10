"""Tests de la sélection des thématiques et de l'orchestration d'audit."""

from pathlib import Path

import pytest

from accessi_code.models.result import TestResult as Result
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import TestRegistry as Registry
from accessi_code.rgaa.themes import (
    filter_registry_by_themes,
    implemented_themes,
    parse_theme_label,
    theme_number,
)
from accessi_code.service.audit_orchestrator import (
    AuditOrchestrator,
    AuditRequest,
    AuditRequestError,
)
from accessi_code.service.audit_services import AuditServices


def make_test(test_id: str, criterion_id: str, status=TestStatus.PASS, error: Exception | None = None):
    class FakeTest(RGAATest):
        async def run(self, context, services=None):
            if error is not None:
                raise error
            return Result(test_id=test_id, criterion_id=criterion_id, status=status, summary="ok")

    FakeTest.test_id = test_id
    FakeTest.criterion_id = criterion_id
    return FakeTest()


def registry_factory():
    return Registry(
        [
            make_test("1.1.1", "1.1"),
            make_test("6.1.1", "6.1", TestStatus.NEEDS_REVIEW),
            make_test("6.2.1", "6.2", TestStatus.FAIL),
        ]
    )


@pytest.fixture
def html_file(tmp_path: Path) -> Path:
    path = tmp_path / "page.html"
    path.write_text("<!DOCTYPE html><html lang='fr'><body><p>Bonjour</p></body></html>", encoding="utf-8")
    return path


@pytest.fixture
def orchestrator(tmp_path: Path) -> AuditOrchestrator:
    return AuditOrchestrator(
        workspace_root=tmp_path / "workspace",
        registry_factory=registry_factory,
        services_factory=AuditServices,
    )


# --- Catalogue des thématiques -------------------------------------------


def test_theme_number_from_criterion():
    assert theme_number("6.1") == 6
    assert theme_number("11.1") == 11
    assert theme_number("14.1") is None
    assert theme_number("abc") is None


def test_parse_theme_label():
    assert parse_theme_label("6. Liens") == 6
    assert parse_theme_label("13. Consultation") == 13
    assert parse_theme_label("Liens") is None


def test_filter_registry_keeps_only_selected_themes_in_order():
    registry = registry_factory()
    filtered = filter_registry_by_themes(registry, {6})
    assert [t.test_id for t in filtered] == ["6.1.1", "6.2.1"]
    assert len(registry) == 3  # Le registre d'origine est intact.


def test_implemented_themes():
    assert implemented_themes(registry_factory()) == {1, 6}


# --- Orchestrateur ----------------------------------------------------------


@pytest.mark.asyncio
async def test_runs_only_selected_themes(orchestrator, html_file):
    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({6})))

    test_ids = [t.test_id for c in outcome.result.criteria for t in c.tests]
    assert test_ids == ["6.1.1", "6.2.1"]
    assert outcome.executed_themes == {6}
    assert outcome.implemented_themes == {1, 6}
    assert outcome.notices == []


@pytest.mark.asyncio
async def test_themes_without_tests_are_reported_not_audited(orchestrator, html_file):
    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1, 2})))

    assert outcome.executed_themes == {1}
    assert any("2. Cadres" in notice for notice in outcome.notices)


@pytest.mark.asyncio
async def test_no_implemented_theme_raises(orchestrator, html_file):
    with pytest.raises(AuditRequestError, match="Aucun test automatisé"):
        await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({2, 3})))


@pytest.mark.asyncio
async def test_empty_selection_raises(orchestrator, html_file):
    with pytest.raises(AuditRequestError, match="au moins une thématique"):
        await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset()))


@pytest.mark.asyncio
async def test_unknown_theme_raises(orchestrator, html_file):
    with pytest.raises(AuditRequestError, match="inconnues"):
        await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({42})))


@pytest.mark.asyncio
async def test_missing_html_raises(orchestrator, tmp_path):
    css = tmp_path / "style.css"
    css.write_text("body{}", encoding="utf-8")
    with pytest.raises(AuditRequestError, match="fichier HTML"):
        await orchestrator.run(AuditRequest(files=(css,), themes=frozenset({1})))


@pytest.mark.asyncio
async def test_missing_file_raises(orchestrator, tmp_path):
    with pytest.raises(AuditRequestError, match="introuvables"):
        await orchestrator.run(AuditRequest(files=(tmp_path / "absent.html",), themes=frozenset({1})))


@pytest.mark.asyncio
async def test_url_only_is_refused(orchestrator):
    with pytest.raises(AuditRequestError, match="URL"):
        await orchestrator.run(AuditRequest(url="https://exemple.fr", themes=frozenset({1})))


@pytest.mark.asyncio
async def test_url_with_html_is_ignored_with_notice(orchestrator, html_file):
    outcome = await orchestrator.run(AuditRequest(files=(html_file,), url="https://exemple.fr", themes=frozenset({1})))
    assert any("URL" in notice for notice in outcome.notices)


@pytest.mark.asyncio
async def test_several_html_files_notice(orchestrator, html_file, tmp_path):
    second = tmp_path / "autre.html"
    second.write_text("<html></html>", encoding="utf-8")
    outcome = await orchestrator.run(AuditRequest(files=(html_file, second), themes=frozenset({1})))
    assert any("seul le premier" in notice for notice in outcome.notices)


@pytest.mark.asyncio
async def test_failing_test_becomes_error_without_stopping_audit(tmp_path, html_file):
    def factory():
        return Registry([make_test("1.1.1", "1.1", error=RuntimeError("boom")), make_test("1.7.1", "1.7")])

    orchestrator = AuditOrchestrator(workspace_root=tmp_path / "ws", registry_factory=factory, services_factory=None)
    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1})))

    statuses = {t.test_id: t.status for c in outcome.result.criteria for t in c.tests}
    assert statuses == {"1.1.1": TestStatus.ERROR, "1.7.1": TestStatus.PASS}


@pytest.mark.asyncio
async def test_unavailable_ai_services_fall_back_with_notice(tmp_path, html_file):
    def broken_services():
        raise RuntimeError("OLLAMA_HOST manquant")

    orchestrator = AuditOrchestrator(
        workspace_root=tmp_path / "ws",
        registry_factory=registry_factory,
        services_factory=broken_services,
    )
    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1})))

    assert any("Services IA indisponibles" in notice for notice in outcome.notices)
    assert outcome.result.criteria  # L'audit déterministe a bien eu lieu.

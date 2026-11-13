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
    assert any("page principale analysée" in notice for notice in outcome.notices)


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


# Analyse du rendu (Playwright) et durées mesurées


class FakeEnricher:
    """Remplace le ContextEnricher : aucun navigateur n'est lancé."""

    def __init__(self, error: str | None = None, raises: Exception | None = None):
        self.calls = 0
        self.error = error
        self.raises = raises

    async def enrich(self, context):
        self.calls += 1
        if self.raises is not None:
            raise self.raises

        class Report:
            error = self.error
            non_text_error = None

        return Report()


def make_rendering_test(test_id: str, criterion_id: str):
    """Test qui exploite les styles calculés, comme les critères de contraste."""
    from accessi_code.models.capabilities import Capability

    test = make_test(test_id, criterion_id)
    type(test).optional_capabilities = frozenset({Capability.TEXT_CONTRAST})
    return test


def rendering_registry():
    return Registry([make_test("1.1.1", "1.1"), make_rendering_test("3.2.1", "3.2")])


def make_orchestrator(tmp_path: Path, enricher: FakeEnricher | None) -> AuditOrchestrator:
    return AuditOrchestrator(
        workspace_root=tmp_path / "workspace",
        registry_factory=rendering_registry,
        services_factory=None,
        enricher_factory=(lambda: enricher) if enricher is not None else None,
    )


@pytest.mark.asyncio
async def test_rendering_runs_only_for_themes_that_need_it(tmp_path, html_file):
    enricher = FakeEnricher()
    orchestrator = make_orchestrator(tmp_path, enricher)

    await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1})))
    assert enricher.calls == 0

    await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({3})))
    assert enricher.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enricher",
    [FakeEnricher(error="Chromium introuvable"), FakeEnricher(raises=RuntimeError("navigateur absent"))],
)
async def test_rendering_failure_is_reported_without_stopping_audit(tmp_path, html_file, enricher):
    orchestrator = make_orchestrator(tmp_path, enricher)

    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({3})))

    assert any("analyse du rendu" in notice.lower() for notice in outcome.notices)
    assert {t.test_id for c in outcome.result.criteria for t in c.tests} == {"3.2.1"}


@pytest.mark.asyncio
async def test_durations_are_saved_and_used_by_the_next_estimate(tmp_path, html_file):
    orchestrator = make_orchestrator(tmp_path, FakeEnricher())
    assert orchestrator.estimate(frozenset({1, 3})).measured_tests == 0

    await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1, 3})))

    reopened = make_orchestrator(tmp_path, FakeEnricher())
    estimate = reopened.estimate(frozenset({1, 3}))
    assert estimate.fully_measured
    assert estimate.with_enrichment
    assert (tmp_path / "workspace" / "audit_timings.json").is_file()


def test_estimate_without_tests_is_none(tmp_path):
    orchestrator = make_orchestrator(tmp_path, None)

    assert orchestrator.estimate(frozenset({13})) is None
    assert orchestrator.estimate(frozenset({3})).with_enrichment is False


@pytest.mark.asyncio
async def test_homepage_is_the_main_page(tmp_path, orchestrator):
    other = tmp_path / "a-propos.html"
    other.write_text("<html lang='fr'><body>A</body></html>", encoding="utf-8")
    home = tmp_path / "index.html"
    home.write_text("<html lang='fr'><body>Accueil</body></html>", encoding="utf-8")

    outcome = await orchestrator.run(AuditRequest(files=(other, home), themes=frozenset({1})))

    assert any("page principale analysée est index.html" in notice for notice in outcome.notices)


# Vérification du serveur d'IA


def make_ai_orchestrator(tmp_path: Path, *, ai_ok: bool, calls: list[str]) -> AuditOrchestrator:
    async def ai_check():
        calls.append("check")
        return ai_ok

    def services_factory():
        calls.append("services")
        return AuditServices()

    return AuditOrchestrator(
        workspace_root=tmp_path / "workspace",
        registry_factory=registry_factory,
        services_factory=services_factory,
        enricher_factory=None,
        ai_check=ai_check,
    )


@pytest.mark.asyncio
async def test_unavailable_ai_is_reported_and_ai_services_are_skipped(tmp_path, html_file):
    calls: list[str] = []
    events = []
    orchestrator = make_ai_orchestrator(tmp_path, ai_ok=False, calls=calls)

    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1, 6})), events.append)

    assert calls == ["check"]  # Les services IA ne sont jamais construits.
    assert any("IA non disponible" in notice for notice in outcome.notices)
    assert events[-1].ai_available is False
    # Durées faussées par l'absence d'IA : non enregistrées.
    assert not orchestrator.timing.is_measured("6.1.1")


@pytest.mark.asyncio
async def test_available_ai_uses_ai_services(tmp_path, html_file):
    calls: list[str] = []
    orchestrator = make_ai_orchestrator(tmp_path, ai_ok=True, calls=calls)

    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1})))

    assert calls == ["check", "services"]
    assert not any("IA non disponible" in notice for notice in outcome.notices)


@pytest.mark.asyncio
async def test_failing_ai_check_counts_as_unavailable(tmp_path, html_file):
    async def broken_check():
        raise OSError("réseau coupé")

    orchestrator = AuditOrchestrator(
        workspace_root=tmp_path / "workspace",
        registry_factory=registry_factory,
        services_factory=AuditServices,
        enricher_factory=None,
        ai_check=broken_check,
    )

    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({1})))

    assert any("IA non disponible" in notice for notice in outcome.notices)


def test_browser_evidence_tests_trigger_rendering():
    from accessi_code.models.capabilities import Capability
    from accessi_code.service.audit_orchestrator import needs_rendering

    test = make_test("12.9.1", "12.9")
    type(test).optional_capabilities = frozenset({Capability.BROWSER_INTERACTION})

    assert needs_rendering(Registry([test])) is True
    assert needs_rendering(Registry([make_test("1.1.1", "1.1")])) is False


@pytest.mark.asyncio
async def test_browser_evidence_failure_is_reported(tmp_path, html_file):
    class BrowserFailingEnricher(FakeEnricher):
        async def enrich(self, context):
            self.calls += 1

            class Report:
                error = None
                non_text_error = None
                browser_evidence_error = "Navigation Chromium : aucun navigateur"

            return Report()

    orchestrator = make_orchestrator(tmp_path, BrowserFailingEnricher())

    outcome = await orchestrator.run(AuditRequest(files=(html_file,), themes=frozenset({3})))

    assert any("aucun navigateur" in notice for notice in outcome.notices)

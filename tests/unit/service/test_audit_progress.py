"""Tests de la progression réelle : runner, orchestrateur et modèle."""

from pathlib import Path

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.result import TestResult as Result
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import TestRegistry as Registry
from accessi_code.rgaa.runner import TestRunner as Runner
from accessi_code.service.audit_orchestrator import AuditOrchestrator, AuditRequest
from accessi_code.service.audit_progress import AuditProgress, AuditStep


def make_test(test_id: str, criterion_id: str = "1.1", error: Exception | None = None):
    class FakeTest(RGAATest):
        async def run(self, context, services=None):
            if error is not None:
                raise error
            return Result(test_id=test_id, criterion_id=criterion_id, status=Status.PASS, summary="ok")

    FakeTest.test_id = test_id
    FakeTest.criterion_id = criterion_id
    return FakeTest()


def context(tmp_path: Path) -> AuditContext:
    return AuditContext(audit_id="a", workspace_path=tmp_path, files=[])


@pytest.mark.asyncio
async def test_runner_reports_each_test(tmp_path):
    calls = []
    runner = Runner(Registry([make_test("1.1.1"), make_test("1.1.2")]))
    await runner.run_all(context(tmp_path), lambda done, total, r: calls.append((done, total, r.test_id)))
    assert calls == [(1, 2, "1.1.1"), (2, 2, "1.1.2")]


@pytest.mark.asyncio
async def test_runner_accepts_async_callback(tmp_path):
    calls = []

    async def on_progress(done, total, result):
        calls.append(done)

    await Runner(Registry([make_test("1.1.1")])).run_all(context(tmp_path), on_progress)
    assert calls == [1]


@pytest.mark.asyncio
async def test_broken_callback_does_not_stop_audit(tmp_path):
    def broken(*_):
        raise RuntimeError("affichage cassé")

    results = await Runner(Registry([make_test("1.1.1"), make_test("1.1.2")])).run_all(context(tmp_path), broken)
    assert [r.status for r in results] == [Status.PASS, Status.PASS]


@pytest.mark.asyncio
async def test_runner_without_callback_is_unchanged(tmp_path):
    results = await Runner(Registry([make_test("1.1.1")])).run_all(context(tmp_path))
    assert len(results) == 1


@pytest.mark.asyncio
async def test_orchestrator_progress_sequence(tmp_path):
    html = tmp_path / "page.html"
    html.write_text("<html lang='fr'><body></body></html>", encoding="utf-8")

    def registry():
        return Registry([make_test("1.1.1"), make_test("1.1.2", error=RuntimeError("boom"))])

    orchestrator = AuditOrchestrator(workspace_root=tmp_path / "ws", registry_factory=registry, services_factory=None)
    events: list[AuditProgress] = []
    await orchestrator.run(AuditRequest(files=(html,), themes=frozenset({1})), events.append)

    assert [(e.step, e.done_tests, e.total_tests) for e in events] == [
        (AuditStep.PREPARATION, 0, 2),
        (AuditStep.TESTS, 0, 2),
        (AuditStep.TESTS, 1, 2),
        (AuditStep.TESTS, 2, 2),
        (AuditStep.DONE, 2, 2),
    ]
    assert events[-1].error_test_ids == ("1.1.2",)


def test_percent_only_when_known():
    assert AuditProgress(AuditStep.PREPARATION, total_tests=4).percent is None
    assert AuditProgress(AuditStep.TESTS, total_tests=0).percent is None
    assert AuditProgress(AuditStep.TESTS, done_tests=1, total_tests=4).percent == 25
    assert AuditProgress(AuditStep.DONE, done_tests=4, total_tests=4).percent == 100

"""Tests du rendu de la page de chargement et du flux de progression."""

import asyncio

import pytest

from accessi_code.service.audit_progress import AuditProgress, AuditStep
from accessi_code.ui.audit_bridge import UIAuditResult, stream_audit
from accessi_code.ui.loading_view import render_progress


def test_initial_state_is_indeterminate_without_percent():
    html = render_progress(None)
    assert "accessicode-progress-indeterminate" in html
    assert "aria-valuenow" not in html
    assert "%" not in html


def test_running_state_shows_real_counts():
    html = render_progress(AuditProgress(AuditStep.TESTS, done_tests=3, total_tests=12, last_test_id="8.1.2"))
    assert 'aria-valuenow="3"' in html and 'aria-valuemax="12"' in html
    assert "width: 25%" in html
    assert "3 test(s) terminé(s) sur 12" in html
    assert "8.1.2" in html
    assert 'aria-current="step"' in html
    assert "accessicode-step-done" in html  # La préparation est terminée.


def test_done_state_marks_all_steps_done():
    html = render_progress(AuditProgress(AuditStep.DONE, done_tests=2, total_tests=2))
    assert "accessicode-step-current" not in html and "accessicode-step-todo" not in html
    assert "width: 100%" in html


def test_errors_are_listed_and_escaped():
    html = render_progress(AuditProgress(AuditStep.TESTS, 1, 2, error_test_ids=("<b>x</b>",)))
    assert "1 test(s) en erreur" in html
    assert "<b>x</b>" not in html


class FakeOrchestrator:
    async def run(self, request, on_progress=None):
        on_progress(AuditProgress(AuditStep.PREPARATION, total_tests=1))
        on_progress(AuditProgress(AuditStep.DONE, done_tests=1, total_tests=1))
        raise RuntimeError("fin simulée")


@pytest.mark.asyncio
async def test_stream_yields_progress_then_final_result():
    items = [item async for item in stream_audit(None, [], ["1. Images"], FakeOrchestrator())]

    assert isinstance(items[-1], UIAuditResult)
    assert "fin simulée" in items[-1].error
    assert all(isinstance(item, AuditProgress) for item in items[:-1])
    assert items[-2].step == AuditStep.DONE  # Le dernier état n'est jamais perdu.


class SlowOrchestrator:
    """Émet une progression puis attend indéfiniment, comme un long test IA."""

    def __init__(self):
        self.cancelled = asyncio.Event()

    async def run(self, request, on_progress=None):
        on_progress(AuditProgress(AuditStep.TESTS, done_tests=0, total_tests=5))
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


@pytest.mark.asyncio
async def test_closing_stream_cancels_audit():
    orchestrator = SlowOrchestrator()
    stream = stream_audit(None, [], ["1. Images"], orchestrator)

    first = await anext(stream)
    assert first.step == AuditStep.TESTS
    await stream.aclose()

    await asyncio.wait_for(orchestrator.cancelled.wait(), timeout=2)


@pytest.mark.asyncio
async def test_cancelling_consumer_task_cancels_audit():
    """Reproduit l'annulation Gradio : la tâche qui consomme le flux est annulée."""
    orchestrator = SlowOrchestrator()
    received = asyncio.Event()

    async def consume():
        async for _ in stream_audit(None, [], ["1. Images"], orchestrator):
            received.set()

    consumer = asyncio.create_task(consume())
    await asyncio.wait_for(received.wait(), timeout=2)
    consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer

    await asyncio.wait_for(orchestrator.cancelled.wait(), timeout=2)

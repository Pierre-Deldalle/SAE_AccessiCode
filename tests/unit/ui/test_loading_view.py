"""Tests du rendu de la page de chargement et du flux de progression."""

import asyncio

import pytest

from accessi_code.service.audit_progress import AuditProgress, AuditStep
from accessi_code.ui.audit_bridge import UIAuditResult, advance_clock, stream_audit
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


def test_timing_is_displayed_during_the_audit():
    html = render_progress(AuditProgress(AuditStep.TESTS, 3, 10, elapsed_seconds=12, remaining_seconds=75))

    assert "Temps écoulé : 12 s" in html
    assert "Temps restant estimé : environ 1 min 15 s" in html


def test_timing_is_hidden_once_done():
    html = render_progress(AuditProgress(AuditStep.DONE, 2, 2, elapsed_seconds=5, remaining_seconds=0))

    assert "Temps restant" not in html


def test_rendering_step_is_shown_only_when_performed():
    with_rendering = render_progress(AuditProgress(AuditStep.ENRICHMENT, total_tests=4))
    without = render_progress(AuditProgress(AuditStep.TESTS, 0, 4, enrichment_needed=False))

    assert "Analyse du rendu de la page" in with_rendering
    assert "Analyse du rendu de la page" not in without


def test_advance_clock_keeps_progress_and_moves_time():
    progress = AuditProgress(AuditStep.TESTS, 2, 5, elapsed_seconds=10, remaining_seconds=4)

    later = advance_clock(progress, 6)

    assert (later.step, later.done_tests, later.total_tests) == (AuditStep.TESTS, 2, 5)
    assert later.elapsed_seconds == 16
    assert later.remaining_seconds == 0.0  # Jamais négatif.


class LongTestOrchestrator:
    """Un seul état de progression, puis un long « test IA »."""

    async def run(self, request, on_progress=None):
        on_progress(AuditProgress(AuditStep.TESTS, 0, 1, elapsed_seconds=1.0, remaining_seconds=30.0))
        await asyncio.sleep(2.5)
        raise RuntimeError("fin simulée")


@pytest.mark.asyncio
async def test_long_test_still_updates_the_clock():
    items = [item async for item in stream_audit(None, [], ["1. Images"], LongTestOrchestrator())]
    progress = [item for item in items if isinstance(item, AuditProgress)]

    assert len(progress) >= 2  # État initial + au moins une mise à jour d'horloge.
    assert progress[-1].elapsed_seconds > progress[0].elapsed_seconds
    assert progress[-1].remaining_seconds < progress[0].remaining_seconds


def test_ai_warning_shown_only_when_ai_is_unavailable():
    unavailable = render_progress(AuditProgress(AuditStep.TESTS, 1, 4, ai_available=False))
    available = render_progress(AuditProgress(AuditStep.TESTS, 1, 4, ai_available=True))
    unknown = render_progress(AuditProgress(AuditStep.PREPARATION, total_tests=4))

    assert "IA non disponible, certains tests ne seront pas évalués." in unavailable
    assert "IA non disponible" not in available
    assert "IA non disponible" not in unknown

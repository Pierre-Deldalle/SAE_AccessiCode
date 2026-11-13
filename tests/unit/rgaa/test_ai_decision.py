from dataclasses import dataclass

import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import (
    AI_MAX_ITEMS_ENV,
    DEFAULT_AI_MAX_ITEMS,
    ai_item_limit,
    analysis_evidence,
    count_statuses,
    get_analyzer,
    status_from_verdict,
    worst_status,
)
from accessi_code.service.audit_services import AuditServices


@pytest.mark.parametrize(
    ("verdict", "confidence", "expected"),
    [
        (True, "high", TestStatus.PASS),
        (False, "medium", TestStatus.FAIL),
        (True, "low", TestStatus.NEEDS_REVIEW),
        (False, "low", TestStatus.NEEDS_REVIEW),
        (None, "high", TestStatus.NEEDS_REVIEW),
    ],
)
def test_status_from_verdict(verdict, confidence, expected) -> None:
    assert status_from_verdict(verdict, confidence) is expected


def test_status_from_verdict_can_be_inverted() -> None:
    kwargs = {"when_true": TestStatus.FAIL, "when_false": TestStatus.PASS}
    assert status_from_verdict(True, "high", **kwargs) is TestStatus.FAIL
    assert status_from_verdict(False, "high", **kwargs) is TestStatus.PASS
    assert status_from_verdict(True, "low", **kwargs) is TestStatus.NEEDS_REVIEW


def test_worst_status_follows_conventions_priority() -> None:
    assert worst_status([TestStatus.PASS, TestStatus.NEEDS_REVIEW, TestStatus.FAIL]) is TestStatus.FAIL
    assert worst_status([TestStatus.NEEDS_REVIEW, TestStatus.ERROR]) is TestStatus.ERROR
    assert worst_status([TestStatus.PASS, TestStatus.NEEDS_REVIEW]) is TestStatus.NEEDS_REVIEW
    assert worst_status([TestStatus.PASS, TestStatus.NOT_APPLICABLE]) is TestStatus.PASS
    assert worst_status([]) is TestStatus.NOT_APPLICABLE


def test_count_statuses() -> None:
    counts = count_statuses([TestStatus.PASS, TestStatus.PASS, TestStatus.FAIL])
    assert counts["pass"] == 2
    assert counts["fail"] == 1
    assert counts["needs_review"] == 0


def test_get_analyzer() -> None:
    analyzer = object()
    services = AuditServices(text_relevance_analyzer=analyzer)
    assert get_analyzer(services, "text_relevance_analyzer") is analyzer
    assert get_analyzer(services, "sensory_analyzer") is None
    assert get_analyzer(None, "text_relevance_analyzer") is None


def test_ai_item_limit(monkeypatch) -> None:
    monkeypatch.delenv(AI_MAX_ITEMS_ENV, raising=False)
    assert ai_item_limit() == DEFAULT_AI_MAX_ITEMS
    monkeypatch.setenv(AI_MAX_ITEMS_ENV, "12")
    assert ai_item_limit() == 12
    monkeypatch.setenv(AI_MAX_ITEMS_ENV, "abc")
    assert ai_item_limit() == DEFAULT_AI_MAX_ITEMS
    monkeypatch.setenv(AI_MAX_ITEMS_ENV, "0")
    assert ai_item_limit() == DEFAULT_AI_MAX_ITEMS


def test_analysis_evidence() -> None:
    @dataclass
    class Analysis:
        relevant: bool
        confidence: str

    assert analysis_evidence(Analysis(True, "high")) == {"relevant": True, "confidence": "high"}
    assert analysis_evidence({"a": 1}) == {"a": 1}

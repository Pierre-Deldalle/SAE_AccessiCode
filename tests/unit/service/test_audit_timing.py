"""Tests de la mesure et de l'estimation de la durée des audits."""

import json
from pathlib import Path

import pytest

from accessi_code.service.audit_timing import (
    DEFAULT_PREPARATION_SECONDS,
    DEFAULT_TEST_SECONDS,
    AuditTimingStore,
    RemainingTimeTracker,
    format_duration,
)


def test_unmeasured_tests_use_starting_values(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={"8.7.1": 10.0})

    estimate = store.estimate(["1.1.1", "8.7.1"], with_enrichment=False)

    assert estimate.seconds == pytest.approx(DEFAULT_PREPARATION_SECONDS + DEFAULT_TEST_SECONDS + 10.0)
    assert estimate.total_tests == 2
    assert estimate.measured_tests == 0
    assert not estimate.fully_measured


def test_enrichment_is_added_only_when_needed(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={})
    store.record_enrichment(3.0)

    without = store.estimate(["1.1.1"], with_enrichment=False).seconds
    with_rendering = store.estimate(["1.1.1"], with_enrichment=True).seconds

    assert with_rendering - without == pytest.approx(3.0)


def test_measures_are_smoothed_between_audits(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={})
    store.record_test("8.7.1", 10.0)
    store.record_test("8.7.1", 20.0)

    assert store.test_seconds("8.7.1") == pytest.approx(15.0)
    assert store.is_measured("8.7.1")


def test_measures_survive_a_restart(tmp_path: Path):
    path = tmp_path / "workspace" / "timings.json"
    store = AuditTimingStore(path, defaults={})
    store.record_test("1.1.1", 0.4)
    store.record_enrichment(2.5)
    store.record_preparation(0.2)
    store.save()

    reloaded = AuditTimingStore(path, defaults={})
    estimate = reloaded.estimate(["1.1.1"], with_enrichment=True)

    assert reloaded.test_seconds("1.1.1") == pytest.approx(0.4)
    assert estimate.seconds == pytest.approx(0.4 + 2.5 + 0.2)
    assert estimate.fully_measured


@pytest.mark.parametrize("content", ["pas du json", json.dumps({"version": 99, "tests": {"1.1.1": 5}})])
def test_unreadable_file_is_ignored(tmp_path: Path, content: str):
    path = tmp_path / "timings.json"
    path.write_text(content, encoding="utf-8")

    store = AuditTimingStore(path, defaults={})

    assert not store.is_measured("1.1.1")


def test_invalid_durations_are_ignored(tmp_path: Path):
    path = tmp_path / "timings.json"
    path.write_text(json.dumps({"version": 1, "tests": {"1.1.1": -3, "1.1.2": "lent", "1.1.3": 0.5}}), encoding="utf-8")

    store = AuditTimingStore(path, defaults={})

    assert not store.is_measured("1.1.1")
    assert not store.is_measured("1.1.2")
    assert store.test_seconds("1.1.3") == pytest.approx(0.5)


def test_remaining_time_follows_observed_pace(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={"a": 2.0, "b": 2.0, "c": 2.0})
    tracker = RemainingTimeTracker(store, ["a", "b", "c"])

    assert tracker.remaining_seconds(0) == pytest.approx(6.0)

    # Le premier test a pris deux fois plus de temps que prévu.
    tracker.record(0, 4.0)
    assert tracker.remaining_seconds(1) == pytest.approx(8.0)


def test_pace_is_ignored_on_tiny_samples(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={"a": 0.01, "b": 5.0})
    tracker = RemainingTimeTracker(store, ["a", "b"])

    tracker.record(0, 1.0)  # 100 fois plus lent, mais sur une durée négligeable.

    assert tracker.remaining_seconds(1) == pytest.approx(5.0)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.2, "1 s"), (45, "45 s"), (60, "1 min"), (130, "2 min 10 s"), (3900, "1 h 5 min")],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected

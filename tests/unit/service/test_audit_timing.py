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


def test_remaining_time_follows_observed_pace_progressively(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={test_id: 20.0 for test_id in "abcd"})
    tracker = RemainingTimeTracker(store, list("abcd"))
    assert tracker.remaining_seconds(0) == pytest.approx(80.0)

    # Les tests prennent deux fois plus de temps que prévu : le rythme s'en rapproche peu à peu.
    tracker.record(0, 40.0)
    first = tracker.pace()
    tracker.record(1, 40.0)
    second = tracker.pace()
    assert 1.0 < first < second < 2.0
    assert tracker.remaining_seconds(2) == pytest.approx(40.0 * second)


def test_tiny_samples_barely_change_the_pace(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={"a": 0.01, "b": 5.0})
    tracker = RemainingTimeTracker(store, ["a", "b"])

    tracker.record(0, 1.0)  # 100 fois plus lent, mais sur une durée négligeable.

    assert tracker.remaining_seconds(1) == pytest.approx(5.0, rel=0.1)


def test_remaining_after_current_excludes_the_running_test(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={"a": 30.0, "b": 10.0, "c": 5.0})
    tracker = RemainingTimeTracker(store, ["a", "b", "c"])

    assert tracker.remaining_seconds(0) == pytest.approx(45.0)
    assert tracker.remaining_after_current(0) == pytest.approx(15.0)
    assert tracker.remaining_after_current(2) == pytest.approx(0.0)


def test_unmeasured_test_uses_the_median_of_its_theme(tmp_path: Path):
    store = AuditTimingStore(tmp_path / "t.json", defaults={})
    for test_id, seconds in (("11.1.1", 1.0), ("11.2.1", 12.0), ("11.3.1", 20.0), ("3.1.1", 50.0)):
        store.record_test(test_id, seconds)

    assert store.test_seconds("11.9.9") == pytest.approx(12.0)  # médiane du thème 11
    assert store.test_seconds("5.1.1") == pytest.approx(DEFAULT_TEST_SECONDS)  # thème jamais mesuré
    assert not store.is_measured("11.9.9")


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.2, "1 s"), (45, "45 s"), (60, "1 min"), (130, "2 min 10 s"), (3900, "1 h 5 min")],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_audits_without_ai_use_their_own_durations(tmp_path: Path):
    from accessi_code.service.audit_timing import NO_AI_MAX_SECONDS

    path = tmp_path / "timings.json"
    store = AuditTimingStore(path, defaults={})
    store.record_test("8.7.1", 20.0)  # avec IA
    store.record_test("8.2.1", 30.0)  # avec IA
    store.record_test("8.7.1", 0.02, with_ai=False)  # sans IA : conclut aussitôt « non testé »
    store.save()

    reloaded = AuditTimingStore(path, defaults={})
    assert reloaded.test_seconds("8.7.1") == pytest.approx(20.0)
    assert reloaded.test_seconds("8.7.1", with_ai=False) == pytest.approx(0.02)
    # Jamais mesuré sans IA : durée avec IA plafonnée.
    assert reloaded.test_seconds("8.2.1", with_ai=False) == pytest.approx(NO_AI_MAX_SECONDS)

    tracker = RemainingTimeTracker(reloaded, ["8.7.1", "8.2.1"], with_ai=False)
    assert tracker.remaining_seconds(0) == pytest.approx((0.02 + NO_AI_MAX_SECONDS) * tracker.pace())

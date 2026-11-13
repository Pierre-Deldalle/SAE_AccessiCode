"""
Mesure et estimation de la durée des audits.

Chaque audit enregistre la durée réelle de chaque test RGAA et de
l'analyse du rendu (Playwright). Ces mesures, conservées d'un audit à
l'autre dans ``workspace/audit_timings.json``, servent à estimer :

- avant l'audit, la durée totale pour les thématiques cochées ;
- pendant l'audit, le temps restant, corrigé selon le rythme observé.

Un test jamais mesuré utilise une valeur de départ. Ce module ne dépend
ni de Gradio ni d'Ollama.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Durée de départ d'un test jamais mesuré (contrôle déterministe sur le DOM).
DEFAULT_TEST_SECONDS = 0.05
# Durées de départ des tests qui interrogent l'IA : moyennes de plusieurs
# audits de test_files/full_site avec le serveur Ollama de l'IUT.
# Elles sont remplacées par les mesures locales dès le premier audit.
DEFAULT_SECONDS_BY_TEST: dict[str, float] = {
    "8.2.1": 9.0,
    "8.4.1": 4.0,
    "8.6.1": 5.0,
    "8.7.1": 11.0,
    "8.9.1": 9.0,
    "8.10.1": 9.0,
}
DEFAULT_ENRICHMENT_SECONDS = 4.0
DEFAULT_PREPARATION_SECONDS = 0.5

# Poids d'une nouvelle mesure dans la moyenne glissante.
NEW_MEASURE_WEIGHT = 0.5
# Bornes de la correction de rythme appliquée pendant l'audit.
MIN_PACE, MAX_PACE = 0.25, 4.0
# En dessous de cette durée estimée, le rythme observé n'est pas fiable.
MIN_SECONDS_FOR_PACE = 2.0

_FILE_VERSION = 1


@dataclass(frozen=True, slots=True)
class AuditEstimate:
    """Estimation de la durée d'un audit."""

    seconds: float
    total_tests: int
    # Nombre de tests dont la durée provient d'une mesure réelle.
    measured_tests: int
    with_enrichment: bool

    @property
    def fully_measured(self) -> bool:
        return self.total_tests > 0 and self.measured_tests == self.total_tests


class AuditTimingStore:
    """Durées mesurées des tests RGAA, conservées entre deux audits."""

    def __init__(self, path: Path | None = None, defaults: Mapping[str, float] | None = None):
        self.path = Path(path) if path is not None else None
        self.defaults = dict(DEFAULT_SECONDS_BY_TEST if defaults is None else defaults)
        self.tests: dict[str, float] = {}
        self.enrichment: float | None = None
        self.preparation: float | None = None
        self._load()

    # Lecture des durées

    def test_seconds(self, test_id: str) -> float:
        if test_id in self.tests:
            return self.tests[test_id]
        return self.defaults.get(test_id, DEFAULT_TEST_SECONDS)

    def is_measured(self, test_id: str) -> bool:
        return test_id in self.tests

    def enrichment_seconds(self) -> float:
        return self.enrichment if self.enrichment is not None else DEFAULT_ENRICHMENT_SECONDS

    def preparation_seconds(self) -> float:
        return self.preparation if self.preparation is not None else DEFAULT_PREPARATION_SECONDS

    def estimate(self, test_ids: Iterable[str], *, with_enrichment: bool) -> AuditEstimate:
        ids = list(test_ids)
        seconds = self.preparation_seconds() + sum(self.test_seconds(test_id) for test_id in ids)
        if with_enrichment:
            seconds += self.enrichment_seconds()
        return AuditEstimate(
            seconds=seconds,
            total_tests=len(ids),
            measured_tests=sum(1 for test_id in ids if self.is_measured(test_id)),
            with_enrichment=with_enrichment,
        )

    # Enregistrement des mesures

    def record_test(self, test_id: str, seconds: float) -> None:
        self.tests[test_id] = _smooth(self.tests.get(test_id), seconds)

    def record_enrichment(self, seconds: float) -> None:
        self.enrichment = _smooth(self.enrichment, seconds)

    def record_preparation(self, seconds: float) -> None:
        self.preparation = _smooth(self.preparation, seconds)

    def save(self) -> None:
        """Écrit les mesures ; une erreur d'écriture n'interrompt jamais l'audit."""
        if self.path is None:
            return
        data = {
            "version": _FILE_VERSION,
            "tests": {test_id: round(value, 4) for test_id, value in sorted(self.tests.items())},
            "enrichment": self.enrichment,
            "preparation": self.preparation,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            logger.warning("Impossible d'enregistrer les durées d'audit dans %s.", self.path, exc_info=True)

    def _load(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            logger.warning("Fichier de durées illisible, ignoré : %s.", self.path)
            return
        if not isinstance(data, dict) or data.get("version") != _FILE_VERSION:
            return
        tests = data.get("tests")
        if isinstance(tests, dict):
            self.tests = {str(key): float(value) for key, value in tests.items() if _is_duration(value)}
        if _is_duration(data.get("enrichment")):
            self.enrichment = float(data["enrichment"])
        if _is_duration(data.get("preparation")):
            self.preparation = float(data["preparation"])


class RemainingTimeTracker:
    """
    Temps restant pendant l'audit.

    Les durées estimées des tests restants sont corrigées par le rythme
    réellement observé sur les tests déjà terminés (machine ou serveur IA
    plus rapide ou plus lent que lors des audits précédents).
    """

    def __init__(self, store: AuditTimingStore, test_ids: Iterable[str]):
        self.store = store
        self.test_ids = list(test_ids)
        self._estimated_done = 0.0
        self._actual_done = 0.0

    def record(self, index: int, actual_seconds: float) -> None:
        """Note la durée réelle du test d'indice ``index`` dans l'ordre d'exécution."""
        if 0 <= index < len(self.test_ids):
            self._estimated_done += self.store.test_seconds(self.test_ids[index])
            self._actual_done += max(0.0, actual_seconds)

    def pace(self) -> float:
        if self._estimated_done < MIN_SECONDS_FOR_PACE or self._actual_done <= 0:
            return 1.0
        return min(MAX_PACE, max(MIN_PACE, self._actual_done / self._estimated_done))

    def remaining_seconds(self, done_tests: int) -> float:
        remaining = sum(self.store.test_seconds(test_id) for test_id in self.test_ids[done_tests:])
        return remaining * self.pace()


def format_duration(seconds: float) -> str:
    """Durée lisible : « 45 s », « 2 min 10 s », « 1 h 5 min »."""
    total = max(1, round(seconds))
    if total < 60:
        return f"{total} s"
    if total < 3600:
        minutes, rest = divmod(total, 60)
        return f"{minutes} min" + (f" {rest} s" if rest else "")
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    return f"{hours} h" + (f" {minutes} min" if minutes else "")


def _smooth(previous: float | None, measure: float) -> float:
    measure = max(0.0, float(measure))
    if previous is None:
        return measure
    return (1 - NEW_MEASURE_WEIGHT) * previous + NEW_MEASURE_WEIGHT * measure


def _is_duration(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0

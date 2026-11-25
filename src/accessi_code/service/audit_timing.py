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
# Sans IA, un test jamais mesuré dans ce mode prend au plus cette durée : les tests
# qui dépendent de l'IA concluent aussitôt « non testé ».
NO_AI_MAX_SECONDS = 0.5
DEFAULT_ENRICHMENT_SECONDS = 4.0
DEFAULT_PREPARATION_SECONDS = 0.5

# Poids d'une nouvelle mesure dans la moyenne glissante.
NEW_MEASURE_WEIGHT = 0.5
# Bornes de la correction de rythme appliquée pendant l'audit.
MIN_PACE, MAX_PACE = 0.2, 5.0
# Rythme « neutre » supposé au départ, en secondes d'audit : le rythme observé ne
# remplace l'estimation que progressivement, ce qui évite les sauts du temps restant
# sur les premiers tests (rythme = (réel + PACE_PRIOR) / (estimé + PACE_PRIOR)).
PACE_PRIOR_SECONDS = 20.0

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
        # Durées mesurées lors des audits sans IA (serveur indisponible).
        self.tests_without_ai: dict[str, float] = {}
        self.enrichment: float | None = None
        self.preparation: float | None = None
        self._load()

    # Lecture des durées

    def test_seconds(self, test_id: str, *, with_ai: bool = True) -> float:
        """
        Durée mesurée du test ; sinon sa valeur de départ ; sinon la durée médiane des
        tests mesurés de sa thématique (un nouveau test ressemble à ses voisins) ;
        sinon la durée d'un contrôle déterministe.

        Sans IA : durée mesurée sans IA, sinon la durée avec IA plafonnée à NO_AI_MAX_SECONDS.
        """
        if not with_ai:
            if test_id in self.tests_without_ai:
                return self.tests_without_ai[test_id]
            return min(self.test_seconds(test_id), NO_AI_MAX_SECONDS)
        if test_id in self.tests:
            return self.tests[test_id]
        if test_id in self.defaults:
            return self.defaults[test_id]
        theme = _theme(test_id)
        neighbours = sorted(value for key, value in self.tests.items() if _theme(key) == theme)
        if neighbours:
            return neighbours[len(neighbours) // 2]
        return DEFAULT_TEST_SECONDS

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

    def record_test(self, test_id: str, seconds: float, *, with_ai: bool = True) -> None:
        measures = self.tests if with_ai else self.tests_without_ai
        measures[test_id] = _smooth(measures.get(test_id), seconds)

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
            "tests_without_ai": {test_id: round(value, 4) for test_id, value in sorted(self.tests_without_ai.items())},
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
        without_ai = data.get("tests_without_ai")
        if isinstance(without_ai, dict):
            self.tests_without_ai = {str(key): float(value) for key, value in without_ai.items() if _is_duration(value)}
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

    def __init__(self, store: AuditTimingStore, test_ids: Iterable[str], *, with_ai: bool = True):
        self.store = store
        self.test_ids = list(test_ids)
        self.with_ai = with_ai
        self._estimated_done = 0.0
        self._actual_done = 0.0

    def record(self, index: int, actual_seconds: float) -> None:
        """Note la durée réelle du test d'indice ``index`` dans l'ordre d'exécution."""
        if 0 <= index < len(self.test_ids):
            self._estimated_done += self.store.test_seconds(self.test_ids[index], with_ai=self.with_ai)
            self._actual_done += max(0.0, actual_seconds)

    def pace(self) -> float:
        """Rapport entre durée réelle et durée estimée des tests terminés, lissé par PACE_PRIOR_SECONDS."""
        ratio = (self._actual_done + PACE_PRIOR_SECONDS) / (self._estimated_done + PACE_PRIOR_SECONDS)
        return min(MAX_PACE, max(MIN_PACE, ratio))

    def remaining_seconds(self, done_tests: int) -> float:
        """Temps restant estimé quand ``done_tests`` tests sont terminés."""
        remaining = sum(
            self.store.test_seconds(test_id, with_ai=self.with_ai) for test_id in self.test_ids[done_tests:]
        )
        return remaining * self.pace()

    def remaining_after_current(self, done_tests: int) -> float:
        """
        Temps restant des tests qui suivent celui en cours : le temps restant affiché
        ne descend jamais en dessous, même si le test en cours dure plus que prévu.
        """
        return self.remaining_seconds(done_tests + 1)


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


def _theme(test_id: str) -> str:
    return test_id.split(".", 1)[0]


def _is_duration(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0

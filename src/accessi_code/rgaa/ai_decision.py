"""
Règles communes de décision des tests RGAA qui s'appuient sur l'IA.

Applique CONVENTIONS.md §9 à §11 en un seul endroit :
- confiance "low" ou conclusion absente → NEEDS_REVIEW, jamais PASS ni FAIL ;
- priorité des statuts lorsqu'un test traite plusieurs éléments ;
- récupération d'un analyseur dans ``services`` sans dépendre de son implémentation.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from typing import Any

from accessi_code.models.result import TestStatus

# Nombre maximal d'éléments qu'un test soumet à l'IA (CONVENTIONS : coût maîtrisé).
AI_MAX_ITEMS_ENV = "ACCESSICODE_AI_MAX_ITEMS"
DEFAULT_AI_MAX_ITEMS = 50

# Priorité décroissante : un FAIL certain n'est jamais masqué par une incertitude.
STATUS_PRIORITY: tuple[TestStatus, ...] = (
    TestStatus.FAIL,
    TestStatus.ERROR,
    TestStatus.NEEDS_REVIEW,
    TestStatus.NOT_TESTED,
    TestStatus.PASS,
    TestStatus.NOT_APPLICABLE,
)


def get_analyzer(services: Any | None, name: str) -> Any | None:
    """Analyseur ``name`` fourni par les services, ou None (audit sans IA)."""
    if services is None:
        return None
    return getattr(services, name, None)


def ai_item_limit() -> int:
    """
    Limite d'éléments soumis à l'IA par test.

    Lue dans ACCESSICODE_AI_MAX_ITEMS ; une valeur absente ou invalide
    donne la valeur par défaut.
    """
    raw = os.environ.get(AI_MAX_ITEMS_ENV, "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_AI_MAX_ITEMS
    return value if value > 0 else DEFAULT_AI_MAX_ITEMS


def status_from_verdict(
    verdict: bool | None,
    confidence: str | None,
    *,
    when_true: TestStatus = TestStatus.PASS,
    when_false: TestStatus = TestStatus.FAIL,
) -> TestStatus:
    """
    Convertit une conclusion de l'IA en statut RGAA.

    ``when_true`` / ``when_false`` permettent d'inverser le sens lorsque la
    question posée à l'IA est négative (par exemple « l'information repose-t-elle
    uniquement sur la couleur ? » : true → FAIL).
    """
    if confidence == "low" or verdict is None:
        return TestStatus.NEEDS_REVIEW
    return when_true if verdict else when_false


def worst_status(statuses: Iterable[TestStatus]) -> TestStatus:
    """Statut global d'un test qui a examiné plusieurs éléments (aucun → NOT_APPLICABLE)."""
    present = set(statuses)
    for status in STATUS_PRIORITY:
        if status in present:
            return status
    return TestStatus.NOT_APPLICABLE


def count_statuses(statuses: Iterable[TestStatus]) -> dict[str, int]:
    """Nombre d'éléments par statut, sérialisable en JSON (pour ``metadata``)."""
    counts = {status.value: 0 for status in STATUS_PRIORITY}
    for status in statuses:
        counts[status.value] += 1
    return counts


def analysis_evidence(analysis: Any) -> dict[str, Any]:
    """Réponse de l'IA sous forme de dictionnaire, pour ``Finding.evidence``."""
    if is_dataclass(analysis) and not isinstance(analysis, type):
        return asdict(analysis)
    if isinstance(analysis, dict):
        return dict(analysis)
    return {"value": repr(analysis)}

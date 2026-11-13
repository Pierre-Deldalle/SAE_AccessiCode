"""
Suivi de progression d'un audit.

Le pourcentage provient uniquement de l'avancement réel du moteur
(tests terminés). Le temps restant est une estimation, fondée sur les
durées mesurées lors des audits précédents et sur le rythme observé.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum


class AuditStep(str, Enum):
    """Étapes successives d'un audit, dans l'ordre."""

    PREPARATION = "preparation"
    ENRICHMENT = "enrichment"
    TESTS = "tests"
    SYNTHESIS = "synthesis"
    DONE = "done"


STEP_LABELS: dict[AuditStep, str] = {
    AuditStep.PREPARATION: "Préparation des documents",
    AuditStep.ENRICHMENT: "Analyse du rendu de la page",
    AuditStep.TESTS: "Exécution des tests RGAA",
    AuditStep.SYNTHESIS: "Synthèse des résultats",
}

STEP_ORDER: tuple[AuditStep, ...] = tuple(STEP_LABELS)


@dataclass(frozen=True, slots=True)
class AuditProgress:
    """État d'avancement à un instant donné."""

    step: AuditStep
    done_tests: int = 0
    total_tests: int = 0
    last_test_id: str | None = None
    # Tests terminés en erreur jusqu'ici.
    error_test_ids: tuple[str, ...] = ()
    # Temps écoulé depuis le lancement et temps restant estimé, en secondes.
    elapsed_seconds: float | None = None
    remaining_seconds: float | None = None
    # False si l'analyse du rendu n'est pas nécessaire pour les thématiques cochées.
    enrichment_needed: bool = True
    # False si le serveur d'IA ne répond pas ; None tant que ce n'est pas vérifié.
    ai_available: bool | None = None

    @property
    def percent(self) -> int | None:
        """Pourcentage de tests terminés, uniquement quand il est connu."""
        if self.step == AuditStep.DONE:
            return 100
        if self.step in (AuditStep.TESTS, AuditStep.SYNTHESIS) and self.total_tests > 0:
            return round(100 * self.done_tests / self.total_tests)
        return None


AuditProgressCallback = Callable[[AuditProgress], Awaitable[None] | None]


async def notify_progress(callback: AuditProgressCallback | None, progress: AuditProgress) -> None:
    """Transmet la progression ; une erreur d'affichage n'interrompt jamais l'audit."""
    if callback is None:
        return
    try:
        outcome = callback(progress)
        if asyncio.iscoroutine(outcome):
            await outcome
    except asyncio.CancelledError:
        raise
    except Exception:
        pass

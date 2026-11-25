"""
Pont entre les composants Gradio et l'orchestrateur d'audit.

Convertit les valeurs brutes de l'interface (URL, fichiers déposés,
libellés de thématiques) en AuditRequest, lance l'audit et retourne
des données prêtes à afficher. Aucune logique d'audit ici.
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from accessi_code.ai.token_usage import TokenUsage
from accessi_code.rgaa.themes import parse_theme_label
from accessi_code.service.audit_orchestrator import (
    AuditOrchestrator,
    AuditRequest,
    AuditRequestError,
    check_ai_available,
)
from accessi_code.service.audit_progress import AuditProgress, AuditProgressCallback, AuditStep
from accessi_code.service.audit_timing import AuditEstimate
from accessi_code.service.theme_summary import ThemeSummary, summarize_themes

ROOT_DIR = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = ROOT_DIR / "workspace"

_orchestrator: AuditOrchestrator | None = None


def get_orchestrator() -> AuditOrchestrator:
    """Orchestrateur partagé, créé au premier audit."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AuditOrchestrator(workspace_root=WORKSPACE_DIR, ai_check=check_ai_available)
    return _orchestrator


@dataclass(slots=True)
class UIAuditResult:
    """Ce que la page de résultats doit afficher, ou l'erreur à montrer."""

    summaries: tuple[ThemeSummary, ...] = ()
    notices: list[str] = field(default_factory=list)
    error: str | None = None
    # Tokens consommés par l'IA et durée totale de l'audit, en secondes.
    tokens_used: int = 0
    duration_seconds: float = 0.0


def uploaded_paths(files: Any) -> tuple[Path, ...]:
    """Chemins locaux des fichiers fournis par gr.File (str, objets ou liste)."""
    if files is None:
        return ()
    if not isinstance(files, list | tuple):
        files = [files]
    paths = []
    for item in files:
        if item is None:
            continue
        path = getattr(item, "path", None) or getattr(item, "name", None) or item
        paths.append(Path(str(path)))
    return tuple(paths)


def selected_theme_numbers(theme_labels: list[str] | None) -> frozenset[int]:
    """Numéros des thématiques à partir des libellés « N. Nom » cochés."""
    numbers = (parse_theme_label(label) for label in theme_labels or [])
    return frozenset(n for n in numbers if n is not None)


def estimate_audit(
    theme_labels: list[str] | None,
    orchestrator: AuditOrchestrator | None = None,
) -> AuditEstimate | None:
    """Durée estimée pour les thématiques cochées (None si aucun test à exécuter)."""
    themes = selected_theme_numbers(theme_labels)
    if not themes:
        return None
    return (orchestrator or get_orchestrator()).estimate(themes)


def build_audit_request(url: str | None, files: Any, theme_labels: list[str] | None) -> AuditRequest:
    """Construit la demande d'audit à partir des valeurs de l'interface."""
    return AuditRequest(
        files=uploaded_paths(files),
        url=(url or "").strip() or None,
        themes=selected_theme_numbers(theme_labels),
    )


async def run_audit_from_ui(
    url: str | None,
    files: Any,
    theme_labels: list[str] | None,
    orchestrator: AuditOrchestrator | None = None,
    on_progress: AuditProgressCallback | None = None,
    token_usage: TokenUsage | None = None,
) -> UIAuditResult:
    """Lance l'audit et retourne les synthèses, ou un message d'erreur lisible."""
    request = build_audit_request(url, files, theme_labels)
    orchestrator = orchestrator or get_orchestrator()

    try:
        outcome = await orchestrator.run(request, on_progress, token_usage=token_usage)
    except AuditRequestError as error:
        return UIAuditResult(error=str(error))
    except Exception as error:  # Erreur inattendue : on informe sans planter l'interface.
        return UIAuditResult(error=f"L'audit n'a pas pu être réalisé ({type(error).__name__} : {error}).")

    summaries = summarize_themes(
        outcome.result,
        selected=request.themes,
        implemented=outcome.implemented_themes,
    )
    return UIAuditResult(
        summaries=summaries,
        notices=outcome.notices,
        tokens_used=getattr(outcome, "tokens_used", 0),
        duration_seconds=getattr(outcome, "duration_seconds", 0.0),
    )


# Intervalle de mise à jour de l'affichage pendant un test long.
HEARTBEAT_SECONDS = 1.0


def advance_clock(progress: AuditProgress, seconds: float, tokens_used: int | None = None) -> AuditProgress:
    """
    Même état d'avancement, avec le temps écoulé, le temps restant et les tokens actualisés.

    Le temps restant diminue avec le temps écoulé, sans descendre sous celui des étapes
    qui n'ont pas encore commencé (``remaining_floor_seconds``) : un test plus long que
    prévu ne fait pas croire que l'audit est presque fini.
    """
    if progress.step == AuditStep.DONE or progress.elapsed_seconds is None:
        return progress
    remaining = progress.remaining_seconds
    if remaining is not None:
        remaining = max(progress.remaining_floor_seconds or 0.0, remaining - seconds, 0.0)
    return dataclasses.replace(
        progress,
        elapsed_seconds=progress.elapsed_seconds + seconds,
        remaining_seconds=remaining,
        tokens_used=max(progress.tokens_used, tokens_used or 0),
    )


async def stream_audit(
    url: str | None,
    files: Any,
    theme_labels: list[str] | None,
    orchestrator: AuditOrchestrator | None = None,
) -> AsyncIterator[AuditProgress | UIAuditResult]:
    """
    Lance l'audit en tâche de fond et produit, dans l'ordre :
    les AuditProgress successifs, puis un UIAuditResult final.

    Pendant un test long (appel à l'IA), l'état le plus récent est renvoyé
    chaque seconde avec un temps écoulé et un temps restant mis à jour,
    pour que l'interface ne paraisse pas figée.

    Si l'appelant arrête l'itération (page fermée), l'audit est annulé.
    """
    queue: asyncio.Queue[AuditProgress] = asyncio.Queue()
    # Compteur lu à chaque seconde : les tokens avancent aussi pendant un long test.
    usage = TokenUsage()
    task = asyncio.create_task(
        run_audit_from_ui(url, files, theme_labels, orchestrator, queue.put_nowait, token_usage=usage)
    )
    loop = asyncio.get_running_loop()
    last_sent: AuditProgress | None = None
    last_sent_at = 0.0

    try:
        while not task.done():
            getter = asyncio.create_task(queue.get())
            await asyncio.wait({task, getter}, timeout=HEARTBEAT_SECONDS, return_when=asyncio.FIRST_COMPLETED)
            if not getter.done():
                getter.cancel()
                if not task.done() and last_sent is not None:
                    yield advance_clock(last_sent, loop.time() - last_sent_at, usage.total)
                continue
            latest = getter.result()
            # Plusieurs tests rapides : on n'affiche que l'état le plus récent.
            while not queue.empty():
                latest = queue.get_nowait()
            last_sent, last_sent_at = latest, loop.time()
            yield latest

        # Dernier état reçu juste avant la fin de la tâche.
        last: AuditProgress | None = None
        while not queue.empty():
            last = queue.get_nowait()
        if last is not None:
            yield last
        yield task.result()
    finally:
        if not task.done():
            task.cancel()

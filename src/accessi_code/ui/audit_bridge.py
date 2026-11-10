"""
Pont entre les composants Gradio et l'orchestrateur d'audit.

Convertit les valeurs brutes de l'interface (URL, fichiers déposés,
libellés de thématiques) en AuditRequest, lance l'audit et retourne
des données prêtes à afficher. Aucune logique d'audit ici.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from accessi_code.rgaa.themes import parse_theme_label
from accessi_code.service.audit_orchestrator import (
    AuditOrchestrator,
    AuditRequest,
    AuditRequestError,
)
from accessi_code.service.audit_progress import AuditProgress, AuditProgressCallback
from accessi_code.service.theme_summary import ThemeSummary, summarize_themes

ROOT_DIR = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = ROOT_DIR / "workspace"

_orchestrator: AuditOrchestrator | None = None


def get_orchestrator() -> AuditOrchestrator:
    """Orchestrateur partagé, créé au premier audit."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AuditOrchestrator(workspace_root=WORKSPACE_DIR)
    return _orchestrator


@dataclass(slots=True)
class UIAuditResult:
    """Ce que la page de résultats doit afficher, ou l'erreur à montrer."""

    summaries: tuple[ThemeSummary, ...] = ()
    notices: list[str] = field(default_factory=list)
    error: str | None = None


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


def build_audit_request(url: str | None, files: Any, theme_labels: list[str] | None) -> AuditRequest:
    """Construit la demande d'audit à partir des valeurs de l'interface."""
    numbers = (parse_theme_label(label) for label in theme_labels or [])
    return AuditRequest(
        files=uploaded_paths(files),
        url=(url or "").strip() or None,
        themes=frozenset(n for n in numbers if n is not None),
    )


async def run_audit_from_ui(
    url: str | None,
    files: Any,
    theme_labels: list[str] | None,
    orchestrator: AuditOrchestrator | None = None,
    on_progress: AuditProgressCallback | None = None,
) -> UIAuditResult:
    """Lance l'audit et retourne les synthèses, ou un message d'erreur lisible."""
    request = build_audit_request(url, files, theme_labels)
    orchestrator = orchestrator or get_orchestrator()

    try:
        outcome = await orchestrator.run(request, on_progress)
    except AuditRequestError as error:
        return UIAuditResult(error=str(error))
    except Exception as error:  # Erreur inattendue : on informe sans planter l'interface.
        return UIAuditResult(error=f"L'audit n'a pas pu être réalisé ({type(error).__name__} : {error}).")

    summaries = summarize_themes(
        outcome.result,
        selected=request.themes,
        implemented=outcome.implemented_themes,
    )
    return UIAuditResult(summaries=summaries, notices=outcome.notices)


async def stream_audit(
    url: str | None,
    files: Any,
    theme_labels: list[str] | None,
    orchestrator: AuditOrchestrator | None = None,
) -> AsyncIterator[AuditProgress | UIAuditResult]:
    """
    Lance l'audit en tâche de fond et produit, dans l'ordre :
    les AuditProgress successifs, puis un UIAuditResult final.

    Si l'appelant arrête l'itération (page fermée), l'audit est annulé.
    """
    queue: asyncio.Queue[AuditProgress] = asyncio.Queue()
    task = asyncio.create_task(run_audit_from_ui(url, files, theme_labels, orchestrator, queue.put_nowait))

    try:
        while not task.done():
            getter = asyncio.create_task(queue.get())
            await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
            if not getter.done():
                getter.cancel()
                continue
            latest = getter.result()
            # Plusieurs tests rapides : on n'affiche que l'état le plus récent.
            while not queue.empty():
                latest = queue.get_nowait()
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

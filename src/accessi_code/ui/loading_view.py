"""Rendu HTML de la page de chargement, indépendant de Gradio.

La barre n'avance que d'après l'AuditProgress fourni par le moteur.
Tant que le nombre de tests terminés n'est pas connu, une barre
indéterminée est affichée, sans pourcentage.
"""

from __future__ import annotations

from html import escape

from accessi_code.service.audit_progress import (
    STEP_LABELS,
    STEP_ORDER,
    AuditProgress,
    AuditStep,
)
from accessi_code.service.audit_timing import format_duration

# Nombre maximal d'identifiants de tests en erreur cités sur la page.
MAX_ERRORS_LISTED = 5


def _step_state(step: AuditStep, progress: AuditProgress | None) -> str:
    """Retourne « done », « current » ou « todo » pour une étape."""
    if progress is None:
        return "current" if step == STEP_ORDER[0] else "todo"
    if progress.step == AuditStep.DONE:
        return "done"
    current = STEP_ORDER.index(progress.step)
    index = STEP_ORDER.index(step)
    if index < current:
        return "done"
    return "current" if index == current else "todo"


_STATE_TEXT = {
    "done": ("✓", "terminée"),
    "current": ("●", "en cours"),
    "todo": ("○", "à venir"),
}


def _visible_steps(progress: AuditProgress | None) -> tuple[AuditStep, ...]:
    """L'analyse du rendu n'apparaît que si elle est réalisée pour cet audit."""
    if progress is not None and not progress.enrichment_needed:
        return tuple(step for step in STEP_ORDER if step != AuditStep.ENRICHMENT)
    return STEP_ORDER


def _render_steps(progress: AuditProgress | None) -> str:
    items = []
    for step in _visible_steps(progress):
        state = _step_state(step, progress)
        marker, label = _STATE_TEXT[state]
        current = ' aria-current="step"' if state == "current" else ""
        items.append(
            f'<li class="accessicode-step accessicode-step-{state}"{current}>'
            f'<span class="accessicode-step-marker" aria-hidden="true">{marker}</span>'
            f"{escape(STEP_LABELS[step])}"
            f'<span class="accessicode-sr-only"> ({label})</span></li>'
        )
    return '<ol class="accessicode-steps">' + "".join(items) + "</ol>"


def _description(progress: AuditProgress | None) -> str:
    if progress is None or progress.step == AuditStep.PREPARATION:
        total = progress.total_tests if progress else 0
        suffix = f" {total} test(s) à exécuter." if total else ""
        return "Copie et analyse des documents importés…" + suffix
    if progress.step == AuditStep.ENRICHMENT:
        return "Analyse du rendu de la page dans un navigateur (styles et contrastes)…"
    if progress.step == AuditStep.SYNTHESIS:
        return "Synthèse des résultats par thématique…"
    if progress.step == AuditStep.DONE:
        return f"Audit terminé : {progress.total_tests} test(s) exécuté(s)."
    text = f"{progress.done_tests} test(s) terminé(s) sur {progress.total_tests}"
    if progress.last_test_id:
        text += f" — dernier : test {progress.last_test_id}"
    return text + "."


def _timing(progress: AuditProgress | None) -> str:
    """Temps écoulé et temps restant estimé, quand ils sont connus."""
    if progress is None or progress.step == AuditStep.DONE:
        return ""
    parts = []
    if progress.elapsed_seconds is not None:
        parts.append(f"Temps écoulé : {format_duration(progress.elapsed_seconds)}")
    if progress.remaining_seconds is not None:
        if progress.remaining_seconds < 1:
            parts.append("Temps restant estimé : quelques secondes")
        else:
            parts.append(f"Temps restant estimé : environ {format_duration(progress.remaining_seconds)}")
    if not parts:
        return ""
    return '<p class="accessicode-progress-timing">' + escape(" · ".join(parts)) + "</p>"


AI_WARNING_TEXT = "IA non disponible, certains tests ne seront pas évalués."


def _ai_warning(progress: AuditProgress | None) -> str:
    """Zone rouge affichée quand le serveur d'IA ne répond pas."""
    if progress is None or progress.ai_available is not False:
        return ""
    return f'<p class="accessicode-progress-alert accessicode-progress-ai-warning">{escape(AI_WARNING_TEXT)}</p>'


def render_progress(progress: AuditProgress | None) -> str:
    """HTML complet du bloc de progression."""
    percent = progress.percent if progress else None

    if percent is None:
        bar = (
            '<div class="accessicode-progress-track accessicode-progress-indeterminate" '
            'role="progressbar" aria-label="Progression de l\'audit" aria-valuetext="En préparation">'
            '<div class="accessicode-progress-fill"></div></div>'
        )
    else:
        done = progress.done_tests if progress else 0
        total = progress.total_tests if progress else 0
        bar = (
            '<div class="accessicode-progress-track" role="progressbar" '
            'aria-label="Progression des tests" '
            f'aria-valuemin="0" aria-valuemax="{total}" aria-valuenow="{done}" '
            f'aria-valuetext="{done} test(s) sur {total}">'
            f'<div class="accessicode-progress-fill" style="width: {percent}%"></div></div>'
            f'<p class="accessicode-progress-percent" aria-hidden="true">{percent} %</p>'
        )

    alert = ""
    if progress and progress.error_test_ids:
        ids = ", ".join(escape(test_id) for test_id in progress.error_test_ids[:MAX_ERRORS_LISTED])
        more = len(progress.error_test_ids) - MAX_ERRORS_LISTED
        if more > 0:
            ids += f" et {more} autre(s)"
        alert = (
            '<p class="accessicode-progress-alert">'
            f"{len(progress.error_test_ids)} test(s) en erreur ({ids}). "
            "L'audit continue ; le détail figurera dans les résultats.</p>"
        )

    return (
        '<div class="accessicode-progress-section">'
        + _render_steps(progress)
        + bar
        + f'<p class="accessicode-progress-description" aria-live="polite">{escape(_description(progress))}</p>'
        + _timing(progress)
        + _ai_warning(progress)
        + alert
        + "</div>"
    )

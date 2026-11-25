"""Rendu des résultats d'audit, indépendant de Gradio.

Transforme des ThemeSummary en classes CSS de cartes et en HTML de
détail (voir theme_detail_view.py). Aucune dépendance à Gradio, au moteur RGAA ou à Ollama :
ce module est testable sans lancer l'interface.
"""

from accessi_code.ai.token_usage import format_tokens
from accessi_code.service.audit_timing import format_duration
from accessi_code.service.theme_summary import ThemeState, ThemeSummary
from accessi_code.ui.theme_detail_view import (
    MAX_FINDINGS_PER_TEST,
    build_theme_detail,
    priority_label,
    score_category,
    split_recommendation,
)

__all__ = [
    "MAX_FINDINGS_PER_TEST",
    "build_theme_detail",
    "priority_label",
    "score_category",
    "split_recommendation",
]

DEFAULT_THEME_DETAIL = (
    '<p class="ac-muted">Sélectionnez une carte ci-dessus pour afficher les informations du thème.</p>'
)

LEGEND_TEXT = (
    "**Codes de couleur :** **rouge (0–35 %)** · **jaune (36–65 %)** · "
    "**vert (66–100 %)** · **cyan : à vérifier manuellement** · "
    "**gris : non évaluée**. "
    "Le pourcentage est la part des critères conformes parmi les critères "
    "que les tests automatiques ont pu trancher (conformes ou non conformes). "
    "Ces repères sont propres à AccessiCode : ce n'est pas un taux officiel "
    "de conformité RGAA. Une carte bordée de pointillés rouges signale un "
    "**résultat incomplet** : certains critères n'ont pas pu être évalués."
)

# Texte affiché dans le cercle pour les thématiques sans pourcentage.
# « \A » est un retour à la ligne en CSS.
_STATE_CIRCLE_TEXT = {
    ThemeState.NEEDS_REVIEW: ("review", "À\\Avérifier"),
    ThemeState.ERROR: ("error", "Erreur"),
    ThemeState.NOT_TESTED: ("neutral", "Non\\Atestée"),
    ThemeState.NOT_APPLICABLE: ("neutral", "Non\\Aapplicable"),
    ThemeState.NOT_IMPLEMENTED: ("neutral", "Pas de\\Atest"),
    ThemeState.NOT_SELECTED: ("neutral", "Non\\Aretenue"),
}

# CSS généré : un pourcentage par classe (0 à 100) et un texte par état.
SCORE_CSS = "\n".join(
    [f'.theme-score-{n} {{ --score-text: "{n} %"; }}' for n in range(101)]
    + [f'.theme-score-{state.value} {{ --score-text: "{text}"; }}' for state, (_, text) in _STATE_CIRCLE_TEXT.items()]
)


def _is_incomplete(summary: ThemeSummary) -> bool:
    """Résultat partiel : des critères de la thématique n'ont pas pu être évalués."""
    return summary.state not in (ThemeState.NOT_SELECTED, ThemeState.NOT_IMPLEMENTED) and summary.incomplete


def card_label(summary: ThemeSummary) -> str:
    """
    Texte d'une carte : nom de la thématique, base du pourcentage et,
    le cas échéant, l'avertissement « Résultat incomplet ».
    """
    lines = [summary.theme.label]
    if summary.state == ThemeState.SCORED:
        lines.append(f"Calculé sur {summary.decided} critère(s) sur {summary.applicable}")
    if _is_incomplete(summary):
        lines.append("⚠ Résultat incomplet")
    return "\n".join(lines)


def card_classes(summary: ThemeSummary) -> list[str]:
    """Classes CSS d'une carte : contenu du cercle, couleur et état incomplet."""
    extra = ["theme-incomplete"] if _is_incomplete(summary) else []
    if summary.state == ThemeState.SCORED and summary.score is not None:
        return [
            "resultats-theme-card",
            f"theme-score-{summary.score}",
            f"theme-status-{score_category(summary.score)}",
            *extra,
        ]
    color, _ = _STATE_CIRCLE_TEXT[summary.state]
    return [
        "resultats-theme-card",
        "theme-score-word",
        f"theme-score-{summary.state.value}",
        f"theme-status-{color}",
        *extra,
    ]


def initial_card_classes() -> list[str]:
    return ["resultats-theme-card", "theme-score-word", "theme-status-neutral"]


# HTML, Markdown et délimiteurs LaTeX remplacés par des entités, en une passe.
_ESCAPE_TABLE = str.maketrans({char: f"&#{ord(char)};" for char in "&<>\"'\\`*_[]{}#|~$!"})


def _safe(text: object, limit: int = 300) -> str:
    """
    Neutralise un texte provenant de la page auditée ou d'une IA.

    Le HTML et la syntaxe Markdown/LaTeX sont échappés pour éviter toute
    injection dans l'interface.
    """
    value = " ".join(str(text).split())
    if len(value) > limit:
        value = value[: limit - 1] + "…"
    return value.translate(_ESCAPE_TABLE)


def audit_stats(duration_seconds: float, tokens_used: int) -> str:
    """« Audit réalisé en 2 min 10 s · 12 345 tokens utilisés par l'IA. »"""
    parts = []
    if duration_seconds > 0:
        parts.append(f"Audit réalisé en {format_duration(duration_seconds)}")
    parts.append(f"{format_tokens(tokens_used)} utilisés par l'IA" if tokens_used else "aucun appel à l'IA")
    return " · ".join(parts) + "."


def build_notices(notices: list[str], stats: str = "") -> str:
    """Durée et tokens de l'audit, puis avertissements (URL ignorée, thématiques sans test…)."""
    lines = [f"**{_safe(stats, 300)}**"] if stats else []
    if notices:
        if lines:
            lines.append("")
        lines += [f"- {_safe(notice, 500)}" for notice in notices]
    return "\n".join(lines)


def show_detail(summaries: tuple[ThemeSummary, ...], index: int) -> str:
    if not summaries or index >= len(summaries):
        return DEFAULT_THEME_DETAIL
    return build_theme_detail(summaries[index])

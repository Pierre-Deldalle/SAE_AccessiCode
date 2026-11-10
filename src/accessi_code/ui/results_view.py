"""Rendu des résultats d'audit, indépendant de Gradio.

Transforme des ThemeSummary en classes CSS de cartes et en Markdown
de détail. Aucune dépendance à Gradio, au moteur RGAA ou à Ollama :
ce module est testable sans lancer l'interface.
"""

from accessi_code.models.result import TestResult, TestStatus
from accessi_code.service.theme_summary import (
    STATE_LABELS,
    STATUS_LABELS,
    ThemeState,
    ThemeSummary,
)

DEFAULT_THEME_DETAIL = "Sélectionnez une carte ci-dessus pour afficher les informations du thème."

LEGEND_TEXT = (
    "**Codes de couleur :** **rouge (0–35 %)** · **jaune (36–65 %)** · "
    "**vert (66–100 %)** · **cyan : à vérifier manuellement** · "
    "**gris : non évaluée**. "
    "Le pourcentage est la part des critères conformes parmi les critères "
    "que les tests automatiques ont pu trancher (conformes ou non conformes). "
    "Ces repères sont propres à AccessiCode : ce n'est pas un taux officiel "
    "de conformité RGAA."
)

# Nombre maximal d'anomalies détaillées par test, pour garder la page lisible.
MAX_FINDINGS_PER_TEST = 15

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


def score_category(score: int) -> str:
    """Détermine la couleur associée à un pourcentage."""
    if not 0 <= score <= 100:
        raise ValueError("Le score doit être compris entre 0 et 100.")
    if score <= 35:
        return "danger"
    if score <= 65:
        return "warning"
    return "success"


def priority_label(score: int) -> str:
    """Retourne une indication compréhensible sans la couleur."""
    category = score_category(score)
    if category == "danger":
        return "Priorité élevée"
    if category == "warning":
        return "À surveiller"
    return "Satisfaisant"


def card_classes(summary: ThemeSummary) -> list[str]:
    """Classes CSS d'une carte : contenu du cercle et couleur."""
    if summary.state == ThemeState.SCORED and summary.score is not None:
        return [
            "resultats-theme-card",
            f"theme-score-{summary.score}",
            f"theme-status-{score_category(summary.score)}",
        ]
    color, _ = _STATE_CIRCLE_TEXT[summary.state]
    return [
        "resultats-theme-card",
        "theme-score-word",
        f"theme-score-{summary.state.value}",
        f"theme-status-{color}",
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


def _test_lines(test: TestResult) -> list[str]:
    """Lignes Markdown décrivant un test et ses anomalies."""
    lines = [
        f"- **Test {_safe(test.test_id)}** — {STATUS_LABELS.get(test.status, test.status.value)} : "
        f"{_safe(test.summary)} ({test.tested_elements} élément(s) analysé(s))"
    ]

    if test.status == TestStatus.ERROR:
        error = test.metadata.get("error") or test.metadata.get("error_type")
        if error:
            lines.append(f"    - Détail de l'erreur : {_safe(error)}")
    elif test.status == TestStatus.NOT_TESTED:
        missing = test.metadata.get("missing_capabilities")
        if missing:
            lines.append(f"    - Données manquantes : {_safe(', '.join(map(str, missing)))}")

    for finding in test.findings[:MAX_FINDINGS_PER_TEST]:
        line = f"    - <code>{_safe(finding.element, 160)}</code> — {_safe(finding.message)}"
        if finding.recommendation:
            line += f" *Recommandation : {_safe(finding.recommendation)}*"
        lines.append(line)

    hidden = len(test.findings) - MAX_FINDINGS_PER_TEST
    if hidden > 0:
        lines.append(f"    - … et {hidden} autre(s) observation(s).")
    return lines


def build_theme_detail(summary: ThemeSummary) -> str:
    """Construit le détail Markdown d'une thématique."""
    parts = [f"## {_safe(summary.theme.label)}", ""]

    if summary.state in (ThemeState.NOT_SELECTED, ThemeState.NOT_IMPLEMENTED):
        reason = (
            "Cette thématique n'a pas été sélectionnée pour cet audit."
            if summary.state == ThemeState.NOT_SELECTED
            else "AccessiCode ne possède pas encore de test automatisé pour cette thématique."
        )
        parts += [f"**État :** {STATE_LABELS[summary.state]}", "", reason, "", "Elle n'a donc pas été auditée."]
        return "\n".join(parts)

    if summary.score is not None:
        parts.append(f"**Score :** {summary.score} % — {priority_label(summary.score)}  ")
    parts.append(f"**État :** {STATE_LABELS[summary.state]}")

    counts = summary.criteria_counts
    parts += [
        "",
        f"{len(summary.criteria)} critère(s) examiné(s) : "
        + ", ".join(f"{counts[st]} {label.lower()}" for st, label in STATUS_LABELS.items() if counts.get(st)),
        "",
    ]
    if summary.pending_review:
        parts += [
            f"**{summary.pending_review} critère(s) restent à vérifier par une personne** "
            "et ne sont pas comptés dans le pourcentage.",
            "",
        ]

    for criterion in summary.criteria:
        parts.append(f"### Critère {_safe(criterion.criterion_id)} — {STATUS_LABELS.get(criterion.status, '')}")
        parts.append("")
        for test in criterion.tests:
            parts += _test_lines(test)
        parts.append("")

    review = [t for c in summary.criteria for t in c.tests if t.status == TestStatus.NEEDS_REVIEW]
    if review:
        parts += ["### Contrôles à vérifier manuellement", ""]
        parts += [f"- Test {_safe(t.test_id)} : {_safe(t.summary)}" for t in review]

    return "\n".join(parts)


def build_notices(notices: list[str]) -> str:
    """Avertissements de l'audit (URL ignorée, thématiques sans test…)."""
    if not notices:
        return ""
    return "\n".join(f"- {_safe(notice, 500)}" for notice in notices)


def show_detail(summaries: tuple[ThemeSummary, ...], index: int) -> str:
    if not summaries or index >= len(summaries):
        return DEFAULT_THEME_DETAIL
    return build_theme_detail(summaries[index])

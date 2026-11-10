"""
Synthèse des résultats d'audit par thématique RGAA.

Méthode de calcul du pourcentage (au niveau des critères, comme le RGAA) :

    score = critères conformes / (critères conformes + critères non conformes)

Seuls les critères tranchés automatiquement (PASS ou FAIL) entrent dans le
calcul. Les critères à vérifier, en erreur, non testés ou non applicables en
sont exclus et sont comptés à part. Sans critère tranché, aucun pourcentage
n'est produit. Ce score porte uniquement sur les tests implémentés : ce n'est
pas un taux officiel de conformité RGAA.

Ce module ne dépend ni de Gradio ni d'Ollama : il consomme uniquement
AuditResult / CriterionResult / TestResult.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from accessi_code.models.audit_result import AuditResult, CriterionResult
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.themes import RGAA_THEMES, RGAATheme, theme_number


class ThemeState(str, Enum):
    """État d'une thématique dans le rapport."""

    NOT_SELECTED = "not_selected"
    NOT_IMPLEMENTED = "not_implemented"
    SCORED = "scored"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"
    NOT_TESTED = "not_tested"
    NOT_APPLICABLE = "not_applicable"


STATUS_LABELS: dict[TestStatus, str] = {
    TestStatus.PASS: "Conforme",
    TestStatus.FAIL: "Non conforme",
    TestStatus.NEEDS_REVIEW: "À vérifier manuellement",
    TestStatus.ERROR: "Erreur d'exécution",
    TestStatus.NOT_TESTED: "Non testé",
    TestStatus.NOT_APPLICABLE: "Non applicable",
}

STATE_LABELS: dict[ThemeState, str] = {
    ThemeState.NOT_SELECTED: "Non sélectionnée",
    ThemeState.NOT_IMPLEMENTED: "Aucun test automatisé disponible",
    ThemeState.SCORED: "Évaluée",
    ThemeState.NEEDS_REVIEW: "À vérifier manuellement",
    ThemeState.ERROR: "Erreur d'exécution",
    ThemeState.NOT_TESTED: "Non testée (données manquantes)",
    ThemeState.NOT_APPLICABLE: "Non applicable",
}


@dataclass(frozen=True, slots=True)
class ThemeSummary:
    """Synthèse d'une thématique, prête à être affichée."""

    theme: RGAATheme
    state: ThemeState
    score: int | None = None
    criteria: tuple[CriterionResult, ...] = ()
    # Nombre de critères par statut agrégé.
    criteria_counts: dict[TestStatus, int] = field(default_factory=dict)

    @property
    def pending_review(self) -> int:
        """Critères qui demandent encore une intervention humaine."""
        return self.criteria_counts.get(TestStatus.NEEDS_REVIEW, 0) + self.criteria_counts.get(TestStatus.ERROR, 0)


def compute_score(criteria: list[CriterionResult] | tuple[CriterionResult, ...]) -> int | None:
    """Pourcentage de critères conformes parmi les critères tranchés, ou None."""
    passed = sum(1 for c in criteria if c.status == TestStatus.PASS)
    failed = sum(1 for c in criteria if c.status == TestStatus.FAIL)
    decided = passed + failed
    if decided == 0:
        return None
    return round(100 * passed / decided)


def _state_without_score(counts: Counter) -> ThemeState:
    if counts[TestStatus.NEEDS_REVIEW]:
        return ThemeState.NEEDS_REVIEW
    if counts[TestStatus.ERROR]:
        return ThemeState.ERROR
    if counts[TestStatus.NOT_TESTED]:
        return ThemeState.NOT_TESTED
    return ThemeState.NOT_APPLICABLE


def summarize_themes(
    result: AuditResult | None,
    *,
    selected: frozenset[int] | set[int],
    implemented: frozenset[int] | set[int],
) -> tuple[ThemeSummary, ...]:
    """
    Construit les 13 synthèses de thématique, dans l'ordre officiel.

    Args:
        result: résultat du moteur (None : aucun audit exécuté).
        selected: thématiques cochées par l'utilisateur.
        implemented: thématiques possédant au moins un test dans le registre.
    """
    by_theme: dict[int, list[CriterionResult]] = {}
    if result is not None:
        for criterion in result.criteria:
            number = theme_number(criterion.criterion_id)
            if number is not None:
                by_theme.setdefault(number, []).append(criterion)

    summaries: list[ThemeSummary] = []
    for theme in RGAA_THEMES:
        if theme.number not in selected:
            summaries.append(ThemeSummary(theme, ThemeState.NOT_SELECTED))
            continue

        criteria = by_theme.get(theme.number, [])
        if theme.number not in implemented or not criteria:
            summaries.append(ThemeSummary(theme, ThemeState.NOT_IMPLEMENTED))
            continue

        counts = Counter(c.status for c in criteria)
        score = compute_score(criteria)
        state = ThemeState.SCORED if score is not None else _state_without_score(counts)
        summaries.append(
            ThemeSummary(
                theme=theme,
                state=state,
                score=score,
                criteria=tuple(criteria),
                criteria_counts=dict(counts),
            )
        )
    return tuple(summaries)

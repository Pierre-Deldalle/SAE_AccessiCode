"""
Règles communes de décision des tests RGAA qui s'appuient sur l'IA.

Applique CONVENTIONS.md §9 à §11 en un seul endroit :
- confiance "low" ou conclusion absente → NEEDS_REVIEW, jamais PASS ni FAIL ;
- priorité des statuts lorsqu'un test traite plusieurs éléments ;
- récupération d'un analyseur dans ``services`` sans dépendre de son implémentation.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from accessi_code.ai.schemas import RelevanceAnalysis, SensoryAnalysis, StructureCandidateAnalysis
from accessi_code.ai.text_safety import read_suggestion
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
        data = asdict(analysis)
        # La proposition est réservée à la recommandation d'un verdict FAIL.
        data.pop("suggestion", None)
        return data
    if isinstance(analysis, dict):
        return dict(analysis)
    return {"value": repr(analysis)}


# ----------------------------------------------------------------------
# Soumission d'une liste d'éléments à un analyseur
# ----------------------------------------------------------------------

NO_AI_MESSAGE = "L'analyse IA n'est pas disponible : la vérification doit être faite manuellement."
LIMIT_MESSAGE = "Limite d'éléments analysés par l'IA atteinte pour ce test."
AI_ERROR_MESSAGE = "L'analyse IA a échoué."


@dataclass
class Verdict:
    """
    Conclusion pour un élément soumis à l'IA.

    reason :
        "ai" (réponse exploitable ou incertaine), "unavailable" (pas d'IA),
        "limit" (limite d'éléments atteinte) ou "error".
    """

    status: TestStatus
    explanation: str = ""
    analysis: Any | None = None
    reason: str = "ai"
    error: str | None = None

    @property
    def evidence(self) -> dict[str, Any]:
        data: dict[str, Any] = {"reason": self.reason}
        if self.analysis is not None:
            data["analysis"] = analysis_evidence(self.analysis)
        if self.error:
            data["error"] = self.error
        return data

    def message(self, fail: str, uncertain: str) -> str:
        """Message de Finding adapté au statut (avec l'explication de l'IA) ; vide si conforme."""
        if self.status in {TestStatus.PASS, TestStatus.NOT_APPLICABLE}:
            return ""
        if self.reason == "unavailable":
            return f"{uncertain} {NO_AI_MESSAGE}"
        if self.reason == "limit":
            return f"{uncertain} {LIMIT_MESSAGE}"
        if self.reason == "error":
            return AI_ERROR_MESSAGE
        head = fail if self.status is TestStatus.FAIL else uncertain
        return f"{head} {self.explanation}".strip()

    def recommendation(self, base: str) -> str:
        """Ajoute le texte de remplacement à la recommandation d'un échec établi."""
        if self.status is not TestStatus.FAIL or getattr(self.analysis, "confidence", None) == "low":
            return base
        suggestion = read_suggestion(getattr(self.analysis, "suggestion", None))
        return f"{base}\nProposition : {suggestion}" if suggestion is not None else base


async def judge_batch(
    services: Any | None,
    analyzer_name: str,
    method: str,
    kind: str,
    items: list[Any],
    *,
    verdict_field: str,
    expected_type: type,
    when_true: TestStatus = TestStatus.PASS,
    when_false: TestStatus = TestStatus.FAIL,
    decide: Callable[[Any], TestStatus] | None = None,
) -> list[Verdict]:
    """
    Soumet ``items`` à ``services.<analyzer_name>.<method>(kind, items)`` et
    retourne un Verdict par élément, dans l'ordre.

    - pas d'analyseur → NEEDS_REVIEW ;
    - au-delà de la limite d'éléments → NEEDS_REVIEW ;
    - exception ou réponse mal formée → ERROR ;
    - sinon ``decide(analysis)`` si fourni, ou la règle de confiance
      (``status_from_verdict``) appliquée à ``verdict_field``.
    """
    if not items:
        return []

    analyzer = get_analyzer(services, analyzer_name)
    if analyzer is None:
        return [Verdict(TestStatus.NEEDS_REVIEW, reason="unavailable") for _ in items]

    limit = ai_item_limit()
    judged, skipped = items[:limit], items[limit:]

    try:
        analyses = await getattr(analyzer, method)(kind, judged)
        if len(analyses) != len(judged) or not all(isinstance(item, expected_type) for item in analyses):
            raise TypeError(f"Une réponse {expected_type.__name__} par élément est attendue.")
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
        return [Verdict(TestStatus.ERROR, reason="error", error=failure) for _ in items]

    def status_of(analysis: Any) -> TestStatus:
        if decide is not None:
            return decide(analysis)
        return status_from_verdict(
            getattr(analysis, verdict_field),
            analysis.confidence,
            when_true=when_true,
            when_false=when_false,
        )

    verdicts = [
        Verdict(status_of(analysis), explanation=analysis.explanation, analysis=analysis) for analysis in analyses
    ]
    verdicts.extend(Verdict(TestStatus.NEEDS_REVIEW, reason="limit") for _ in skipped)
    return verdicts


async def judge_relevance(services: Any | None, kind: str, items: list[Any]) -> list[Verdict]:
    """Pertinence de textes (``text_relevance_analyzer``) : true → PASS, false → FAIL."""
    return await judge_batch(
        services,
        "text_relevance_analyzer",
        "analyze_relevance",
        kind,
        items,
        verdict_field="relevant",
        expected_type=RelevanceAnalysis,
    )


async def judge_structure(services: Any | None, kind: str, candidates: list[Any]) -> list[Verdict]:
    """
    Passages non balisés (``structure_analyzer``) : un passage qui devrait être
    balisé (titre, liste, citation…) → FAIL ; sinon NOT_APPLICABLE.
    """
    return await judge_batch(
        services,
        "structure_analyzer",
        "classify_candidates",
        kind,
        candidates,
        verdict_field="should_be_marked",
        expected_type=StructureCandidateAnalysis,
        when_true=TestStatus.FAIL,
        when_false=TestStatus.NOT_APPLICABLE,
    )


# ----------------------------------------------------------------------
# Caractéristiques sensorielles (RGAA 3.1, 10.9, 10.10)
# ----------------------------------------------------------------------


def sensory_status(analysis: SensoryAnalysis, *, judge_alternative: bool = False) -> TestStatus:
    """
    Statut d'un candidat sensoriel.

    - la caractéristique ne transmet pas d'information → NOT_APPLICABLE ;
    - 3.1 / 10.9 (``judge_alternative`` faux) : information donnée uniquement
      par la caractéristique → FAIL, sinon PASS ;
    - 10.10 (``judge_alternative`` vrai) : sans autre moyen, la règle n'est pas
      appliquée et le défaut relève de 10.9 → NOT_APPLICABLE ; sinon l'autre
      moyen est-il pertinent → PASS / FAIL ;
    - confiance "low" ou réponse null → NEEDS_REVIEW.
    """
    if analysis.confidence == "low" or analysis.conveys_information is None:
        return TestStatus.NEEDS_REVIEW
    if analysis.conveys_information is False:
        return TestStatus.NOT_APPLICABLE
    if analysis.relies_only_on_sensory is None:
        return TestStatus.NEEDS_REVIEW
    if not judge_alternative:
        return TestStatus.FAIL if analysis.relies_only_on_sensory else TestStatus.PASS
    if analysis.relies_only_on_sensory:
        return TestStatus.NOT_APPLICABLE
    return status_from_verdict(analysis.alternative_relevant, analysis.confidence)


async def judge_sensory(
    services: Any | None,
    kind: str,
    candidates: list[Any],
    *,
    judge_alternative: bool = False,
) -> list[Verdict]:
    """Passages de texte soumis par lots à ``sensory_analyzer.analyze_texts``."""
    return await judge_batch(
        services,
        "sensory_analyzer",
        "analyze_texts",
        kind,
        candidates,
        verdict_field="relies_only_on_sensory",
        expected_type=SensoryAnalysis,
        decide=lambda analysis: sensory_status(analysis, judge_alternative=judge_alternative),
    )


async def judge_sensory_images(
    services: Any | None,
    kind: str,
    images: list[Any],
    *,
    judge_alternative: bool = False,
) -> list[Verdict]:
    """
    Images soumises une par une à ``sensory_analyzer.analyze_image`` (VLM).

    Une erreur sur une image ne concerne que cette image (ERROR).
    """
    if not images:
        return []

    analyzer = get_analyzer(services, "sensory_analyzer")
    if analyzer is None:
        return [Verdict(TestStatus.NEEDS_REVIEW, reason="unavailable") for _ in images]

    limit = ai_item_limit()
    verdicts: list[Verdict] = []
    for image in images[:limit]:
        try:
            analysis = await analyzer.analyze_image(kind, image)
            if not isinstance(analysis, SensoryAnalysis):
                raise TypeError("Une réponse SensoryAnalysis est attendue.")
        except Exception as error:
            verdicts.append(Verdict(TestStatus.ERROR, reason="error", error=f"{type(error).__name__}: {error}"))
            continue
        verdicts.append(
            Verdict(
                sensory_status(analysis, judge_alternative=judge_alternative),
                explanation=analysis.explanation,
                analysis=analysis,
            )
        )
    verdicts.extend(Verdict(TestStatus.NEEDS_REVIEW, reason="limit") for _ in images[limit:])
    return verdicts

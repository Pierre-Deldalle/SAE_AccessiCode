"""
Socle commun des tests RGAA du thème 1 (images).

Chaque test déclare les types d'éléments qu'il vise (``kinds``), un filtre de
périmètre (``in_scope``) et la règle à appliquer à un élément (``evaluate``).
Le socle se charge du reste :

- inventaire des images (``analysis/image_elements.py``) ;
- ordre des sources de preuve : vérification humaine documentée
  (``context.image_evidence``), puis DOM, puis IA ;
- règle de confiance (confiance "low" ou réponse null → NEEDS_REVIEW) ;
- limite d'éléments soumis à l'IA ;
- agrégation des statuts et construction du ``TestResult``.
"""

from __future__ import annotations

import weakref
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import AlternativeAnalysis, ImageProfile
from accessi_code.analysis.image_elements import ImageElement, ImageKind, find_image_elements, has_image_file
from accessi_code.analysis.images import make_local_resource_loader
from accessi_code.analysis.location import locate
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.ai_decision import (
    ai_item_limit,
    count_statuses,
    get_analyzer,
    worst_status,
)
from accessi_code.rgaa.base import RGAATest

NO_AI_MESSAGE = "L'analyse IA n'est pas disponible : la vérification doit être faite manuellement."


# ----------------------------------------------------------------------
# Résultats intermédiaires
# ----------------------------------------------------------------------


@dataclass
class Judgement:
    """
    Réponse à une question posée sur un élément (« est-elle porteuse d'information ? »…).

    source :
        "evidence" (vérification humaine documentée), "dom", "ai",
        "unavailable" (pas d'IA), "budget" (limite atteinte) ou "error".
    """

    value: bool | None
    source: str
    explanation: str = ""
    confidence: str | None = None
    error: str | None = None

    @property
    def evidence(self) -> dict[str, Any]:
        data: dict[str, Any] = {"source": self.source}
        if self.explanation:
            data["explanation"] = self.explanation
        if self.confidence:
            data["confidence"] = self.confidence
        if self.error:
            data["error"] = self.error
        return data


@dataclass
class Outcome:
    """Statut d'un élément et, si nécessaire, l'observation qui l'explique."""

    status: TestStatus
    finding: Finding | None = None


@dataclass
class AIBudget:
    """Nombre d'éléments qu'un test peut encore soumettre à l'IA."""

    remaining: int

    def take(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


def outcome(
    status: TestStatus,
    element: ImageElement | None = None,
    message: str = "",
    recommendation: str | None = None,
    *,
    node: Tag | None = None,
    **evidence: Any,
) -> Outcome:
    """
    Outcome avec un Finding (sauf pour PASS et NOT_APPLICABLE sans message).

    La ligne et l'extrait HTML sont pris sur ``node`` s'il est fourni, sinon sur
    la balise de l'image elle-même.
    """
    if element is None or (status in {TestStatus.PASS, TestStatus.NOT_APPLICABLE} and not message):
        return Outcome(status)
    line, snippet = locate(node if node is not None else element.tag)
    return Outcome(
        status,
        Finding(
            element=element.key,
            message=message,
            recommendation=recommendation,
            evidence={"kind": element.kind, **evidence},
            line=line,
            snippet=snippet,
        ),
    )


def unresolved(
    element: ImageElement,
    judgement: Judgement,
    message: str,
    recommendation: str,
) -> Outcome:
    """Question restée sans réponse fiable : ERROR si l'IA a échoué, sinon NEEDS_REVIEW."""
    if judgement.source == "error":
        return outcome(
            TestStatus.ERROR,
            element,
            "L'analyse IA de l'élément a échoué.",
            "Relancer l'audit ou vérifier manuellement.",
            judgement=judgement.evidence,
        )
    detail = judgement.explanation if judgement.source == "ai" and judgement.explanation else ""
    if judgement.source == "unavailable":
        detail = NO_AI_MESSAGE
    if judgement.source == "budget":
        detail = "Limite d'éléments analysés par l'IA atteinte pour ce test."
    full_message = f"{message} {detail}".strip()
    return outcome(TestStatus.NEEDS_REVIEW, element, full_message, recommendation, judgement=judgement.evidence)


# ----------------------------------------------------------------------
# Contexte d'évaluation : preuves, profil IA, analyses d'alternative
# ----------------------------------------------------------------------


@dataclass
class Evaluation:
    """Données partagées pendant l'exécution d'un test."""

    context: AuditContext
    services: Any | None
    soup: BeautifulSoup
    elements: list[ImageElement]
    budget: AIBudget
    _profiles: dict[str, tuple[ImageProfile | None, Judgement]] = field(default_factory=dict)
    ai_calls: int = 0

    @property
    def image_analyzer(self) -> Any | None:
        return get_analyzer(self.services, "image_analyzer")

    def evidence(self, element: ImageElement, key: str) -> bool | None:
        """Valeur d'une vérification humaine documentée (``verified=True`` exigé)."""
        record = (self.context.image_evidence or {}).get(element.key)
        if not isinstance(record, dict) or record.get("verified") is not True:
            return None
        value = record.get(key)
        return value if isinstance(value, bool) else None

    async def profile(self, element: ImageElement) -> tuple[ImageProfile | None, Judgement]:
        """Profil IA de l'image (un seul appel par élément et par test, mis en cache par l'analyseur)."""
        cached = self._profiles.get(element.key)
        if cached is not None:
            return cached

        analyzer = self.image_analyzer
        if analyzer is None:
            result: tuple[ImageProfile | None, Judgement] = (None, Judgement(None, "unavailable"))
        elif not self.budget.take():
            result = (None, Judgement(None, "budget"))
        else:
            self.ai_calls += 1
            try:
                profile = await self._request_profile(analyzer, element)
                if not isinstance(profile, ImageProfile):
                    raise TypeError("ImageProfile attendu.")
                result = (profile, Judgement(None, "ai", profile.explanation, profile.confidence))
            except Exception as error:
                result = (None, Judgement(None, "error", error=f"{type(error).__name__}: {error}"))

        self._profiles[element.key] = result
        return result

    async def profile_flag(self, element: ImageElement, name: str) -> Judgement:
        """Un champ du profil IA, ramené à None si la confiance est faible."""
        profile, judgement = await self.profile(element)
        if profile is None:
            return judgement
        value = getattr(profile, name)
        if profile.confidence == "low":
            value = None
        return Judgement(value, "ai", profile.explanation, profile.confidence)

    async def information_role(self, element: ImageElement) -> Judgement:
        """L'image est-elle porteuse d'information ?"""
        verified = self.evidence(element, "information_bearing")
        if verified is not None:
            return Judgement(verified, "evidence")
        if element.functional:
            return Judgement(True, "dom", "L'image est contenue dans un lien ou un bouton.")
        return await self.profile_flag(element, "information_bearing")

    async def decorative(self, element: ImageElement) -> Judgement:
        """L'image est-elle décorative ? Le marquage du code fait foi (RGAA 1.2)."""
        verified = self.evidence(element, "information_bearing")
        if verified is not None:
            return Judgement(not verified, "evidence")
        if element.marked_decorative and not element.functional:
            return Judgement(True, "dom", "L'image est déclarée décorative dans le code.")
        role = await self.information_role(element)
        return Judgement(
            None if role.value is None else not role.value, role.source, role.explanation, role.confidence, role.error
        )

    async def captcha(self, element: ImageElement) -> Judgement:
        """L'image est-elle un CAPTCHA ou une image-test ?"""
        verified = self.evidence(element, "is_captcha")
        if verified is not None:
            return Judgement(verified, "evidence")
        if element.captcha_marker:
            return Judgement(True, "dom", "Le code désigne l'image comme un CAPTCHA.")
        judgement = await self.profile_flag(element, "is_captcha")
        # Sans réponse fiable, l'image n'est pas considérée comme un CAPTCHA :
        # les critères 1.4 et 1.5 ne visent que les CAPTCHA identifiés.
        return judgement

    async def alternative(self, element: ImageElement, mode: str) -> tuple[AlternativeAnalysis | None, Judgement]:
        """Analyse IA de l'alternative textuelle (pertinence, concision, ou nature du CAPTCHA)."""
        analyzer = self.image_analyzer
        if analyzer is None:
            return None, Judgement(None, "unavailable")
        if not self.budget.take():
            return None, Judgement(None, "budget")
        self.ai_calls += 1
        try:
            analysis = await analyzer.analyze_alternative(
                element_html=element.html,
                alternative=element.alternatives_text(),
                context=element.context_text,
                image=element.image_info if has_image_file(element) else None,
                mode=mode,
            )
            if not isinstance(analysis, AlternativeAnalysis):
                raise TypeError("AlternativeAnalysis attendu.")
        except Exception as error:
            return None, Judgement(None, "error", error=f"{type(error).__name__}: {error}")
        return analysis, Judgement(None, "ai", analysis.explanation, analysis.confidence)

    async def _request_profile(self, analyzer: Any, element: ImageElement) -> ImageProfile:
        if has_image_file(element):
            try:
                return await analyzer.profile(element.image_info)
            except FileNotFoundError, OSError:
                pass
        return await analyzer.profile_element(element.html, element.context_text)


# ----------------------------------------------------------------------
# Classe de base des tests du thème 1
# ----------------------------------------------------------------------


class ImageTest(RGAATest):
    """Test RGAA du thème 1 appliqué à chaque élément graphique concerné."""

    criterion_id: ClassVar[str]
    kinds: ClassVar[tuple[ImageKind, ...]]

    required_capabilities = frozenset({Capability.DOM})
    optional_capabilities = frozenset({Capability.IMAGES})

    empty_summary: ClassVar[str] = "Aucun élément concerné par ce test."

    def in_scope(self, element: ImageElement) -> bool:
        """Filtre déterministe du périmètre, avant toute évaluation."""
        return True

    @abstractmethod
    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        """Applique la règle RGAA à un élément."""
        raise NotImplementedError

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        all_elements = image_elements(context)
        elements = [element for element in all_elements if element.kind in self.kinds and self.in_scope(element)]

        if not elements:
            return TestResult(self.test_id, self.criterion_id, TestStatus.NOT_APPLICABLE, self.empty_summary)

        evaluation = Evaluation(
            context=context,
            services=services,
            soup=context.dom,
            elements=all_elements,
            budget=AIBudget(ai_item_limit()),
        )

        outcomes = [await self.evaluate(element, evaluation) for element in elements]
        return build_result(self, outcomes, evaluation)


def build_result(test: ImageTest, outcomes: list[Outcome], evaluation: Evaluation) -> TestResult:
    statuses = [item.status for item in outcomes]
    counts = count_statuses(statuses)
    status = worst_status(statuses)
    tested = sum(1 for item in statuses if item is not TestStatus.NOT_APPLICABLE)

    if status is TestStatus.NOT_APPLICABLE:
        summary = test.empty_summary
    else:
        summary = (
            f"{tested} élément(s) concerné(s) : {counts['pass']} conforme(s), "
            f"{counts['fail']} non conforme(s), {counts['needs_review']} à vérifier"
            + (f", {counts['error']} erreur(s)" if counts["error"] else "")
            + "."
        )

    return TestResult(
        test_id=test.test_id,
        criterion_id=test.criterion_id,
        status=status,
        summary=summary,
        findings=[item.finding for item in outcomes if item.finding is not None],
        tested_elements=tested,
        metadata={
            "candidates": len(outcomes),
            "statuses": counts,
            "ai_calls": evaluation.ai_calls,
            "ai_available": evaluation.image_analyzer is not None,
        },
    )


# ----------------------------------------------------------------------
# Inventaire mis en cache par document (59 tests lisent le même DOM)
# ----------------------------------------------------------------------

_INVENTORY: dict[int, tuple[weakref.ref, list[ImageElement]]] = {}
_INVENTORY_MAX = 8


def image_elements(context: AuditContext) -> list[ImageElement]:
    """Inventaire des images du document principal, calculé une fois par DOM."""
    dom = context.dom
    cached = _INVENTORY.get(id(dom))
    if cached is not None and cached[0]() is dom:
        return cached[1]

    base_dir = context.html_path.parent if context.html_path is not None else None
    elements = find_image_elements(
        dom,
        base_dir=base_dir,
        resource_loader=make_local_resource_loader(base_dir) if base_dir is not None else None,
    )

    if len(_INVENTORY) >= _INVENTORY_MAX:
        _INVENTORY.clear()
    try:
        _INVENTORY[id(dom)] = (weakref.ref(dom), elements)
    except TypeError:
        pass
    return elements

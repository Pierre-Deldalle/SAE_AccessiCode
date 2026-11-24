"""
Socle des tests RGAA sur les caractéristiques sensorielles : couleur (3.1),
forme, taille et position (10.9 et 10.10).

Chaque test choisit ses candidats (``analysis/sensory.py``) ; l'IA
(``sensory_analyzer``) juge ensuite chaque candidat :

- la caractéristique ne transmet pas d'information → NOT_APPLICABLE ;
- 3.1 / 10.9 : l'information repose uniquement sur elle → FAIL, sinon PASS ;
- 10.10 : l'autre moyen qui transmet l'information est-il pertinent ?
- confiance faible, réponse null ou pas d'IA → NEEDS_REVIEW ; exception → ERROR.

Les médias (vidéo, son, objets embarqués) ne peuvent pas être analysés par
l'IA : ils sont signalés pour vérification manuelle.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import SensoryCandidate
from accessi_code.analysis.image_elements import ImageElement, has_image_file
from accessi_code.analysis.sensory import Candidate, identifier, media_elements
from accessi_code.analysis.structure import is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import Verdict, judge_sensory, judge_sensory_images
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_01_images._common import image_elements


class SensoryTest(RGAATest):
    """Paramètres communs : type d'analyse, messages et périmètre."""

    kind: ClassVar[str]
    judge_alternative: ClassVar[bool] = False
    locate_findings: ClassVar[bool] = False

    noun: ClassVar[str] = "élément(s)"
    empty_summary: ClassVar[str]
    fail_message: ClassVar[str]
    uncertain_message: ClassVar[str]
    recommendation: ClassVar[str]

    required_capabilities = frozenset({Capability.DOM})

    def _dom(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom

    def _outcome(self, element: str, verdict: Verdict, *, node: Tag, **evidence: Any) -> Outcome:
        return make_outcome(
            verdict.status,
            element,
            verdict.message(self.fail_message, self.uncertain_message),
            verdict.recommendation(self.recommendation) if self.kind == "shape_size_position" else self.recommendation,
            node=node if self.locate_findings else None,
            **evidence,
            **verdict.evidence,
        )

    def _result(self, outcomes: list[Outcome]) -> TestResult:
        return build_result(self, outcomes, empty_summary=self.empty_summary, noun=self.noun)


class SensoryTextTest(SensoryTest):
    """Passages de texte ou éléments repérés dans le DOM, jugés par lots."""

    @abstractmethod
    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        raise NotImplementedError

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._dom(context)
        candidates = self.candidates(context, soup)
        if not candidates:
            return not_applicable(self, self.empty_summary)

        items = [SensoryCandidate(item.text, item.html, item.context) for item in candidates]
        verdicts = await judge_sensory(services, self.kind, items, judge_alternative=self.judge_alternative)
        return self._result(
            [
                self._outcome(item.identifier, verdict, node=item.tag, text=item.text[:300], **item.evidence)
                for item, verdict in zip(candidates, verdicts, strict=True)
            ]
        )


def informative_images(context: AuditContext) -> list[ImageElement]:
    """Images qui peuvent porter une information : celles déclarées décoratives sont exclues (RGAA 1.2)."""
    return [
        element
        for element in image_elements(context)
        if (element.functional or not element.marked_decorative) and not is_hidden(element.tag)
    ]


class SensoryImageTest(SensoryTest):
    """
    Images porteuses d'information : le VLM observe l'image lorsqu'un fichier
    est disponible ; sinon le LLM lit le code (SVG, canvas…) et les alternatives.
    """

    noun = "image(s)"
    optional_capabilities = frozenset({Capability.IMAGES})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        self._dom(context)
        images = informative_images(context)
        if not images:
            return not_applicable(self, self.empty_summary)

        with_file = [element for element in images if has_image_file(element)]
        without_file = [element for element in images if not has_image_file(element)]

        file_verdicts = await judge_sensory_images(
            services,
            self.kind,
            [element.image_info for element in with_file],
            judge_alternative=self.judge_alternative,
        )
        code_verdicts = await judge_sensory(
            services,
            self.kind,
            [
                SensoryCandidate(
                    element.alternatives_text() or "(aucune alternative textuelle)",
                    element.html[:400],
                    element.context_text,
                )
                for element in without_file
            ],
            judge_alternative=self.judge_alternative,
        )
        verdicts = {id(element): verdict for element, verdict in zip(with_file, file_verdicts, strict=True)}
        verdicts.update({id(element): verdict for element, verdict in zip(without_file, code_verdicts, strict=True)})

        return self._result(
            [
                self._outcome(
                    identifier(element.tag, index),
                    verdicts[id(element)],
                    node=element.tag,
                    source="image" if has_image_file(element) else "code",
                    alternatives=element.alternatives_text(),
                )
                for index, element in enumerate(images)
            ]
        )


class SensoryMediaTest(SensoryTest):
    """Médias dont le contenu ne peut pas être analysé : vérification manuelle, sans IA."""

    media: ClassVar[tuple[str, ...]]
    noun = "média(s)"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._dom(context)
        elements = media_elements(soup, self.media)
        if not elements:
            return not_applicable(self, self.empty_summary)

        return self._result(
            [
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    identifier(tag, index),
                    self.uncertain_message,
                    self.recommendation,
                    node=tag if self.locate_findings else None,
                    reason="media_not_analyzable",
                )
                for index, tag in enumerate(elements)
            ]
        )

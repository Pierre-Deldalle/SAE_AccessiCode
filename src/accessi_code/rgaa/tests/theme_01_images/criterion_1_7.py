"""
RGAA 4.1.2 — critère 1.7 : pour chaque image porteuse d'information ayant une
description détaillée, cette description est-elle pertinente ?

Chaque description disponible (longdesc chargée, passage adjacent, cible d'un
lien, aria-describedby…) est comparée au contenu visuel de l'image par
l'analyseur d'images (VLM + LLM), comme le faisait l'ancien test 1.7.1.
Sans fichier image exploitable (svg en ligne, canvas), la comparaison visuelle
est impossible : vérification humaine.
"""

from __future__ import annotations

from accessi_code.ai.schemas import DescriptionAnalysis
from accessi_code.analysis.image_elements import ImageElement, has_image_file
from accessi_code.analysis.images import DetailedDescription
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import Verdict, analysis_evidence, status_from_verdict, worst_status
from accessi_code.rgaa.tests.theme_01_images._common import (
    NO_AI_MESSAGE,
    Evaluation,
    ImageTest,
    Outcome,
    outcome,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_6 import present_mechanisms

RECOMMENDATION = "Rédiger une description détaillée qui restitue toute l'information de l'image."


class _DescriptionRelevanceTest(ImageTest):
    """Pertinence des descriptions détaillées d'une image."""

    criterion_id = "1.7"
    empty_summary = "Aucune image avec description détaillée."

    def in_scope(self, element: ImageElement) -> bool:
        return not element.marked_decorative and bool(present_mechanisms(element))

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        verified = evaluation.evidence(element, "description_relevant")
        if verified is True:
            return outcome(TestStatus.PASS)
        if verified is False:
            return outcome(TestStatus.FAIL, element, "La description détaillée n'est pas pertinente.", RECOMMENDATION)

        mechanisms = present_mechanisms(element)
        descriptions = [item for item in element.available_descriptions if item.source in mechanisms]
        if not descriptions:
            return outcome(
                TestStatus.NEEDS_REVIEW,
                element,
                "La description détaillée n'a pas pu être lue (ressource externe, cible absente ou contenu dynamique).",
                "Vérifier manuellement le contenu et la pertinence de la description.",
                errors=[description.error for description in element.descriptions if description.error],
            )

        analyzer = evaluation.image_analyzer
        if analyzer is None or not has_image_file(element):
            reason = NO_AI_MESSAGE if analyzer is None else "Le contenu visuel de l'image n'est pas analysable."
            return outcome(
                TestStatus.NEEDS_REVIEW,
                element,
                f"La pertinence de la description détaillée doit être vérifiée. {reason}",
                "Comparer la description au contenu de l'image.",
                descriptions=[_summary(description) for description in descriptions],
            )

        outcomes = [await self._judge(element, description, evaluation) for description in descriptions]
        relevant_outcomes = [item for item in outcomes if item.status is not TestStatus.NOT_APPLICABLE]
        if not relevant_outcomes:
            return outcome(TestStatus.NOT_APPLICABLE)

        status = worst_status(item.status for item in relevant_outcomes)
        for item in relevant_outcomes:
            if item.status is status:
                return item
        return relevant_outcomes[0]

    async def _judge(self, element: ImageElement, description: DetailedDescription, evaluation: Evaluation) -> Outcome:
        if not evaluation.budget.take():
            return outcome(
                TestStatus.NEEDS_REVIEW,
                element,
                "Limite d'éléments analysés par l'IA atteinte pour ce test.",
                "Comparer la description au contenu de l'image.",
            )
        evaluation.ai_calls += 1
        try:
            analysis = await evaluation.image_analyzer.analyze(element.image_info, description)
            if not isinstance(analysis, DescriptionAnalysis):
                raise TypeError("DescriptionAnalysis attendu.")
        except Exception as error:
            return outcome(
                TestStatus.ERROR,
                element,
                "L'analyse IA de la description détaillée a échoué.",
                "Relancer l'audit ou vérifier manuellement.",
                error=f"{type(error).__name__}: {error}",
                description=_summary(description),
            )

        if analysis.is_detailed_description is False:
            # Le contenu associé n'est pas une description détaillée de l'image.
            return outcome(TestStatus.NOT_APPLICABLE)

        status = status_from_verdict(analysis.relevant, analysis.confidence)
        if status is TestStatus.PASS:
            return outcome(TestStatus.PASS)
        message = (
            "La description détaillée n'est pas pertinente."
            if status is TestStatus.FAIL
            else "La pertinence de la description détaillée reste incertaine."
        )
        return outcome(
            status,
            element,
            f"{message} {analysis.explanation}".strip(),
            Verdict(status, analysis=analysis).recommendation(RECOMMENDATION),
            description=_summary(description),
            analysis=analysis_evidence(analysis),
        )


def _summary(description: DetailedDescription) -> dict[str, str | None]:
    return {"source": description.source, "reference": description.reference, "content": description.content[:300]}


class Test171(_DescriptionRelevanceTest):
    """1.7.1 : image (img ou role="img")."""

    test_id = "1.7.1"
    kinds = ("img", "role_img")


class Test172(_DescriptionRelevanceTest):
    """1.7.2 : bouton de type image."""

    test_id = "1.7.2"
    kinds = ("input",)


class Test173(_DescriptionRelevanceTest):
    """1.7.3 : image objet (object)."""

    test_id = "1.7.3"
    kinds = ("object",)


class Test174(_DescriptionRelevanceTest):
    """1.7.4 : image embarquée (embed)."""

    test_id = "1.7.4"
    kinds = ("embed",)


class Test175(_DescriptionRelevanceTest):
    """1.7.5 : image vectorielle (svg)."""

    test_id = "1.7.5"
    kinds = ("svg",)


class Test176(_DescriptionRelevanceTest):
    """1.7.6 : image bitmap (canvas)."""

    test_id = "1.7.6"
    kinds = ("canvas",)

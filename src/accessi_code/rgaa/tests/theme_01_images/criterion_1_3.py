"""
RGAA 4.1.2 — critère 1.3 : pour chaque image porteuse d'information ayant une
alternative textuelle, cette alternative est-elle pertinente (hors cas
particuliers) ?

Périmètre : images porteuses d'information ayant au moins une alternative,
hors CAPTCHA et images-tests (traités par le critère 1.4).
La pertinence et la concision sont jugées par l'IA, en comparant
l'alternative au contenu visuel lorsque le fichier image est disponible.
"""

from __future__ import annotations

from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import Verdict, analysis_evidence, status_from_verdict
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Outcome,
    outcome,
    unresolved,
)


class _AlternativeRelevanceTest(ImageTest):
    """Pertinence de l'alternative d'une image porteuse d'information."""

    criterion_id = "1.3"
    empty_summary = "Aucune image avec alternative textuelle concernée par ce test."

    # Champ de AlternativeAnalysis jugé par ce test.
    verdict_field = "relevant"
    evidence_key = "alternative_relevant"
    fail_message = "L'alternative textuelle n'est pas pertinente."
    uncertain_message = "La pertinence de l'alternative reste incertaine."
    recommendation = "Rédiger une alternative qui transmet la même information que l'image (ou sa fonction)."

    def in_scope(self, element: ImageElement) -> bool:
        return bool(element.alternatives) and not element.marked_decorative

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        captcha = await evaluation.captcha(element)
        if captcha.value is True:
            return outcome(TestStatus.NOT_APPLICABLE)

        role = await evaluation.information_role(element)
        if role.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if role.value is None:
            return unresolved(
                element,
                role,
                "Le rôle informatif de l'image n'a pas pu être établi.",
                "Vérifier si l'image est porteuse d'information, puis la pertinence de son alternative.",
            )

        verified = evaluation.evidence(element, self.evidence_key)
        if verified is True:
            return outcome(TestStatus.PASS)
        if verified is False:
            return outcome(TestStatus.FAIL, element, self.fail_message, self.recommendation, source="evidence")

        analysis, judgement = await evaluation.alternative(element, "alternative")
        if analysis is None:
            return unresolved(
                element,
                judgement,
                "La pertinence de l'alternative n'a pas pu être évaluée.",
                "Comparer l'alternative au contenu de l'image.",
            )

        status = status_from_verdict(getattr(analysis, self.verdict_field), analysis.confidence)
        if status is TestStatus.PASS:
            return outcome(TestStatus.PASS)
        message = self.fail_message if status is TestStatus.FAIL else self.uncertain_message
        return outcome(
            status,
            element,
            f"{message} {analysis.explanation}".strip(),
            Verdict(status, analysis=analysis).recommendation(self.recommendation),
            alternatives=element.alternatives,
            analysis=analysis_evidence(analysis),
        )


class Test131(_AlternativeRelevanceTest):
    """1.3.1 : image (img ou role="img")."""

    test_id = "1.3.1"
    kinds = ("img", "role_img")


class Test132(_AlternativeRelevanceTest):
    """1.3.2 : zone (area) d'une image réactive."""

    test_id = "1.3.2"
    kinds = ("area",)


class Test133(_AlternativeRelevanceTest):
    """1.3.3 : bouton de type image (input type="image")."""

    test_id = "1.3.3"
    kinds = ("input",)
    recommendation = "Rédiger une alternative qui décrit l'action déclenchée par le bouton."


class Test134(_AlternativeRelevanceTest):
    """1.3.4 : image objet (object)."""

    test_id = "1.3.4"
    kinds = ("object",)


class Test135(_AlternativeRelevanceTest):
    """1.3.5 : image embarquée (embed)."""

    test_id = "1.3.5"
    kinds = ("embed",)


class Test136(_AlternativeRelevanceTest):
    """1.3.6 : image vectorielle (svg)."""

    test_id = "1.3.6"
    kinds = ("svg",)


class Test137(_AlternativeRelevanceTest):
    """1.3.7 : image bitmap (canvas)."""

    test_id = "1.3.7"
    kinds = ("canvas",)


class Test138(ImageTest):
    """
    1.3.8 : le contenu alternatif placé entre <canvas> et </canvas> est-il
    correctement restitué par les technologies d'assistance ?

    La restitution ne peut être constatée qu'avec une technologie d'assistance :
    sans vérification documentée (``correctly_exposed``), le test reste à vérifier.
    """

    test_id = "1.3.8"
    criterion_id = "1.3"
    kinds = ("canvas",)
    empty_summary = "Aucun canvas avec contenu alternatif."

    def in_scope(self, element: ImageElement) -> bool:
        return "content" in element.alternatives and not element.marked_decorative

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        verified = evaluation.evidence(element, "correctly_exposed")
        if verified is True:
            return outcome(TestStatus.PASS)
        if verified is False:
            return outcome(
                TestStatus.FAIL,
                element,
                "Le contenu alternatif du canvas n'est pas restitué par les technologies d'assistance.",
                "Rendre le contenu de repli accessible (texte visible par l'arbre d'accessibilité).",
            )
        return outcome(
            TestStatus.NEEDS_REVIEW,
            element,
            "La restitution du contenu alternatif du canvas doit être vérifiée avec un lecteur d'écran.",
            "Vérifier avec un lecteur d'écran que le contenu entre <canvas> et </canvas> est annoncé.",
            content=element.alternatives["content"][:200],
        )


class Test139(_AlternativeRelevanceTest):
    """1.3.9 : l'alternative est-elle courte et concise (hors cas particuliers) ?"""

    test_id = "1.3.9"
    kinds = ("img", "role_img", "area", "input", "object", "embed", "svg", "canvas")
    verdict_field = "concise"
    evidence_key = "concise"
    fail_message = "L'alternative textuelle n'est pas courte et concise."
    uncertain_message = "La concision de l'alternative reste incertaine."
    recommendation = "Raccourcir l'alternative ; placer les détails dans une description détaillée (critère 1.6)."

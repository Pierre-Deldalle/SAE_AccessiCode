"""
RGAA 4.1.2 — critère 1.4 : pour chaque image utilisée comme CAPTCHA ou comme
image-test, ayant une alternative textuelle, cette alternative permet-elle
d'identifier la nature et la fonction de l'image ?

Un CAPTCHA est identifié par le code (« captcha » dans id, class, src…), par
une vérification documentée ou par le profil IA de l'image.
"""

from __future__ import annotations

from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import analysis_evidence, status_from_verdict
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Outcome,
    outcome,
    unresolved,
)


class _CaptchaAlternativeTest(ImageTest):
    """Alternative d'un CAPTCHA indiquant sa nature et sa fonction."""

    criterion_id = "1.4"
    empty_summary = "Aucun CAPTCHA ou image-test avec alternative textuelle."
    recommendation = "Indiquer dans l'alternative la nature et la fonction de l'image (par ex. « Code de sécurité »)."

    def in_scope(self, element: ImageElement) -> bool:
        return bool(element.alternatives)

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        captcha = await evaluation.captcha(element)
        if captcha.value is not True:
            return outcome(TestStatus.NOT_APPLICABLE)

        verified = evaluation.evidence(element, "captcha_alternative_relevant")
        if verified is not None:
            return outcome(
                TestStatus.PASS if verified else TestStatus.FAIL,
                element,
                "" if verified else "L'alternative n'indique pas la nature et la fonction du CAPTCHA.",
                self.recommendation,
                source="evidence",
            )

        analysis, judgement = await evaluation.alternative(element, "captcha")
        if analysis is None:
            return unresolved(
                element,
                judgement,
                "L'alternative du CAPTCHA n'a pas pu être évaluée.",
                "Vérifier que l'alternative indique la nature et la fonction de l'image.",
            )

        status = status_from_verdict(analysis.relevant, analysis.confidence)
        if status is TestStatus.PASS:
            return outcome(TestStatus.PASS)
        message = (
            "L'alternative n'indique pas la nature et la fonction du CAPTCHA."
            if status is TestStatus.FAIL
            else "La pertinence de l'alternative du CAPTCHA reste incertaine."
        )
        return outcome(
            status,
            element,
            f"{message} {analysis.explanation}".strip(),
            self.recommendation,
            alternatives=element.alternatives,
            analysis=analysis_evidence(analysis),
        )


class Test141(_CaptchaAlternativeTest):
    """1.4.1 : image (img ou role="img")."""

    test_id = "1.4.1"
    kinds = ("img", "role_img")


class Test142(_CaptchaAlternativeTest):
    """1.4.2 : zone (area) d'une image réactive."""

    test_id = "1.4.2"
    kinds = ("area",)


class Test143(_CaptchaAlternativeTest):
    """1.4.3 : bouton de type image."""

    test_id = "1.4.3"
    kinds = ("input",)


class Test144(_CaptchaAlternativeTest):
    """1.4.4 : image objet (object)."""

    test_id = "1.4.4"
    kinds = ("object",)


class Test145(_CaptchaAlternativeTest):
    """1.4.5 : image embarquée (embed)."""

    test_id = "1.4.5"
    kinds = ("embed",)


class Test146(_CaptchaAlternativeTest):
    """1.4.6 : image vectorielle (svg)."""

    test_id = "1.4.6"
    kinds = ("svg",)


class Test147(_CaptchaAlternativeTest):
    """1.4.7 : image bitmap (canvas)."""

    test_id = "1.4.7"
    kinds = ("canvas",)

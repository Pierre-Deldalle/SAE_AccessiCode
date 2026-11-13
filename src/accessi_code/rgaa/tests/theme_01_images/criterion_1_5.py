"""
RGAA 4.1.2 — critère 1.5 : pour chaque image utilisée comme CAPTCHA, une
solution d'accès alternatif au contenu ou à la fonction du CAPTCHA est-elle
présente ?

Le DOM fournit les candidats (CAPTCHA audio, liens ou boutons du type
« écouter », « nous contacter »…). L'IA juge si un candidat donne réellement
accès à la fonctionnalité sans voir l'image. Aucun candidat dans la page :
non-conformité.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceAnalysis, RelevanceItem
from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import get_analyzer, status_from_verdict
from accessi_code.rgaa.tests.theme_01_images._common import (
    NO_AI_MESSAGE,
    Evaluation,
    ImageTest,
    Judgement,
    Outcome,
    outcome,
    unresolved,
)

_ALTERNATIVE_ACCESS = re.compile(
    r"audio|écouter|ecouter|sonore|vocal|version texte|sans captcha|autre moyen|contact|téléphon|telephon|"
    r"assistance|courriel|e-mail|mail|appel",
    re.IGNORECASE,
)

_MAX_CANDIDATES = 8


def alternative_access_candidates(element: ImageElement, soup: BeautifulSoup) -> list[Tag]:
    """Éléments susceptibles d'offrir une autre voie que le CAPTCHA graphique."""
    candidates: list[Tag] = []
    for tag in soup.find_all(["audio", "a", "button"]):
        if tag is element.tag or element.tag in tag.descendants:
            continue
        if tag.name == "audio":
            candidates.append(tag)
            continue
        label = " ".join([tag.get_text(" ", strip=True), str(tag.get("aria-label") or ""), str(tag.get("title") or "")])
        if _ALTERNATIVE_ACCESS.search(label) or _ALTERNATIVE_ACCESS.search(str(tag.get("href") or "")):
            candidates.append(tag)
    return candidates[:_MAX_CANDIDATES]


def _item(tag: Tag, element: ImageElement) -> RelevanceItem:
    text = tag.get_text(" ", strip=True) or str(tag.get("aria-label") or tag.get("title") or "")
    if tag.name == "audio":
        text = text or "Lecteur audio"
    return RelevanceItem(
        text=text,
        element_html=str(tag)[:400],
        context=element.context_text,
        details={"href": str(tag.get("href") or ""), "captcha": element.alternatives_text() or element.html[:200]},
    )


class _CaptchaAccessTest(ImageTest):
    """Autre forme de CAPTCHA ou autre accès à la fonctionnalité protégée."""

    criterion_id = "1.5"
    empty_summary = "Aucun CAPTCHA identifié."
    recommendation = (
        "Proposer un CAPTCHA non graphique (audio, question logique) ou une autre voie d'accès "
        "(contact par téléphone ou courriel)."
    )

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        captcha = await evaluation.captcha(element)
        if captcha.value is not True:
            return outcome(TestStatus.NOT_APPLICABLE)

        verified = evaluation.evidence(element, "accessible_captcha_alternative")
        if verified is not None:
            return outcome(
                TestStatus.PASS if verified else TestStatus.FAIL,
                element,
                "" if verified else "Aucune solution d'accès alternative au CAPTCHA.",
                self.recommendation,
                source="evidence",
            )

        candidates = alternative_access_candidates(element, evaluation.soup)
        if not candidates:
            return outcome(
                TestStatus.FAIL,
                element,
                "Aucune autre forme de CAPTCHA ni autre solution d'accès n'a été trouvée dans la page.",
                self.recommendation,
            )

        analyzer = get_analyzer(evaluation.services, "text_relevance_analyzer")
        if analyzer is None:
            return outcome(
                TestStatus.NEEDS_REVIEW,
                element,
                f"Des alternatives possibles ont été trouvées ; leur efficacité doit être vérifiée. {NO_AI_MESSAGE}",
                self.recommendation,
                candidates=[str(tag)[:200] for tag in candidates],
            )
        if not evaluation.budget.take():
            return outcome(
                TestStatus.NEEDS_REVIEW,
                element,
                "Limite d'éléments analysés par l'IA atteinte pour ce test.",
                self.recommendation,
            )

        evaluation.ai_calls += 1
        try:
            analyses = await analyzer.analyze_relevance(
                "captcha_alternative", [_item(tag, element) for tag in candidates]
            )
            if len(analyses) != len(candidates) or not all(isinstance(a, RelevanceAnalysis) for a in analyses):
                raise TypeError("Une RelevanceAnalysis par candidat est attendue.")
        except Exception as error:
            failure = Judgement(None, "error", error=f"{type(error).__name__}: {error}")
            return unresolved(element, failure, "", self.recommendation)

        statuses = [status_from_verdict(analysis.relevant, analysis.confidence) for analysis in analyses]
        if TestStatus.PASS in statuses:
            return outcome(TestStatus.PASS)

        details = [
            {"candidate": str(tag)[:200], "relevant": analysis.relevant, "explanation": analysis.explanation}
            for tag, analysis in zip(candidates, analyses, strict=True)
        ]
        if all(status is TestStatus.FAIL for status in statuses):
            return outcome(
                TestStatus.FAIL,
                element,
                "Les liens et contenus trouvés ne constituent pas une alternative au CAPTCHA.",
                self.recommendation,
                candidates=details,
            )
        return outcome(
            TestStatus.NEEDS_REVIEW,
            element,
            "L'efficacité des alternatives possibles au CAPTCHA reste incertaine.",
            self.recommendation,
            candidates=details,
        )


class Test151(_CaptchaAccessTest):
    """1.5.1 : image (img, area, object, embed, svg, canvas ou role="img") utilisée comme CAPTCHA."""

    test_id = "1.5.1"
    kinds = ("img", "role_img", "area", "object", "embed", "svg", "canvas")


class Test152(_CaptchaAccessTest):
    """1.5.2 : bouton associé à une image (input type="image") utilisée comme CAPTCHA."""

    test_id = "1.5.2"
    kinds = ("input",)

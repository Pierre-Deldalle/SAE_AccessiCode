"""
RGAA 4.1.2 — critère 1.8 : chaque image texte porteuse d'information, en
l'absence d'un mécanisme de remplacement, doit si possible être remplacée par
du texte stylé. Cette règle est-elle respectée (hors cas particuliers) ?

Cas particuliers (non applicables) : logos et dénominations commerciales,
CAPTCHA et images-tests, texte réel d'un svg (éléments <text>).
L'IA établit si l'image contient du texte et si ce texte pourrait être rendu
en texte stylé (CSS) sans perte.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from accessi_code.analysis.image_elements import ImageElement, svg_has_only_real_text
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Judgement,
    Outcome,
    outcome,
    unresolved,
)

_REPLACEMENT_MECHANISM = re.compile(
    r"version texte|remplacer les images|afficher (le|en) texte|sans images|images? en texte", re.IGNORECASE
)

RECOMMENDATION = "Remplacer l'image texte par du texte mis en forme en CSS."


def has_replacement_mechanism(soup: BeautifulSoup) -> bool:
    """Un lien ou bouton de la page permet-il de remplacer les images texte par du texte ?"""
    for tag in soup.find_all(["a", "button"]):
        label = " ".join([tag.get_text(" ", strip=True), str(tag.get("aria-label") or ""), str(tag.get("title") or "")])
        if _REPLACEMENT_MECHANISM.search(label):
            return True
    return False


class _TextImageTest(ImageTest):
    """Image texte remplaçable par du texte stylé."""

    criterion_id = "1.8"
    empty_summary = "Aucune image concernée par ce test."

    def in_scope(self, element: ImageElement) -> bool:
        return not element.marked_decorative

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if element.logo_marker:
            return outcome(TestStatus.NOT_APPLICABLE)
        captcha = await evaluation.captcha(element)
        if captcha.value is True:
            return outcome(TestStatus.NOT_APPLICABLE)

        role = await evaluation.information_role(element)
        if role.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)

        contains_text = self._flag(evaluation, element, "is_text_image")
        if contains_text is None:
            contains_text = await evaluation.profile_flag(element, "contains_text")
        if contains_text.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if contains_text.value is None or role.value is None:
            return unresolved(
                element,
                contains_text if contains_text.value is None else role,
                "Impossible d'établir si l'image est une image texte porteuse d'information.",
                "Vérifier si l'image contient du texte ; si oui, le remplacer par du texte stylé.",
            )

        replaceable = self._flag(evaluation, element, "text_replaceable")
        if replaceable is None:
            replaceable = await evaluation.profile_flag(element, "text_replaceable")
        if replaceable.value is False:
            # Effet graphique impossible en CSS, texte faisant partie d'une photo… : règle respectée.
            return outcome(TestStatus.PASS)
        if replaceable.value is None:
            return unresolved(
                element,
                replaceable,
                "Impossible d'établir si le texte de l'image peut être obtenu avec du texte stylé.",
                RECOMMENDATION,
            )

        if has_replacement_mechanism(evaluation.soup):
            return outcome(TestStatus.PASS)

        profile, _ = await evaluation.profile(element)
        text = profile.text_content if profile is not None else ""
        return outcome(
            TestStatus.FAIL,
            element,
            "L'image contient du texte qui pourrait être remplacé par du texte stylé"
            + (f" (« {text[:120]} »)." if text else "."),
            RECOMMENDATION,
            analysis=replaceable.evidence,
        )

    @staticmethod
    def _flag(evaluation: Evaluation, element: ImageElement, key: str) -> Judgement | None:
        verified = evaluation.evidence(element, key)
        return None if verified is None else Judgement(verified, "evidence")


class Test181(_TextImageTest):
    """1.8.1 : image (img ou role="img")."""

    test_id = "1.8.1"
    kinds = ("img", "role_img")


class Test182(_TextImageTest):
    """1.8.2 : bouton de type image."""

    test_id = "1.8.2"
    kinds = ("input",)


class Test183(_TextImageTest):
    """1.8.3 : image objet (object)."""

    test_id = "1.8.3"
    kinds = ("object",)


class Test184(_TextImageTest):
    """1.8.4 : image embarquée (embed)."""

    test_id = "1.8.4"
    kinds = ("embed",)


class Test185(_TextImageTest):
    """1.8.5 : image bitmap (canvas)."""

    test_id = "1.8.5"
    kinds = ("canvas",)


class Test186(_TextImageTest):
    """1.8.6 : image vectorielle (svg) dont le texte n'est pas fait d'éléments <text>."""

    test_id = "1.8.6"
    kinds = ("svg",)

    def in_scope(self, element: ImageElement) -> bool:
        # Le texte réel d'un svg (<text>) n'est pas une image texte.
        return super().in_scope(element) and not svg_has_only_real_text(element.tag)

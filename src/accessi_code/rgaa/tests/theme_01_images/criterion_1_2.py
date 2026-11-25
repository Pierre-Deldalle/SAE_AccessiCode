"""
RGAA 4.1.2 — critère 1.2 : chaque image de décoration est-elle correctement
ignorée par les technologies d'assistance ?

Périmètre : images décoratives sans légende. Une image est décorative si le
code la déclare comme telle (alt vide seul, aria-hidden="true",
role="presentation") ou, à défaut, si l'IA établit qu'elle ne porte aucune
information. Les conditions du test sont ensuite vérifiées dans le DOM.
"""

from __future__ import annotations

from copy import copy

from bs4 import Tag

from accessi_code.analysis.image_elements import ImageElement
from accessi_code.analysis.location import html_opening_tag
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Outcome,
    html_example,
    outcome,
    unresolved,
)

_TEXT_ATTRIBUTES = ("title", "aria-label", "aria-labelledby")


def _has_text_attribute(tag: Tag) -> bool:
    return any(str(tag.get(name) or "").strip() for name in _TEXT_ATTRIBUTES)


class _DecorativeTest(ImageTest):
    """Image de décoration correctement ignorée."""

    criterion_id = "1.2"
    empty_summary = "Aucune image de décoration concernée par ce test."
    recommendation = 'Ajouter aria-hidden="true" et retirer toute alternative textuelle.'

    def in_scope(self, element: ImageElement) -> bool:
        # Une image légendée relève du critère 1.9, pas du 1.2.
        return not element.has_caption

    def problems(self, element: ImageElement) -> list[str]:
        """Conditions du test non respectées (liste vide : conforme)."""
        raise NotImplementedError

    def correct_markup(self, element: ImageElement, tag: Tag) -> bool:
        """Applique la correction à la copie de la balise si un exemple est possible."""
        raise NotImplementedError

    def recommendation_for(self, element: ImageElement) -> str:
        before = element.tag
        after = copy(before)
        for attribute in _TEXT_ATTRIBUTES:
            after.attrs.pop(attribute, None)
        if not self.correct_markup(element, after):
            return self.recommendation

        before_html, after_html = str(before), str(after)
        if before.contents == after.contents:
            before_html, after_html = html_opening_tag(before_html), html_opening_tag(after_html)
        return html_example(self.recommendation, before_html, after_html)

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        decorative = await evaluation.decorative(element)
        if decorative.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if decorative.value is None:
            return unresolved(
                element,
                decorative,
                "Impossible d'établir si l'image est décorative.",
                "Vérifier le rôle de l'image ; si elle est décorative, la masquer aux technologies d'assistance.",
            )

        problems = self.problems(element)
        if not problems:
            return outcome(TestStatus.PASS)
        return outcome(
            TestStatus.FAIL,
            element,
            "L'image de décoration n'est pas ignorée par les technologies d'assistance : " + " ; ".join(problems) + ".",
            self.recommendation_for(element),
            decorative=decorative.evidence,
        )


class _AltDecorativeTest(_DecorativeTest):
    """img / area : alt vide seul, ou aria-hidden="true", ou role="presentation"."""

    recommendation = 'Utiliser alt="" sans title ni aria-label, ou ajouter aria-hidden="true".'

    def correct_markup(self, element: ImageElement, tag: Tag) -> bool:
        tag["alt"] = ""
        return True

    def problems(self, element: ImageElement) -> list[str]:
        if element.aria_hidden or element.presentation_role:
            return []
        if element.has_empty_alt and not _has_text_attribute(element.tag):
            return []
        if element.has_empty_alt:
            return ["l'attribut alt est vide mais un title, aria-label ou aria-labelledby fournit une alternative"]
        if "alt" in element.alternatives:
            return [f"l'attribut alt n'est pas vide (« {element.alternatives['alt'][:80]} »)"]
        return ['ni alt="", ni aria-hidden="true", ni role="presentation"']


class Test121(_AltDecorativeTest):
    """1.2.1 : image (img) de décoration, sans légende."""

    test_id = "1.2.1"
    kinds = ("img",)


class Test122(_AltDecorativeTest):
    """1.2.2 : zone non cliquable (area sans href) de décoration."""

    test_id = "1.2.2"
    kinds = ("area",)
    empty_summary = "Aucune zone non cliquable d'image réactive."

    def in_scope(self, element: ImageElement) -> bool:
        return not element.functional


class _HiddenDecorativeTest(_DecorativeTest):
    """object, svg, canvas, embed : aria-hidden="true" et aucune alternative."""

    def correct_markup(self, element: ImageElement, tag: Tag) -> bool:
        tag["aria-hidden"] = "true"
        if element.kind in {"object", "canvas"} and "content" in element.alternatives:
            if tag.find(True) is not None:
                return False
            tag.clear()
        if element.kind == "svg":
            for description in tag.find_all(["title", "desc"]):
                description.extract()
        if element.kind in {"svg", "canvas"}:
            for child in tag.find_all(True):
                for attribute in _TEXT_ATTRIBUTES:
                    child.attrs.pop(attribute, None)
        return True

    def problems(self, element: ImageElement) -> list[str]:
        problems = []
        if not element.aria_hidden:
            problems.append('aria-hidden="true" est absent')
        if _has_text_attribute(element.tag):
            problems.append("un title, aria-label ou aria-labelledby fournit une alternative")
        return problems


class Test123(_HiddenDecorativeTest):
    """1.2.3 : image objet (object) de décoration, sans légende."""

    test_id = "1.2.3"
    kinds = ("object",)

    def problems(self, element: ImageElement) -> list[str]:
        problems = super().problems(element)
        if "content" in element.alternatives:
            problems.append("un texte entre <object> et </object> fait office d'alternative")
        return problems


class Test124(_HiddenDecorativeTest):
    """1.2.4 : image vectorielle (svg) de décoration, sans légende."""

    test_id = "1.2.4"
    kinds = ("svg",)

    def problems(self, element: ImageElement) -> list[str]:
        problems = super().problems(element)
        descendants = element.tag.find_all(True)
        if any(_has_text_attribute(node) for node in descendants):
            problems.append("un enfant du svg porte un title, aria-label ou aria-labelledby")
        if any(node.get_text(" ", strip=True) for node in element.tag.find_all(["title", "desc"])):
            problems.append("une balise <title> ou <desc> n'est pas vide")
        return problems


class Test125(_HiddenDecorativeTest):
    """1.2.5 : image bitmap (canvas) de décoration, sans légende."""

    test_id = "1.2.5"
    kinds = ("canvas",)

    def problems(self, element: ImageElement) -> list[str]:
        problems = super().problems(element)
        if "content" in element.alternatives:
            problems.append("un texte entre <canvas> et </canvas> fait office d'alternative")
        if any(_has_text_attribute(node) for node in element.tag.find_all(True)):
            problems.append("un enfant du canvas porte une alternative")
        return problems


class Test126(_HiddenDecorativeTest):
    """1.2.6 : image embarquée (embed) de décoration, sans légende."""

    test_id = "1.2.6"
    kinds = ("embed",)

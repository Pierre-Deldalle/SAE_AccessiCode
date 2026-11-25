"""
RGAA 4.1.2 — critère 1.1 : chaque image porteuse d'information a-t-elle
une alternative textuelle ?

Principe : une image qui possède déjà une alternative autorisée est conforme
sans appel à l'IA. L'IA n'intervient que pour savoir si une image sans
alternative est porteuse d'information (sinon le test ne s'applique pas).
"""

from __future__ import annotations

from typing import ClassVar

from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Outcome,
    attribute_example,
    outcome,
    unresolved,
)

# Sources d'alternative autorisées par chaque test du critère 1.1.
ALLOWED = {
    "img": ("aria-labelledby", "aria-label", "alt", "title"),
    "role_img": ("aria-labelledby", "aria-label"),
    "area": ("aria-label", "alt"),
    "input": ("aria-labelledby", "aria-label", "alt", "title"),
    "svg": ("svg-title", "aria-labelledby", "aria-label"),
    "object": ("aria-labelledby", "aria-label", "title"),
    "embed": ("aria-labelledby", "aria-label", "title"),
    "canvas": ("aria-labelledby", "aria-label"),
}


def allowed_alternatives(element: ImageElement) -> list[str]:
    return [source for source in ALLOWED[element.kind] if source in element.alternatives]


def _role_recommendation(element: ImageElement, fallback: str) -> str:
    if (
        element.kind in {"svg", "object", "embed", "canvas"}
        and not element.has_role_img
        and allowed_alternatives(element)
    ):
        return attribute_example(
            'Ajouter role="img" en conservant l\'alternative existante.',
            element.tag,
            {"role": "img"},
        )
    return fallback


def has_adjacent_alternative(element: ImageElement) -> bool:
    """Lien ou bouton placé immédiatement après l'élément (1.1.6 à 1.1.8)."""
    sibling = element.tag.find_next_sibling()
    if sibling is None or sibling.name not in {"a", "button"}:
        return False
    return bool(sibling.get_text(" ", strip=True) or sibling.get("aria-label"))


class _AlternativeTest(ImageTest):
    """Présence d'une alternative sur les images porteuses d'information."""

    criterion_id = "1.1"
    empty_summary = "Aucune image concernée par ce test."

    missing_message: ClassVar[str] = "L'image est porteuse d'information mais n'a aucune alternative textuelle."
    recommendation: ClassVar[str] = "Ajouter une alternative textuelle (attribut alt, aria-label ou aria-labelledby)."

    def satisfied(self, element: ImageElement) -> bool:
        """Conditions déterministes du test remplies."""
        return bool(allowed_alternatives(element))

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if self.satisfied(element):
            return outcome(TestStatus.PASS)

        role = await evaluation.information_role(element)
        if role.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if role.value is None:
            return unresolved(
                element,
                role,
                "L'élément n'a pas d'alternative textuelle et son rôle informatif n'a pas pu être établi.",
                "Vérifier si l'image est porteuse d'information ; si oui, lui donner une alternative.",
            )
        return outcome(
            TestStatus.FAIL,
            element,
            self.missing_message,
            _role_recommendation(element, self.recommendation),
            role=role.evidence,
        )


class Test111(_AlternativeTest):
    """1.1.1 : image (img ou role="img") porteuse d'information."""

    test_id = "1.1.1"
    kinds = ("img", "role_img")


class Test112(_AlternativeTest):
    """1.1.2 : zone cliquable (area avec href) d'une image réactive."""

    test_id = "1.1.2"
    kinds = ("area",)
    empty_summary = "Aucune zone cliquable d'image réactive."
    recommendation = "Ajouter un attribut alt ou aria-label décrivant la destination de la zone."

    def in_scope(self, element: ImageElement) -> bool:
        return element.functional


class Test113(_AlternativeTest):
    """1.1.3 : bouton de type image (toujours porteur d'information)."""

    test_id = "1.1.3"
    kinds = ("input",)
    empty_summary = "Aucun bouton de type image."
    missing_message = "Le bouton de type image n'a aucune alternative textuelle."
    recommendation = "Ajouter un attribut alt décrivant l'action du bouton."


class Test114(ImageTest):
    """
    1.1.4 : image réactive côté serveur (img ismap) doublée d'un mécanisme
    donnant accès aux mêmes destinations.

    Les destinations d'une carte côté serveur ne sont pas connues dans le HTML :
    l'absence de tout autre lien est un défaut certain, sinon une vérification
    humaine documentée (``equivalent_destinations``) est nécessaire.
    """

    test_id = "1.1.4"
    criterion_id = "1.1"
    kinds = ("img",)
    empty_summary = "Aucune image réactive côté serveur (ismap)."

    def in_scope(self, element: ImageElement) -> bool:
        return element.tag.has_attr("ismap")

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        verified = evaluation.evidence(element, "equivalent_destinations")
        if verified is True:
            return outcome(TestStatus.PASS)
        if verified is False:
            return outcome(
                TestStatus.FAIL,
                element,
                "Les destinations de l'image réactive ne sont pas accessibles par un autre moyen.",
                "Proposer des liens texte menant aux mêmes destinations.",
            )

        map_link = element.tag.find_parent("a")
        other_links = [
            link
            for link in evaluation.soup.find_all("a", href=True)
            if link is not map_link and link.get_text(strip=True)
        ]
        if not other_links:
            return outcome(
                TestStatus.FAIL,
                element,
                "L'image réactive côté serveur est le seul moyen d'accéder à ses destinations.",
                "Proposer des liens texte menant aux mêmes destinations.",
            )
        return outcome(
            TestStatus.NEEDS_REVIEW,
            element,
            "Les destinations d'une image réactive côté serveur ne sont pas décrites dans le HTML.",
            "Vérifier que chaque zone cliquable a un lien texte équivalent dans la page.",
            other_links=len(other_links),
        )


class Test115(_AlternativeTest):
    """1.1.5 : image vectorielle (svg) : role="img" et alternative obligatoires."""

    test_id = "1.1.5"
    kinds = ("svg",)
    empty_summary = "Aucune image vectorielle (svg)."

    def satisfied(self, element: ImageElement) -> bool:
        return element.has_role_img and bool(allowed_alternatives(element))

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if self.satisfied(element):
            return outcome(TestStatus.PASS)
        if element.aria_hidden:
            # SVG déclaré décoratif : il relève du critère 1.2.
            return outcome(TestStatus.NOT_APPLICABLE)

        role = await evaluation.information_role(element)
        if role.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if role.value is None:
            return unresolved(
                element,
                role,
                'Le svg n\'a pas à la fois role="img" et une alternative, et son rôle informatif est inconnu.',
                'Si le svg est porteur d\'information : ajouter role="img" et un <title> ou aria-label.',
            )

        missing = []
        if not element.has_role_img:
            missing.append('role="img"')
        if not allowed_alternatives(element):
            missing.append("une alternative (<title>, aria-label ou aria-labelledby)")
        return outcome(
            TestStatus.FAIL,
            element,
            f"Le svg porteur d'information n'a pas {' ni '.join(missing)}.",
            _role_recommendation(element, 'Ajouter role="img" sur la balise <svg> et une alternative textuelle.'),
            role=role.evidence,
        )


class _ObjectLikeTest(_AlternativeTest):
    """object / embed : alternative + role="img", ou lien / bouton adjacent."""

    recommendation = (
        'Ajouter role="img" et une alternative (aria-label, aria-labelledby ou title), '
        "ou un lien adjacent vers un contenu alternatif."
    )

    def satisfied(self, element: ImageElement) -> bool:
        if element.has_role_img and allowed_alternatives(element):
            return True
        return has_adjacent_alternative(element)


class Test116(_ObjectLikeTest):
    """1.1.6 : image objet (object type="image/…")."""

    test_id = "1.1.6"
    kinds = ("object",)
    empty_summary = "Aucune image objet (object)."


class Test117(_ObjectLikeTest):
    """1.1.7 : image embarquée (embed type="image/…")."""

    test_id = "1.1.7"
    kinds = ("embed",)
    empty_summary = "Aucune image embarquée (embed)."


class Test118(_ObjectLikeTest):
    """1.1.8 : image bitmap (canvas)."""

    test_id = "1.1.8"
    kinds = ("canvas",)
    empty_summary = "Aucune image bitmap (canvas)."
    recommendation = (
        'Ajouter role="img" et aria-label, un contenu alternatif entre <canvas> et </canvas>, '
        "ou un lien adjacent vers un contenu alternatif."
    )

    def satisfied(self, element: ImageElement) -> bool:
        if element.has_role_img:
            # Avec role="img", seules aria-label / aria-labelledby comptent.
            return bool(allowed_alternatives(element)) or has_adjacent_alternative(element)
        return "content" in element.alternatives or has_adjacent_alternative(element)

"""
RGAA 4.1.2 — critère 1.6 : chaque image porteuse d'information a-t-elle,
si nécessaire, une description détaillée ?

- Un mécanisme de description autorisé est présent : conforme, sans IA.
- Sinon, l'IA établit si l'image est porteuse d'information et complexe
  (graphique, schéma, carte…) au point de nécessiter une description.
- Les tests de restitution par les technologies d'assistance (1.6.6, 1.6.8,
  1.6.9) vérifient les associations dans le DOM ; la restitution elle-même
  demande un lecteur d'écran.
"""

from __future__ import annotations

import re
from typing import ClassVar

from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Outcome,
    outcome,
    unresolved,
)

_REFERENCE = "alternative_reference"

# Intitulé d'un lien ou bouton adjacent qui annonce une description détaillée.
_DESCRIPTION_LINK = re.compile(
    r"description|décri|détail|version (texte|textuelle)|transcription|données|lire la suite de l'image",
    re.IGNORECASE,
)
_ADJACENT = ("adjacent_link", "adjacent_button")

# Mécanismes autorisés pour chaque type d'élément.
MECHANISMS = {
    "img": ("longdesc", _REFERENCE, *_ADJACENT, "aria-describedby"),
    "object": (_REFERENCE, *_ADJACENT, "aria-describedby"),
    "embed": (_REFERENCE, *_ADJACENT, "aria-describedby"),
    "input": (_REFERENCE, *_ADJACENT, "aria-describedby"),
    "svg": (_REFERENCE, "aria-labelledby", "aria-describedby", "svg-desc", *_ADJACENT),
    "canvas": (_REFERENCE, "aria-labelledby", "aria-describedby", "canvas-content", *_ADJACENT),
    "role_img": (_REFERENCE, "aria-labelledby", "aria-describedby", *_ADJACENT),
}


def present_mechanisms(element: ImageElement) -> list[str]:
    """Mécanismes de description détaillée effectivement utilisables sur l'élément."""
    found: list[str] = []
    if element.alternative_references_description:
        found.append(_REFERENCE)
    for description in element.descriptions:
        usable = description.available
        if description.source == "longdesc":
            usable = bool(description.reference)
        elif description.source in _ADJACENT:
            # Seul un lien ou bouton annoncé comme donnant accès à une description compte.
            # Un lien vers une autre page reste valide même si elle n'a pas été chargée.
            external = description.source == "adjacent_link" and not str(description.reference or "").startswith("#")
            usable = (description.available or external) and _announces_description(element)
        if usable and description.source not in found:
            found.append(description.source)
    return [name for name in found if name in MECHANISMS[element.kind]]


def _announces_description(element: ImageElement) -> bool:
    for sibling in (element.tag.find_next_sibling(), element.tag.find_previous_sibling()):
        if sibling is not None and sibling.name in {"a", "button"}:
            label = " ".join([sibling.get_text(" ", strip=True), str(sibling.get("aria-label") or "")])
            if _DESCRIPTION_LINK.search(label):
                return True
    return False


def broken_describedby(element: ImageElement) -> bool:
    """aria-describedby référence un élément absent, dupliqué ou vide."""
    return any(
        description.source == "aria-describedby" and not description.available and description.reference != "desc"
        for description in element.descriptions
    )


class _DetailedDescriptionTest(ImageTest):
    """Présence d'une description détaillée lorsque l'image la nécessite."""

    criterion_id = "1.6"
    empty_summary = "Aucune image concernée par ce test."
    recommendation: ClassVar[str] = (
        "Fournir une description détaillée : lien ou bouton adjacent, passage référencé par "
        "aria-describedby, ou alternative annonçant une description placée à côté de l'image."
    )

    def in_scope(self, element: ImageElement) -> bool:
        return not element.marked_decorative

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if present_mechanisms(element):
            return outcome(TestStatus.PASS)

        verified = evaluation.evidence(element, "needs_detailed_description")
        if verified is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if verified is True:
            return self._missing(element, source="evidence")

        role = await evaluation.information_role(element)
        if role.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)

        needs = await evaluation.profile_flag(element, "needs_detailed_description")
        if needs.value is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if needs.value is None or role.value is None:
            judgement = needs if needs.value is None else role
            return unresolved(
                element,
                judgement,
                "Impossible d'établir si l'image nécessite une description détaillée.",
                "Vérifier si l'image est complexe (graphique, schéma, carte) ; si oui, ajouter une description.",
            )
        return self._missing(element, analysis=needs.evidence)

    def _missing(self, element: ImageElement, **evidence) -> Outcome:
        return outcome(
            TestStatus.FAIL,
            element,
            "L'image nécessite une description détaillée mais aucun mécanisme de description n'est présent.",
            self.recommendation,
            **evidence,
        )


class Test161(_DetailedDescriptionTest):
    """1.6.1 : image (img)."""

    test_id = "1.6.1"
    kinds = ("img",)


class Test162(_DetailedDescriptionTest):
    """1.6.2 : image objet (object)."""

    test_id = "1.6.2"
    kinds = ("object",)


class Test163(_DetailedDescriptionTest):
    """1.6.3 : image embarquée (embed)."""

    test_id = "1.6.3"
    kinds = ("embed",)


class Test164(_DetailedDescriptionTest):
    """1.6.4 : bouton de type image (input type="image")."""

    test_id = "1.6.4"
    kinds = ("input",)


class Test165(_DetailedDescriptionTest):
    """1.6.5 : image vectorielle (svg)."""

    test_id = "1.6.5"
    kinds = ("svg",)


class Test167(_DetailedDescriptionTest):
    """1.6.7 : image bitmap (canvas)."""

    test_id = "1.6.7"
    kinds = ("canvas",)


class Test1610(_DetailedDescriptionTest):
    """1.6.10 : balise possédant role="img"."""

    test_id = "1.6.10"
    kinds = ("role_img",)


# ----------------------------------------------------------------------
# Restitution par les technologies d'assistance
# ----------------------------------------------------------------------


class _RestitutionTest(ImageTest):
    """
    Restitution d'une description détaillée par les technologies d'assistance.

    Association cassée : non conforme. Association valide : la restitution
    doit être constatée avec un lecteur d'écran (vérification documentée
    ``correctly_exposed``), sinon le test reste à vérifier.
    """

    criterion_id = "1.6"
    empty_summary = "Aucune description détaillée concernée par ce test."
    # Mécanismes dont la restitution est contrôlée par le test.
    mechanisms: ClassVar[tuple[str, ...]]

    def in_scope(self, element: ImageElement) -> bool:
        if element.marked_decorative:
            return False
        if broken_describedby(element):
            return True
        return any(name in self.mechanisms for name in present_mechanisms(element))

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if broken_describedby(element):
            return outcome(
                TestStatus.FAIL,
                element,
                "aria-describedby référence un élément absent, dupliqué ou vide.",
                "Faire référencer par aria-describedby l'identifiant unique d'un passage de texte non vide.",
            )
        verified = evaluation.evidence(element, "correctly_exposed")
        if verified is True:
            return outcome(TestStatus.PASS)
        if verified is False:
            return outcome(
                TestStatus.FAIL,
                element,
                "La description détaillée n'est pas restituée par les technologies d'assistance.",
                "Corriger l'association entre l'image et sa description.",
            )
        return outcome(
            TestStatus.NEEDS_REVIEW,
            element,
            "L'association de la description est valide ; sa restitution doit être vérifiée avec un lecteur d'écran.",
            "Vérifier avec un lecteur d'écran que la description détaillée est annoncée.",
            mechanisms=present_mechanisms(element),
        )


class Test166(_RestitutionTest):
    """1.6.6 : svg ayant une description détaillée (aria-label, aria-labelledby, aria-describedby)."""

    test_id = "1.6.6"
    kinds = ("svg",)
    mechanisms = (_REFERENCE, "aria-labelledby", "aria-describedby")


class Test168(_RestitutionTest):
    """1.6.8 : canvas dont la description détaillée est placée entre les balises."""

    test_id = "1.6.8"
    kinds = ("canvas",)
    mechanisms = ("canvas-content",)

    def in_scope(self, element: ImageElement) -> bool:
        if element.marked_decorative:
            return False
        return "canvas-content" in present_mechanisms(element) or (
            "content" in element.alternatives and element.alternative_references_description
        )


class Test169(_RestitutionTest):
    """1.6.9 : image dont la description détaillée est associée par aria-describedby."""

    test_id = "1.6.9"
    kinds = ("img", "role_img", "input", "object", "embed", "svg", "canvas")
    mechanisms = ("aria-describedby",)

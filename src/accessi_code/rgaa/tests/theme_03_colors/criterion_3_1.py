"""
RGAA 4.1.2 — critère 3.1 : dans chaque page web, l'information ne doit pas être
donnée uniquement par la couleur.

Les candidats sont repérés dans le DOM et les feuilles de style ; l'IA juge si
la couleur porte une information et si un autre moyen la transmet aussi :

- 3.1.1 : mots ou groupes de mots mis en couleur ;
- 3.1.2 : indications de couleur données par un texte (« les champs en rouge ») ;
- 3.1.3 : images porteuses d'information (VLM) ;
- 3.1.4 : propriétés CSS de couleur (liens non soulignés dans un texte, états
  signalés par une couleur, styles en ligne) ;
- 3.1.5 : médias temporels vidéo (le son n'a pas de couleur) ;
- 3.1.6 : médias non temporels (objets embarqués).
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.sensory import (
    COLOR_INDICATION,
    Candidate,
    color_property_candidates,
    colored_words,
    text_candidates,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.rgaa.sensory_tests import SensoryImageTest, SensoryMediaTest, SensoryTextTest

RECOMMENDATION = (
    "Transmettre aussi l'information par un autre moyen que la couleur : texte explicite, "
    "symbole, motif, soulignement ou mise en forme."
)


_NO_UNDERLINE = re.compile(r"(text-decoration(?:-line)?\s*:\s*)none", re.IGNORECASE)


def _underlined(css: str) -> str:
    return _NO_UNDERLINE.sub(lambda match: match.group(1) + "underline", css)


def underline_example(link: Tag, removed: str | None) -> str:
    """Exemple qui rétablit le soulignement, dans le style en ligne ou dans la règle CSS qui l'a retiré."""
    if not removed:
        return ""
    if removed.startswith("style en ligne"):
        after = opening_tag(link, style=_underlined(str(link.get("style") or "")))
        return f" Exemple : {opening_tag(link)} → {after}"
    return f" Exemple : {removed} → {_underlined(removed)}"


class ColorTest:
    kind = "color"
    criterion_id = "3.1"
    recommendation = RECOMMENDATION
    detailed_results = True


class Test311(ColorTest, SensoryTextTest):
    """3.1.1 : mise en couleur de mots porteuse d'information."""

    test_id = "3.1.1"
    noun = "mot(s) mis en couleur"
    empty_summary = "Aucun mot ou groupe de mots mis en couleur."
    fail_message = "L'information portée par la mise en couleur de ce texte n'est donnée que par la couleur."
    uncertain_message = (
        "Vérifier que la mise en couleur de ce texte ne porte pas une information donnée uniquement par la couleur."
    )

    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        return colored_words(context)


class Test312(ColorTest, SensoryTextTest):
    """3.1.2 : indication de couleur donnée par un texte."""

    test_id = "3.1.2"
    noun = "texte(s) citant une couleur"
    empty_summary = "Aucun texte ne fait référence à une couleur."
    fail_message = "Ce texte donne une information uniquement par une couleur."
    uncertain_message = "Vérifier que l'indication de couleur de ce texte est accompagnée d'un autre moyen de repérage."

    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        return text_candidates(soup, COLOR_INDICATION)


class Test313(ColorTest, SensoryImageTest):
    """3.1.3 : images véhiculant une information."""

    test_id = "3.1.3"
    empty_summary = "Aucune image porteuse d'information."
    fail_message = "L'information de cette image n'est donnée que par la couleur."
    uncertain_message = "Vérifier que l'information de cette image n'est pas donnée uniquement par la couleur."


class Test314(ColorTest, SensoryTextTest):
    """3.1.4 : propriétés CSS déterminant une couleur et véhiculant une information."""

    test_id = "3.1.4"
    noun = "élément(s) coloré(s) par CSS"
    empty_summary = "Aucune propriété CSS de couleur susceptible de porter une information."
    fail_message = "La propriété CSS de couleur de cet élément est le seul moyen de transmettre l'information."
    uncertain_message = (
        "Vérifier que la couleur appliquée par CSS à cet élément n'est pas le seul moyen de transmettre l'information."
    )

    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        return color_property_candidates(context)

    def example(self, candidate: Candidate) -> str:
        """Lien distingué du texte par sa seule couleur : le soulignement retiré est rétabli."""
        return underline_example(candidate.tag, candidate.evidence.get("underline_removed"))


class Test315(ColorTest, SensoryMediaTest):
    """3.1.5 : médias temporels (vidéo)."""

    test_id = "3.1.5"
    media = ("video",)
    empty_summary = "Aucune vidéo."
    fail_message = ""
    uncertain_message = (
        "Le contenu de la vidéo ne peut pas être analysé automatiquement : vérifier qu'aucune information "
        "n'y est donnée uniquement par la couleur."
    )


class Test316(ColorTest, SensoryMediaTest):
    """3.1.6 : médias non temporels."""

    test_id = "3.1.6"
    media = ("object", "embed", "applet")
    empty_summary = "Aucun média non temporel."
    fail_message = ""
    uncertain_message = (
        "Le contenu de ce média ne peut pas être analysé automatiquement : vérifier qu'aucune information "
        "n'y est donnée uniquement par la couleur."
    )

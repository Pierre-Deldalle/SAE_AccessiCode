"""
RGAA 4.1.2 — critère 10.10 : dans chaque page web, l'information ne doit pas
être donnée par la forme, taille ou position uniquement. Cette règle est-elle
implémentée de façon pertinente ?

Mêmes candidats que 10.9. L'IA juge ici si l'autre moyen qui transmet
l'information (texte, intitulé, titre) est pertinent. Un candidat sans autre
moyen est non conforme au critère 10.9 et n'est pas compté une seconde fois.
L'analyse des candidats est mise en cache : 10.9 et 10.10 partagent les appels IA.

- 10.10.1 : textes ;
- 10.10.2 : images ;
- 10.10.3 : médias temporels ;
- 10.10.4 : médias non temporels.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.sensory import SHAPE_SIZE_POSITION, Candidate, text_candidates
from accessi_code.models.audit_context import AuditContext
from accessi_code.rgaa.sensory_tests import SensoryImageTest, SensoryMediaTest, SensoryTextTest
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    NON_TEMPORAL_MEDIA,
    TEMPORAL_MEDIA,
)

RECOMMENDATION = (
    "Rendre pertinent le moyen qui complète la forme, la taille ou la position : il doit permettre, "
    "seul, d'identifier l'élément ou de comprendre l'information."
)


class RelevantAlternativeTest:
    kind = "shape_size_position"
    criterion_id = "10.10"
    judge_alternative = True
    locate_findings = True
    recommendation = RECOMMENDATION


class Test10101(RelevantAlternativeTest, SensoryTextTest):
    """10.10.1 : textes."""

    test_id = "10.10.1"
    noun = "texte(s) faisant référence à une forme, une taille ou une position"
    empty_summary = "Aucun texte ne complète une forme, une taille ou une position par un autre moyen."
    fail_message = "Le moyen qui complète la forme, la taille ou la position dans ce texte n'est pas pertinent."
    uncertain_message = (
        "Vérifier que le moyen qui complète la forme, la taille ou la position dans ce texte est pertinent."
    )

    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        return text_candidates(soup, SHAPE_SIZE_POSITION)


class Test10102(RelevantAlternativeTest, SensoryImageTest):
    """10.10.2 : images."""

    test_id = "10.10.2"
    empty_summary = "Aucune image ne complète une forme, une taille ou une position par un autre moyen."
    fail_message = "Le moyen qui complète la forme, la taille ou la position dans cette image n'est pas pertinent."
    uncertain_message = (
        "Vérifier que le moyen qui complète la forme, la taille ou la position dans cette image est pertinent."
    )


class Test10103(RelevantAlternativeTest, SensoryMediaTest):
    """10.10.3 : médias temporels."""

    test_id = "10.10.3"
    media = TEMPORAL_MEDIA
    empty_summary = "Aucun média temporel."
    fail_message = ""
    uncertain_message = (
        "Le contenu de ce média ne peut pas être analysé automatiquement : vérifier que le moyen qui complète "
        "la forme, la taille ou la position est pertinent."
    )


class Test10104(RelevantAlternativeTest, SensoryMediaTest):
    """10.10.4 : médias non temporels."""

    test_id = "10.10.4"
    media = NON_TEMPORAL_MEDIA
    empty_summary = "Aucun média non temporel."
    fail_message = ""
    uncertain_message = (
        "Le contenu de ce média ne peut pas être analysé automatiquement : vérifier que le moyen qui complète "
        "la forme, la taille ou la position est pertinent."
    )

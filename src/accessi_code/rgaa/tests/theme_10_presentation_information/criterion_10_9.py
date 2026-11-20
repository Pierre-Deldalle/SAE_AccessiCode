"""
RGAA 4.1.2 — critère 10.9 : dans chaque page web, l'information ne doit pas
être donnée uniquement par la forme, taille ou position.

Un pré-filtre repère les tournures qui désignent une forme, une taille ou une
position (« le bouton rond », « la colonne de droite », « ci-dessous ») ; les
couleurs relèvent du critère 3.1. L'IA juge si l'information repose uniquement
sur cette caractéristique.

- 10.9.1 : textes ;
- 10.9.2 : images porteuses d'information (VLM) ;
- 10.9.3 : médias temporels (vidéo, son) ;
- 10.9.4 : médias non temporels.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from accessi_code.analysis.sensory import SHAPE_SIZE_POSITION, Candidate, text_candidates
from accessi_code.models.audit_context import AuditContext
from accessi_code.rgaa.sensory_tests import SensoryImageTest, SensoryMediaTest, SensoryTextTest

RECOMMENDATION = (
    "Transmettre aussi l'information par un autre moyen que la forme, la taille ou la position : "
    "intitulé explicite, texte, titre de section."
)

TEMPORAL_MEDIA = ("video", "audio")
NON_TEMPORAL_MEDIA = ("object", "embed", "applet")


class ShapeSizePositionTest:
    kind = "shape_size_position"
    criterion_id = "10.9"
    recommendation = RECOMMENDATION


class Test1091(ShapeSizePositionTest, SensoryTextTest):
    """10.9.1 : textes."""

    test_id = "10.9.1"
    noun = "texte(s) faisant référence à une forme, une taille ou une position"
    empty_summary = "Aucun texte ne fait référence à une forme, une taille ou une position."
    fail_message = "Ce texte donne une information uniquement par la forme, la taille ou la position."
    uncertain_message = (
        "Vérifier que ce texte ne donne pas une information uniquement par la forme, la taille ou la position."
    )

    def candidates(self, context: AuditContext, soup: BeautifulSoup) -> list[Candidate]:
        return text_candidates(soup, SHAPE_SIZE_POSITION)


class Test1092(ShapeSizePositionTest, SensoryImageTest):
    """10.9.2 : images."""

    test_id = "10.9.2"
    empty_summary = "Aucune image porteuse d'information."
    fail_message = "L'information de cette image n'est donnée que par la forme, la taille ou la position."
    uncertain_message = (
        "Vérifier que l'information de cette image n'est pas donnée uniquement par la forme, la taille ou la position."
    )


class Test1093(ShapeSizePositionTest, SensoryMediaTest):
    """10.9.3 : médias temporels."""

    test_id = "10.9.3"
    media = TEMPORAL_MEDIA
    empty_summary = "Aucun média temporel."
    fail_message = ""
    uncertain_message = (
        "Le contenu de ce média ne peut pas être analysé automatiquement : vérifier qu'aucune information "
        "n'y est donnée uniquement par la forme, la taille ou la position."
    )


class Test1094(ShapeSizePositionTest, SensoryMediaTest):
    """10.9.4 : médias non temporels."""

    test_id = "10.9.4"
    media = NON_TEMPORAL_MEDIA
    empty_summary = "Aucun média non temporel."
    fail_message = ""
    uncertain_message = (
        "Le contenu de ce média ne peut pas être analysé automatiquement : vérifier qu'aucune information "
        "n'y est donnée uniquement par la forme, la taille ou la position."
    )

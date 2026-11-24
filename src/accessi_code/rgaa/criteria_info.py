"""
Explications par critère RGAA 4.1.2 : intitulé officiel, impact pour l'utilisateur et lien vers la fiche.

Source unique des explications affichées à côté des résultats : les tests RGAA disent ce qui ne va
pas, cette table dit pourquoi cela gêne. Elle ne dépend d'aucun test et n'en modifie aucun.

Règles de rédaction :

- ``title`` : intitulé officiel recopié fidèlement depuis
  https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/ (ponctuation et apostrophes comprises) ;
- ``impact`` : une à deux phrases simples, sans jargon, qui disent qui est gêné et comment.

Thématiques renseignées pour l'instant : 4 (Multimédia).
"""

from __future__ import annotations

from dataclasses import dataclass

RGAA_CRITERIA_URL = "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/"


@dataclass(frozen=True, slots=True)
class CriterionInfo:
    """Explication d'un critère RGAA destinée à un public non spécialiste."""

    criterion_id: str
    title: str
    impact: str
    # Lien vers la fiche officielle ; déduit de criterion_id s'il n'est pas fourni.
    url: str = ""

    def __post_init__(self) -> None:
        if not self.url:
            object.__setattr__(self, "url", criterion_url(self.criterion_id))


def criterion_url(criterion_id: str) -> str:
    """
    Lien vers la fiche officielle d'un critère.

    Les critères sont des ancres de la page « Critères et tests » (…/criteres-et-tests/#4.1) :
    la forme …/criteres-et-tests/4.1 renvoie une erreur 404.
    """
    return f"{RGAA_CRITERIA_URL}#{criterion_id}"


_CRITERIA: tuple[CriterionInfo, ...] = (
    # ------------------------------------------------------------------
    # Thématique 4 : Multimédia
    # ------------------------------------------------------------------
    CriterionInfo(
        "4.1",
        "Chaque média temporel pré-enregistré a-t-il, si nécessaire, une transcription textuelle "
        "ou une audiodescription (hors cas particuliers) ?",
        "Une personne sourde ou malentendante n'entend pas un enregistrement audio, et une personne aveugle "
        "ne voit pas une vidéo. Sans version écrite ni description sonore, elles n'ont pas accès à l'information.",
    ),
    CriterionInfo(
        "4.2",
        "Pour chaque média temporel pré-enregistré ayant une transcription textuelle ou une audiodescription "
        "synchronisée, celles-ci sont-elles pertinentes (hors cas particuliers) ?",
        "Les personnes sourdes, malentendantes ou aveugles comptent sur la version écrite ou la description sonore "
        "pour comprendre le média. Si elle est incomplète ou inexacte, elles passent à côté d'une partie du contenu.",
    ),
    CriterionInfo(
        "4.3",
        "Chaque média temporel synchronisé pré-enregistré a-t-il, si nécessaire, des sous-titres synchronisés "
        "(hors cas particuliers) ?",
        "Sans sous-titres, une personne sourde ou malentendante ne peut pas suivre les dialogues "
        "ni les bruits importants d'une vidéo.",
    ),
    CriterionInfo(
        "4.4",
        "Pour chaque média temporel synchronisé pré-enregistré ayant des sous-titres synchronisés, "
        "ces sous-titres sont-ils pertinents ?",
        "Des sous-titres incomplets, erronés ou décalés par rapport à l'image font perdre le fil aux personnes "
        "sourdes ou malentendantes, qui ne peuvent pas s'aider du son pour corriger.",
    ),
    CriterionInfo(
        "4.5",
        "Chaque média temporel pré-enregistré a-t-il, si nécessaire, une audiodescription synchronisée "
        "(hors cas particuliers) ?",
        "Une personne aveugle ou malvoyante entend la vidéo mais ne voit pas ce qui se passe à l'écran. "
        "Sans une voix qui décrit les scènes importantes, elle manque une partie de l'histoire ou de l'information.",
    ),
    CriterionInfo(
        "4.6",
        "Pour chaque média temporel pré-enregistré ayant une audiodescription synchronisée, "
        "celle-ci est-elle pertinente ?",
        "Si la description sonore oublie des actions ou des textes affichés à l'écran, les personnes aveugles "
        "ou malvoyantes restent privées de ces informations visuelles.",
    ),
    CriterionInfo(
        "4.7",
        "Chaque média temporel est-il clairement identifiable (hors cas particuliers) ?",
        "Une personne aveugle qui se fait lire la page par un lecteur d'écran ne voit pas l'image d'aperçu. "
        "Sans titre ou texte qui présente le média, elle ne sait pas ce qu'elle va écouter ou regarder.",
    ),
    CriterionInfo(
        "4.8",
        "Chaque média non temporel a-t-il, si nécessaire, une alternative (hors cas particuliers) ?",
        "Une carte interactive ou une animation peut être impossible à percevoir ou à manipuler pour une personne "
        "aveugle ou qui n'utilise pas de souris. Sans version de remplacement, elle n'accède pas à son contenu.",
    ),
    CriterionInfo(
        "4.9",
        "Pour chaque média non temporel ayant une alternative, cette alternative est-elle pertinente ?",
        "Si la version de remplacement ne donne pas les mêmes informations ou ne permet pas les mêmes actions, "
        "les personnes qui en dépendent restent privées d'une partie du contenu.",
    ),
    CriterionInfo(
        "4.10",
        "Chaque son déclenché automatiquement est-il contrôlable par l’utilisateur ?",
        "Un son qui démarre tout seul couvre la voix du lecteur d'écran : une personne aveugle n'entend plus "
        "sa page et peine à trouver comment l'arrêter. Il gêne aussi les personnes qui ont du mal à se concentrer.",
    ),
    CriterionInfo(
        "4.11",
        "La consultation de chaque média temporel est-elle, si nécessaire, contrôlable par le clavier "
        "et tout dispositif de pointage ?",
        "Les personnes qui naviguent au clavier, sans souris, ou avec un écran tactile doivent pouvoir lancer, "
        "mettre en pause et arrêter une vidéo ou régler le son. Sinon, elles ne peuvent ni la regarder ni la couper.",
    ),
    CriterionInfo(
        "4.12",
        "La consultation de chaque média non temporel est-elle contrôlable par le clavier "
        "et tout dispositif de pointage ?",
        "Si une carte interactive ou une animation ne se commande qu'à la souris, les personnes qui naviguent "
        "au clavier, par exemple à cause d'un handicap moteur, ne peuvent pas s'en servir.",
    ),
    CriterionInfo(
        "4.13",
        "Chaque média temporel et non temporel est-il compatible avec les technologies d’assistance "
        "(hors cas particuliers) ?",
        "Les personnes aveugles utilisent un lecteur d'écran qui lit la page à voix haute. Si le lecteur vidéo "
        "ou le média ne lui donne pas le nom de ses boutons et de son contenu, elles ne peuvent ni le comprendre "
        "ni le commander.",
    ),
)

CRITERIA_INFO: dict[str, CriterionInfo] = {info.criterion_id: info for info in _CRITERIA}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Explication du critère (« 4.1 »), ou None si le critère n'est pas encore renseigné."""
    return CRITERIA_INFO.get(str(criterion_id).strip())

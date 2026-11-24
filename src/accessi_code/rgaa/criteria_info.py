"""
Explications par critère RGAA 4.1.2, destinées à l'utilisateur final.

Pour chaque critère : son intitulé officiel, ce qu'un défaut change concrètement
pour les personnes concernées (sans jargon), et le lien vers sa fiche officielle.
Les tests RGAA disent ce qui ne va pas ; cette table dit pourquoi cela gêne.

Pour ajouter un critère : ajouter une entrée dans ``CRITERIA``, avec l'intitulé
recopié depuis la méthode officielle.
"""

from __future__ import annotations

from dataclasses import dataclass

RGAA_METHOD_URL = "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/"


@dataclass(frozen=True)
class CriterionInfo:
    """Intitulé, impact pour les utilisateurs et fiche officielle d'un critère."""

    criterion_id: str
    title: str
    impact: str

    @property
    def url(self) -> str:
        return f"{RGAA_METHOD_URL}#{self.criterion_id}"


_ENTRIES = (
    # ---- Thème 2 : cadres ----
    CriterionInfo(
        "2.1",
        "Chaque cadre a-t-il un titre de cadre ?",
        "Une personne aveugle qui utilise un lecteur d'écran entend seulement « cadre » : sans titre, elle ne "
        "sait pas ce que contient ce bloc (carte, vidéo, formulaire…) avant d'y entrer et de l'explorer.",
    ),
    CriterionInfo(
        "2.2",
        "Pour chaque cadre ayant un titre de cadre, ce titre de cadre est-il pertinent ?",
        "Un titre vague comme « iframe » ou « cadre 1 » n'aide pas une personne qui utilise un lecteur d'écran : "
        "elle doit ouvrir le cadre pour découvrir son contenu, et ne peut pas choisir rapidement où aller.",
    ),
    # ---- Thème 7 : scripts ----
    CriterionInfo(
        "7.1",
        "Chaque script est-il, si nécessaire, compatible avec les technologies d'assistance ?",
        "Un bouton ou un menu fabriqué par le code de la page, sans les bonnes informations, est lu comme un simple "
        "texte par le lecteur d'écran : une personne aveugle ne sait pas qu'elle peut l'activer, ni s'il est "
        "ouvert, fermé ou coché.",
    ),
    CriterionInfo(
        "7.2",
        "Pour chaque script ayant une alternative, cette alternative est-elle pertinente ?",
        "Quand le code de la page ne peut pas s'exécuter (navigateur ancien, réglage de sécurité), la version de "
        "remplacement doit offrir la même chose : un simple « Activez JavaScript » laisse la personne sans accès "
        "au contenu ou au service.",
    ),
    CriterionInfo(
        "7.3",
        "Chaque script est-il contrôlable par le clavier et par tout dispositif de pointage (hors cas particuliers) ?",
        "Les personnes qui ne peuvent pas utiliser de souris (handicap moteur, personnes aveugles) naviguent au "
        "clavier : un menu ou un bouton qui ne réagit qu'au clic de la souris leur est inutilisable.",
    ),
    CriterionInfo(
        "7.4",
        "Pour chaque script qui initie un changement de contexte, l'utilisateur est-il averti ou en a-t-il le "
        "contrôle ?",
        "Quand la page change toute seule (nouvelle page, formulaire envoyé dès qu'on choisit dans une liste), une "
        "personne qui utilise un lecteur d'écran ou qui a des difficultés d'attention perd ses repères sans "
        "comprendre ce qui s'est passé.",
    ),
    CriterionInfo(
        "7.5",
        "Dans chaque page web, les messages de statut sont-ils correctement restitués par les technologies "
        "d'assistance ?",
        "Un message qui apparaît sans recharger la page (« Message envoyé », « Erreur dans le formulaire ») n'est "
        "pas lu par le lecteur d'écran s'il n'est pas signalé : une personne aveugle ne sait pas si son action "
        "a réussi.",
    ),
)

CRITERIA: dict[str, CriterionInfo] = {entry.criterion_id: entry for entry in _ENTRIES}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Explications du critère ``criterion_id`` (par exemple "2.1"), ou None s'il n'est pas renseigné."""
    return CRITERIA.get(criterion_id)

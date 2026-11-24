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
    # ---- Thème 11 : formulaires ----
    CriterionInfo(
        "11.1",
        "Chaque champ de formulaire a-t-il une étiquette ?",
        "Une personne aveugle qui utilise un lecteur d'écran entend seulement « zone de saisie » : sans étiquette, "
        "elle ne sait pas s'il faut y écrire son nom, son adresse ou son numéro de téléphone.",
    ),
    CriterionInfo(
        "11.2",
        "Chaque étiquette associée à un champ de formulaire est-elle pertinente (hors cas particuliers) ?",
        "Une étiquette vague comme « Champ 1 » ou « Saisir » ne dit pas ce qu'il faut écrire : une personne qui "
        "utilise un lecteur d'écran, ou qui a des difficultés de compréhension, risque de se tromper. Une personne "
        "qui commande l'ordinateur à la voix doit aussi pouvoir dire le mot affiché pour atteindre le champ.",
    ),
    CriterionInfo(
        "11.3",
        "Dans chaque formulaire, chaque étiquette associée à un champ de formulaire ayant la même fonction et "
        "répétée plusieurs fois dans une même page ou dans un ensemble de pages est-elle cohérente ?",
        "Si la même information s'appelle « Courriel » à un endroit et « Adresse électronique » ailleurs, une "
        "personne qui a des difficultés de compréhension ou de mémoire peut croire qu'on lui demande deux choses "
        "différentes.",
    ),
    CriterionInfo(
        "11.4",
        "Dans chaque formulaire, chaque étiquette de champ et son champ associé sont-ils accolés (hors cas "
        "particuliers) ?",
        "Une personne malvoyante qui agrandit fortement l'écran ne voit qu'une petite partie de la page à la fois : "
        "si l'étiquette est loin de son champ, elle ne sait plus quel texte correspond à quelle zone de saisie.",
    ),
    CriterionInfo(
        "11.5",
        "Dans chaque formulaire, les champs de même nature sont-ils regroupés, si nécessaire ?",
        "Sans regroupement, une personne qui utilise un lecteur d'écran entend « Oui », « Non » ou « Jour », "
        "« Mois », « Année » sans savoir à quelle question ces champs se rapportent.",
    ),
    CriterionInfo(
        "11.6",
        "Dans chaque formulaire, chaque regroupement de champs de même nature a-t-il une légende ?",
        "Un groupe de champs sans titre ne dit pas à quoi il sert : une personne qui utilise un lecteur d'écran "
        "entend les choix proposés (« Madame », « Monsieur ») sans entendre la question posée.",
    ),
    CriterionInfo(
        "11.7",
        "Dans chaque formulaire, chaque légende associée à un regroupement de champs de même nature est-elle "
        "pertinente ?",
        "Un titre de groupe vague comme « Informations » ou « Choix » n'aide pas : une personne qui utilise un "
        "lecteur d'écran ne sait toujours pas ce que ce groupe de champs lui demande.",
    ),
    CriterionInfo(
        "11.8",
        "Dans chaque formulaire, les items de même nature d'une liste de choix sont-ils regroupés de manière "
        "pertinente ?",
        "Dans une longue liste déroulante sans catégories, une personne qui utilise un lecteur d'écran doit écouter "
        "les options une par une, sans repère pour trouver rapidement la bonne.",
    ),
    CriterionInfo(
        "11.9",
        "Dans chaque formulaire, l'intitulé de chaque bouton est-il pertinent (hors cas particuliers) ?",
        "Un bouton sans texte, ou intitulé « OK », ne dit pas ce qu'il va faire : une personne qui utilise un "
        "lecteur d'écran ne sait pas s'il envoie, efface ou annule le formulaire, et une personne qui commande "
        "l'ordinateur à la voix ne peut l'activer que si son nom reprend le texte affiché.",
    ),
    CriterionInfo(
        "11.10",
        "Dans chaque formulaire, le contrôle de saisie est-il utilisé de manière pertinente (hors cas particuliers) ?",
        "Si les champs obligatoires ne sont pas signalés, ou si un message d'erreur n'indique pas quel champ "
        "corriger, une personne aveugle ou qui a des difficultés de compréhension ne peut pas savoir ce qui "
        "empêche l'envoi du formulaire.",
    ),
    CriterionInfo(
        "11.11",
        "Dans chaque formulaire, le contrôle de saisie est-il accompagné, si nécessaire, de suggestions facilitant "
        "la correction des erreurs de saisie ?",
        "Un message comme « Saisie incorrecte », sans exemple ni format attendu, oblige à deviner : une personne qui "
        "a des difficultés de lecture ou de compréhension peut rester bloquée sans pouvoir terminer sa démarche.",
    ),
    CriterionInfo(
        "11.12",
        "Pour chaque formulaire qui modifie ou supprime des données, ou qui transmet des réponses à un test ou à un "
        "examen, ou dont la validation a des conséquences financières ou juridiques, les données saisies "
        "peuvent-elles être modifiées, mises à jour ou récupérées par l'utilisateur ?",
        "Une personne qui fait plus facilement des erreurs de saisie (tremblements, vue réduite, troubles de "
        "l'attention) doit pouvoir vérifier, corriger ou annuler avant qu'un paiement, une commande ou une "
        "suppression devienne définitif.",
    ),
    CriterionInfo(
        "11.13",
        "La finalité d'un champ de saisie peut-elle être déduite pour faciliter le remplissage automatique des "
        "champs avec les données de l'utilisateur ?",
        "Quand le navigateur reconnaît un champ (nom, adresse, téléphone), il peut le remplir tout seul : c'est une "
        "aide précieuse pour les personnes qui ont du mal à taper au clavier ou à retenir ces informations.",
    ),
)

CRITERIA: dict[str, CriterionInfo] = {entry.criterion_id: entry for entry in _ENTRIES}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Explications du critère ``criterion_id`` (par exemple "2.1"), ou None s'il n'est pas renseigné."""
    return CRITERIA.get(criterion_id)

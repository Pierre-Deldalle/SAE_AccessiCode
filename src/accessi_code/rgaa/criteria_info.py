"""Intitulés et impacts des critères RGAA documentés.

Les intitulés proviennent du RGAA 4.1.2, publié par la DINUM le 18 avril 2023
sous Licence Ouverte 2.0.
"""

from dataclasses import dataclass

_CRITERIA_URL = "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/"


@dataclass(frozen=True, slots=True)
class CriterionInfo:
    """Intitulé officiel, impact pour l'utilisateur et lien vers le critère."""

    criterion_id: str
    title: str
    impact: str
    url: str


_CRITERIA_INFO = {
    criterion_id: CriterionInfo(criterion_id, title, impact, f"{_CRITERIA_URL}#{criterion_id}")
    for criterion_id, title, impact in (
        (
            "1.1",
            "Chaque image porteuse d’information a-t-elle une alternative textuelle\u00a0?",
            "Sans texte de remplacement, une personne qui utilise un lecteur d’écran peut manquer une information "
            "ou ne pas savoir à quoi sert un bouton illustré.",
        ),
        (
            "1.2",
            "Chaque image de décoration est-elle correctement ignorée par les technologies d’assistance\u00a0?",
            "Quand un lecteur d’écran annonce des images décoratives, les personnes qui l’utilisent entendent "
            "des détails inutiles et repèrent plus difficilement les informations importantes.",
        ),
        (
            "1.3",
            "Pour chaque image porteuse d’information ayant une alternative textuelle, "
            "cette alternative est-elle pertinente (hors cas particuliers)\u00a0?",
            "Une description vague ou erronée peut induire en erreur les personnes qui utilisent un lecteur d’écran. "
            "Une description trop longue peut aussi ralentir leur lecture.",
        ),
        (
            "1.4",
            "Pour chaque image utilisée comme CAPTCHA ou comme image-test, ayant une alternative textuelle, "
            "cette alternative permet-elle d’identifier la nature et la fonction de l’image\u00a0?",
            "Si l’image est mal décrite, une personne qui utilise un lecteur d’écran peut ne pas comprendre "
            "que la page lui demande de passer un test ou de prouver qu’elle n’est pas un robot.",
        ),
        (
            "1.5",
            "Pour chaque image utilisée comme CAPTCHA, une solution d’accès alternatif au contenu "
            "ou à la fonction du CAPTCHA est-elle présente\u00a0?",
            "Une vérification qui repose uniquement sur une image peut bloquer les personnes aveugles "
            "ou malvoyantes. Elles peuvent, par exemple, se retrouver dans l’impossibilité d’envoyer un formulaire.",
        ),
        (
            "1.6",
            "Chaque image porteuse d’information a-t-elle, si nécessaire, une description détaillée\u00a0?",
            "Sans description détaillée, les personnes qui utilisent un lecteur d’écran peuvent manquer "
            "les valeurs d’un graphique ou les étapes d’un schéma.",
        ),
        (
            "1.7",
            "Pour chaque image porteuse d’information ayant une description détaillée, "
            "cette description est-elle pertinente\u00a0?",
            "Une personne qui utilise un lecteur d’écran peut mal interpréter un graphique si sa description "
            "donne des valeurs fausses ou oublie une tendance importante.",
        ),
        (
            "1.8",
            "Chaque image texte porteuse d’information, en l’absence d’un mécanisme de remplacement, "
            "doit si possible être remplacée par du texte stylé. "
            "Cette règle est-elle respectée (hors cas particuliers)\u00a0?",
            "Les personnes malvoyantes peuvent avoir du mal à lire les mots intégrés dans une image. "
            "Ces mots peuvent devenir flous à l’agrandissement et ne suivent pas les réglages de couleur du texte.",
        ),
        (
            "1.9",
            "Chaque légende d’image est-elle, si nécessaire, correctement reliée à l’image correspondante\u00a0?",
            "Une personne qui utilise un lecteur d’écran peut ne pas savoir quelle image une légende décrit, "
            "surtout lorsque plusieurs images se suivent.",
        ),
        (
            "6.1",
            "Chaque lien est-il explicite (hors cas particuliers)\u00a0?",
            "Un lien vague comme « Cliquez ici » peut obliger les personnes qui utilisent un lecteur d’écran "
            "à l’ouvrir pour savoir où il mène. Les personnes qui naviguent à la voix peuvent aussi avoir du mal "
            "à activer un lien si son nom ne reprend pas le texte qu’elles voient.",
        ),
        (
            "6.2",
            "Dans chaque page web, chaque lien a-t-il un intitulé\u00a0?",
            "Quand un lien n’a pas de nom, le lecteur d’écran peut annoncer seulement « lien » ou lire une adresse "
            "difficile à comprendre. Les personnes qui l’utilisent ont alors du mal à savoir quel lien ouvrir.",
        ),
        (
            "8.1",
            "Chaque page web est-elle définie par un type de document\u00a0?",
            "Sans indication correcte du type de document, le navigateur peut afficher la page en mode ancien. "
            "Certains textes peuvent alors être plus difficiles à lire pour les personnes malvoyantes qui zooment.",
        ),
        (
            "8.2",
            "Pour chaque page web, le code source généré est-il valide selon le type de document spécifié\u00a0?",
            "Certaines erreurs dans la page peuvent empêcher un lecteur d’écran d’annoncer le nom d’un champ. "
            "La personne qui l’utilise peut alors ne pas savoir quoi saisir.",
        ),
        (
            "8.3",
            "Dans chaque page web, la langue par défaut est-elle présente\u00a0?",
            "Sans indication de la langue principale, un lecteur d’écran peut prononcer toute la page "
            "comme si elle était écrite dans une autre langue. Le texte devient alors difficile à comprendre.",
        ),
        (
            "8.4",
            "Pour chaque page web ayant une langue par défaut, le code de langue est-il pertinent\u00a0?",
            "Si la langue indiquée ne correspond pas au texte, les personnes qui utilisent un lecteur d’écran "
            "risquent d’entendre une prononciation qui rend les mots difficiles à reconnaître.",
        ),
        (
            "8.5",
            "Chaque page web a-t-elle un titre de page\u00a0?",
            "Sans titre, une personne qui utilise un lecteur d’écran peut avoir du mal à identifier la page "
            "qu’elle vient d’ouvrir ou à la retrouver parmi ses onglets.",
        ),
        (
            "8.6",
            "Pour chaque page web ayant un titre de page, ce titre est-il pertinent\u00a0?",
            "Un titre vague comme « Accueil » sur plusieurs pages d’un même site peut empêcher une personne "
            "qui utilise un lecteur d’écran de distinguer ses onglets ou de savoir sur quelle page elle se trouve.",
        ),
        (
            "8.7",
            "Dans chaque page web, chaque changement de langue est-il indiqué dans le code source "
            "(hors cas particuliers)\u00a0?",
            "Si le changement de langue n’est pas signalé, le lecteur d’écran peut prononcer un passage "
            "en anglais comme du français. Les personnes qui l’utilisent peuvent alors mal comprendre ce passage.",
        ),
        (
            "8.8",
            "Dans chaque page web, le code de langue de chaque changement de langue est-il valide et pertinent\u00a0?",
            "Une indication de langue invalide ou erronée peut amener le lecteur d’écran à mal prononcer "
            "le passage concerné. Les personnes qui l’écoutent peuvent ne pas reconnaître les mots.",
        ),
        (
            "8.9",
            "Dans chaque page web, les balises ne doivent pas être utilisées uniquement à des fins de présentation. "
            "Cette règle est-elle respectée\u00a0?",
            "Pour une personne qui utilise un lecteur d’écran, un simple retrait peut être annoncé comme une citation "
            "ou un espace vide comme un titre. Ces annonces peuvent rendre l’organisation de la page confuse.",
        ),
        (
            "8.10",
            "Dans chaque page web, les changements du sens de lecture sont-ils signalés\u00a0?",
            "Sans indication du sens de lecture, les personnes qui lisent un passage en arabe ou en hébreu "
            "peuvent voir des mots, des nombres ou des signes de ponctuation apparaître dans un ordre déroutant.",
        ),
        (
            "10.1",
            "Dans le site web, des feuilles de styles sont-elles utilisées pour contrôler la présentation "
            "de l’information\u00a0?",
            "Quand la mise en forme est inscrite directement dans le contenu, les personnes malvoyantes peuvent "
            "avoir du mal à appliquer leurs propres réglages de taille de texte ou de couleurs.",
        ),
        (
            "10.2",
            "Dans chaque page web, le contenu visible porteur d’information reste-t-il présent lorsque les feuilles "
            "de styles sont désactivées\u00a0?",
            "Les personnes qui désactivent la mise en forme pour lire plus facilement peuvent perdre une information, "
            "par exemple la mention indiquant qu’un champ de formulaire est obligatoire.",
        ),
        (
            "10.3",
            "Dans chaque page web, l’information reste-t-elle compréhensible lorsque les feuilles de styles "
            "sont désactivées\u00a0?",
            "Si la mise en forme change l’ordre des informations, une personne qui utilise un lecteur d’écran "
            "ou désactive la mise en forme peut rencontrer une consigne après l’étape où elle en avait besoin.",
        ),
        (
            "10.4",
            "Dans chaque page web, le texte reste-t-il lisible lorsque la taille des caractères est augmentée "
            "jusqu’à 200\u202f%, au moins (hors cas particuliers)\u00a0?",
            "Lorsqu’une personne malvoyante agrandit le texte, des mots peuvent se chevaucher ou être coupés. "
            "Elle peut alors avoir du mal à lire une consigne ou à identifier un bouton.",
        ),
        (
            "10.5",
            "Dans chaque page web, les déclarations CSS de couleurs de fond d’élément et de police sont-elles "
            "correctement utilisées\u00a0?",
            "Si une couleur ou une image de fond manque, le texte peut se confondre avec l’arrière-plan. "
            "Les personnes malvoyantes peuvent alors avoir du mal à le lire.",
        ),
        (
            "10.6",
            "Dans chaque page web, chaque lien dont la nature n’est pas évidente est-il visible "
            "par rapport au texte environnant\u00a0?",
            "Si seule une différence de couleur signale un lien dans un paragraphe, les personnes daltoniennes "
            "ou malvoyantes peuvent ne pas le repérer.",
        ),
        (
            "10.7",
            "Dans chaque page web, pour chaque élément recevant le focus, la prise de focus est-elle visible\u00a0?",
            "Les personnes qui utilisent la touche Tab pour naviguer peuvent perdre leur place si aucun repère "
            "visible n’indique quel lien, bouton ou champ est sélectionné.",
        ),
        (
            "10.8",
            "Pour chaque page web, les contenus cachés ont-ils vocation à être ignorés "
            "par les technologies d’assistance\u00a0?",
            "Un lecteur d’écran peut annoncer les liens d’un menu fermé et désorienter la personne qui l’utilise. "
            "Il peut aussi passer sous silence une information utile qui devait seulement être cachée à l’écran.",
        ),
        (
            "10.9",
            "Dans chaque page web, l’information ne doit pas être donnée uniquement par la forme, taille ou position. "
            "Cette règle est-elle respectée\u00a0?",
            "Une personne qui utilise un lecteur d’écran peut ne pas savoir quel bouton activer si la consigne "
            "dit seulement « cliquez sur le bouton rond ».",
        ),
        (
            "10.10",
            "Dans chaque page web, l’information ne doit pas être donnée par la forme, taille ou position uniquement. "
            "Cette règle est-elle implémentée de façon pertinente\u00a0?",
            "Une personne malvoyante peut encore hésiter entre plusieurs boutons si la consigne qui complète "
            "« le bouton à droite » dit simplement « le bouton d’action ».",
        ),
        (
            "10.11",
            "Pour chaque page web, les contenus peuvent-ils être présentés sans perte d’information ou de "
            "fonctionnalité et sans avoir recours soit à un défilement vertical pour une fenêtre ayant une hauteur "
            "de 256\u202fpx, soit à un défilement horizontal pour une fenêtre ayant une largeur de 320\u202fpx "
            "(hors cas particuliers)\u00a0?",
            "Quand elles agrandissent la page, les personnes malvoyantes peuvent être obligées de faire défiler "
            "la page de gauche à droite pour lire chaque ligne. Du texte ou des boutons peuvent aussi être coupés.",
        ),
        (
            "10.12",
            "Dans chaque page web, les propriétés d’espacement du texte peuvent-elles être redéfinies par "
            "l’utilisateur sans perte de contenu ou de fonctionnalité (hors cas particuliers)\u00a0?",
            "Certaines personnes dyslexiques augmentent l’espace entre les lettres, les mots ou les lignes "
            "pour lire plus facilement. Si le texte se chevauche ou disparaît, elles peuvent perdre des informations.",
        ),
        (
            "10.13",
            "Dans chaque page web, les contenus additionnels apparaissant à la prise de focus ou au survol "
            "d’un composant d’interface sont-ils contrôlables par l’utilisateur (hors cas particuliers)\u00a0?",
            "Une infobulle impossible à fermer peut masquer le texte qu’une personne malvoyante essaie de lire. "
            "Une personne qui déplace lentement la souris peut aussi voir l’infobulle disparaître trop tôt.",
        ),
        (
            "10.14",
            "Dans chaque page web, les contenus additionnels apparaissant via les styles CSS uniquement "
            "peuvent-ils être rendus visibles au clavier et par tout dispositif de pointage\u00a0?",
            "Une personne qui navigue au clavier peut manquer les consignes d’une infobulle ou les liens "
            "d’un sous-menu si ceux-ci s’affichent seulement au survol de la souris.",
        ),
    )
}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Retourne les informations d'un critère documenté."""
    return _CRITERIA_INFO.get(criterion_id)

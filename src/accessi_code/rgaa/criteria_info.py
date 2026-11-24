"""Intitulés et impacts des critères du thème Images.

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
    )
}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Retourne les informations d'un critère documenté."""
    return _CRITERIA_INFO.get(criterion_id)

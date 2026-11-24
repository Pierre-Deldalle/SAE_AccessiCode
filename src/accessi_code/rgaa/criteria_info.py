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
)

CRITERIA: dict[str, CriterionInfo] = {entry.criterion_id: entry for entry in _ENTRIES}


def criterion_info(criterion_id: str) -> CriterionInfo | None:
    """Explications du critère ``criterion_id`` (par exemple "2.1"), ou None s'il n'est pas renseigné."""
    return CRITERIA.get(criterion_id)

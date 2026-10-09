"""Extraction du contenu source d'une feuille de style CSS."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CssExtraction:
    """
    Résultat de l'extraction d'un fichier CSS.

    Attributes:
        source: Contenu CSS complet lu depuis le fichier.
    """

    source: str


def extract_css(path: Path) -> CssExtraction:
    """
    Lit une feuille de style CSS en UTF-8.

    Les erreurs de décodage sont remplacées afin de permettre la poursuite de
    l'audit même lorsqu'un fichier contient des octets invalides.

    Cette fonction extrait uniquement le contenu source. Elle ne calcule pas
    les styles appliqués aux éléments HTML.

    Args:
        path: Chemin du fichier CSS à lire.

    Returns:
        Le contenu source de la feuille CSS.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        OSError: Si le fichier ne peut pas être lu.
    """

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    return CssExtraction(source=source)
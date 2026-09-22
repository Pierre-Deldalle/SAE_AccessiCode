"""Extraction du texte, du DOM et du DOCTYPE d'un document HTML."""

import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class HtmlExtraction:
    """
    Résultat de l'analyse d'un fichier HTML.

    Attributes:
        source: Source complète lue depuis le fichier.
        dom: Document analysé par BeautifulSoup avec ``html.parser``.
        doctype: Déclaration DOCTYPE complète, ou ``None`` si absente.
    """

    source: str
    dom: BeautifulSoup
    doctype: str | None


def extract_html(path: Path) -> HtmlExtraction:
    """
    Lit et analyse un fichier HTML en UTF-8.

    Les erreurs de décodage sont remplacées afin de permettre la poursuite de
    l'audit même lorsqu'un fichier contient des octets invalides.

    Args:
        path: Chemin du document à lire.

    Returns:
        Les données source, le DOM BeautifulSoup et le DOCTYPE extrait.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        OSError: Si le fichier ne peut pas être lu.
    """

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    dom = BeautifulSoup(
        source,
        "html.parser",
    )

    doctype = extract_doctype(source)

    return HtmlExtraction(
        source=source,
        dom=dom,
        doctype=doctype,
    )


def extract_doctype(
    source: str,
) -> str | None:
    """
    Extrait la déclaration DOCTYPE du document HTML.

    Exemple :
        <!DOCTYPE html>

    Args:
        source: Contenu texte du document HTML.

    Returns:
        La déclaration complète, sans espaces extérieurs, ou ``None`` si le
        document n'en contient pas.
    """

    match = re.search(
        r"<!DOCTYPE\s+[^>]+>",
        source,
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    return match.group(0)
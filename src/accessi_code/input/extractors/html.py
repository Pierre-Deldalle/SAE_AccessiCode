import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class HtmlExtraction:
    """
    Informations extraites d'un document HTML.
    """

    source: str
    dom: BeautifulSoup
    doctype: str | None


def extract_html(path: Path) -> HtmlExtraction:
    """
    Lit et analyse un fichier HTML.
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
    """

    match = re.search(
        r"<!DOCTYPE\s+[^>]+>",
        source,
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    return match.group(0)
from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass
class PageInformation:
    """
    Informations générales extraites de manière déterministe d'une page.
    """

    lang: str | None
    title: str | None
    main_heading: str | None
    content: str


def get_page_language(
    soup: BeautifulSoup,
) -> str | None:
    """
    Retourne la langue déclarée sur l'élément html.
    """
    html_element = soup.find(
        "html"
    )

    if not isinstance(
        html_element,
        Tag,
    ):
        return None

    value = html_element.get(
        "lang"
    )

    if (
        isinstance(value, str)
        and value.strip()
    ):
        return value.strip()

    return None


def get_page_title(
    soup: BeautifulSoup,
) -> str | None:
    """
    Retourne le contenu textuel de la balise title.
    """
    title = soup.find(
        "title"
    )

    if not isinstance(
        title,
        Tag,
    ):
        return None

    value = title.get_text(
        " ",
        strip=True,
    )

    return value or None


def get_main_heading(
    soup: BeautifulSoup,
) -> str | None:
    """
    Retourne le texte du premier h1.
    """
    heading = soup.find(
        "h1"
    )

    if not isinstance(
        heading,
        Tag,
    ):
        return None

    value = heading.get_text(
        " ",
        strip=True,
    )

    return value or None


def get_main_content(
    soup: BeautifulSoup,
) -> str:
    """
    Retourne le texte principal utile à une analyse sémantique.

    Le DOM original n'est pas modifié.
    """
    container = (
        soup.find("main")
        or soup.find("body")
        or soup
    )

    # On reparse uniquement cette petite représentation afin de ne pas
    # supprimer script/style du DOM partagé contenu dans AuditContext.
    copy = BeautifulSoup(
        str(container),
        "html.parser",
    )

    for element in copy.find_all(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        element.decompose()

    return copy.get_text(
        " ",
        strip=True,
    )


def extract_page_information(
    soup: BeautifulSoup,
) -> PageInformation:
    """
    Regroupe les principales informations textuelles d'une page.
    """
    return PageInformation(
        lang=get_page_language(soup),
        title=get_page_title(soup),
        main_heading=get_main_heading(soup),
        content=get_main_content(soup),
    )
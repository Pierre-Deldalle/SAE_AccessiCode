from __future__ import annotations

import re
from dataclasses import dataclass

import langcodes
from bs4 import BeautifulSoup, Tag

DOCTYPE_PATTERN = re.compile(
    r"<!doctype\b[^>]*>",
    flags=re.IGNORECASE,
)

HTML_ELEMENT_PATTERN = re.compile(
    r"<html(?:\s|>)",
    flags=re.IGNORECASE,
)


KNOWN_LEGACY_DOCTYPES = {
    ('<!doctype html public "-//w3c//dtd html 4.01//en" "http://www.w3.org/tr/html4/strict.dtd">'),
    ('<!doctype html public "-//w3c//dtd html 4.01 transitional//en" "http://www.w3.org/tr/html4/loose.dtd">'),
    ('<!doctype html public "-//w3c//dtd html 4.01 frameset//en" "http://www.w3.org/tr/html4/frameset.dtd">'),
    ('<!doctype html public "-//w3c//dtd xhtml 1.0 strict//en" "http://www.w3.org/tr/xhtml1/dtd/xhtml1-strict.dtd">'),
    (
        '<!doctype html public "-//w3c//dtd xhtml 1.0 transitional//en" '
        '"http://www.w3.org/tr/xhtml1/dtd/xhtml1-transitional.dtd">'
    ),
    (
        '<!doctype html public "-//w3c//dtd xhtml 1.0 frameset//en" '
        '"http://www.w3.org/tr/xhtml1/dtd/xhtml1-frameset.dtd">'
    ),
    ('<!doctype html public "-//w3c//dtd xhtml 1.1//en" "http://www.w3.org/tr/xhtml11/dtd/xhtml11.dtd">'),
}


@dataclass
class PageInformation:
    """
    Informations générales extraites de manière déterministe d'une page.
    """

    lang: str | None
    title: str | None
    main_heading: str | None
    content: str


def get_document_doctype(
    html_source: str,
) -> str | None:
    """
    Retourne la déclaration DOCTYPE telle qu'elle apparaît dans le source.
    """
    match = DOCTYPE_PATTERN.search(html_source)

    if match is None:
        return None

    return match.group(0)


def normalize_doctype(
    doctype: str,
) -> str:
    """
    Normalise uniquement les espaces et la casse pour faciliter les comparaisons.
    """
    return " ".join(doctype.split()).strip().lower()


def is_html5_doctype(
    doctype: str | None,
) -> bool:
    """
    Indique si le DOCTYPE correspond au DOCTYPE HTML5 standard.
    """
    if doctype is None:
        return False

    return normalize_doctype(doctype) == "<!doctype html>"


def validate_document_doctype(
    doctype: str,
) -> bool | None:
    """
    Valide les DOCTYPE HTML courants.

    True :
        DOCTYPE reconnu comme valide.

    False :
        syntaxe manifestement invalide.

    None :
        syntaxe plausible d'un ancien DOCTYPE externe mais déclaration
        non reconnue dans notre liste. Une vérification humaine reste alors
        préférable à un faux FAIL.
    """
    normalized = normalize_doctype(doctype)

    if normalized == "<!doctype html>":
        return True

    if normalized in KNOWN_LEGACY_DOCTYPES:
        return True

    syntactically_valid = re.fullmatch(
        (
            r"<!doctype\s+html"
            r'(?:\s+public\s+"[^"]+"(?:\s+"[^"]+")?'
            r'|\s+system\s+"[^"]+")'
            r"\s*>"
        ),
        normalized,
        flags=re.IGNORECASE,
    )

    if syntactically_valid:
        return None

    return False


def is_doctype_before_html(
    html_source: str,
) -> bool | None:
    """
    Vérifie que le DOCTYPE apparaît avant l'élément racine html.

    None signifie que l'élément html n'a pas pu être retrouvé.
    """
    doctype_match = DOCTYPE_PATTERN.search(html_source)

    if doctype_match is None:
        return False

    html_match = HTML_ELEMENT_PATTERN.search(html_source)

    if html_match is None:
        return None

    return doctype_match.start() < html_match.start()


def get_page_language(
    soup: BeautifulSoup,
) -> str | None:
    """
    Retourne la langue par défaut déclarée sur l'élément html.
    """
    html_element = soup.find("html")

    if not isinstance(
        html_element,
        Tag,
    ):
        return None

    for attribute in (
        "lang",
        "xml:lang",
    ):
        value = html_element.get(attribute)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def is_valid_language_code(
    value: str,
) -> bool:
    """
    Vérifie la partie principale du code de langue.

    Le RGAA porte la validation sur le code situé avant l'éventuelle
    option régionale, par exemple "fr" dans "fr-FR".
    """
    primary_code = value.strip().split("-", 1)[0].lower()

    if len(primary_code) not in {
        2,
        3,
    }:
        return False

    if not primary_code.isalpha():
        return False

    return bool(langcodes.tag_is_valid(primary_code))


def has_page_title_element(
    soup: BeautifulSoup,
) -> bool:
    """
    Indique si une balise title est présente, indépendamment de son contenu.
    """
    return isinstance(
        soup.find("title"),
        Tag,
    )


def get_page_title(
    soup: BeautifulSoup,
) -> str | None:
    """
    Retourne le contenu textuel de la balise title.
    """
    title = soup.find("title")

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
    heading = soup.find("h1")

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
    Retourne le contenu textuel principal sans modifier le DOM partagé.
    """
    container = soup.find("main") or soup.find("body") or soup

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
    return PageInformation(
        lang=get_page_language(soup),
        title=get_page_title(soup),
        main_heading=get_main_heading(soup),
        content=get_main_content(soup),
    )

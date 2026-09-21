
from __future__ import annotations

from bs4 import BeautifulSoup, Tag


# Types de champs de formulaire pris en charge
FORM_FIELD_SELECTORS = (
    "input:not([type='hidden']):not([type='submit'])"
    ":not([type='reset']):not([type='button'])"
    ":not([type='image'])",
    "textarea",
    "select",
)


def find_form_fields(soup: BeautifulSoup) -> list[Tag]:
    """Retourne les champs de formulaire analysés par le prototype."""

    fields: list[Tag] = []

    for selector in FORM_FIELD_SELECTORS:
        fields.extend(soup.select(selector))

    return fields


def get_element_identifier(element: Tag, index: int) -> str:
    """Retourne un identifiant lisible pour un élément HTML."""

    element_id = element.get("id")

    if isinstance(element_id, str) and element_id.strip():
        return f"{element.name}#{element_id}"

    name = element.get("name")

    if isinstance(name, str) and name.strip():
        return f"{element.name}[name='{name}']"

    return f"{element.name}[index={index}]"


def get_non_empty_attribute(
    element: Tag,
    attribute_name: str,
) -> str | None:
    """Retourne un attribut texte s'il existe et n'est pas vide."""

    value = element.get(attribute_name)

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def get_labelledby_text(
    element: Tag,
    soup: BeautifulSoup,
) -> tuple[bool, str]:
    """
    Vérifie aria-labelledby.

    Retourne :
        (références_valides, texte_referencé)
    """

    value = get_non_empty_attribute(element, "aria-labelledby")

    if value is None:
        return False, ""

    identifiers = value.split()

    referenced_elements: list[Tag] = []

    for identifier in identifiers:
        referenced = soup.find(id=identifier)

        if not isinstance(referenced, Tag):
            return False, ""

        referenced_elements.append(referenced)

    text = " ".join(
        referenced.get_text(" ", strip=True)
        for referenced in referenced_elements
    )

    if not text.strip():
        return False, ""

    return True, text


def has_aria_label(element: Tag) -> bool:
    """Vérifie la présence d'un aria-label non vide."""

    return get_non_empty_attribute(element, "aria-label") is not None


def has_title(element: Tag) -> bool:
    """Vérifie la présence d'un title non vide."""

    return get_non_empty_attribute(element, "title") is not None


def get_matching_label(
    element: Tag,
    soup: BeautifulSoup,
) -> Tag | None:
    """
    Recherche une balise label associée au champ.

    Vérifie l'association explicite via for/id.
    """

    element_id = element.get("id")

    if not isinstance(element_id, str) or not element_id.strip():
        return None

    label = soup.find("label", attrs={"for": element_id})

    if isinstance(label, Tag):
        return label

    return None


def has_matching_label(
    element: Tag,
    soup: BeautifulSoup,
) -> bool:
    """Vérifie si le champ possède un label associé."""

    label = get_matching_label(element, soup)

    if label is None:
        return False

    return bool(label.get_text(" ", strip=True))


def get_labeling_evidence(
    element: Tag,
    soup: BeautifulSoup,
) -> list[str]:
    """
    Retourne les mécanismes d'étiquetage détectés.

    Cette fonction ne constitue pas une décision complète de conformité.
    """

    evidence: list[str] = []

    labelledby_valid, _ = get_labelledby_text(element, soup)

    if labelledby_valid:
        evidence.append("aria-labelledby")

    if has_aria_label(element):
        evidence.append("aria-label")

    if has_matching_label(element, soup):
        evidence.append("label-for")

    if has_title(element):
        evidence.append("title")

    return evidence
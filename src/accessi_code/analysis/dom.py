from __future__ import annotations

from bs4 import BeautifulSoup, Tag


FORM_FIELD_SELECTORS = (
    "input:not([type='hidden'])"
    ":not([type='submit'])"
    ":not([type='reset'])"
    ":not([type='button'])"
    ":not([type='image'])",
    "textarea",
    "select",
)


def find_form_fields(
    soup: BeautifulSoup,
) -> list[Tag]:
    """
    Retourne les champs de formulaire nécessitant potentiellement une étiquette.
    """
    fields: list[Tag] = []

    for selector in FORM_FIELD_SELECTORS:
        fields.extend(
            soup.select(selector)
        )

    return fields


def get_element_identifier(
    element: Tag,
    index: int,
) -> str:
    """
    Génère un identifiant humainement lisible pour un élément.
    """
    element_id = element.get("id")

    if (
        isinstance(element_id, str)
        and element_id.strip()
    ):
        return (
            f"{element.name}#{element_id}"
        )

    name = element.get("name")

    if (
        isinstance(name, str)
        and name.strip()
    ):
        return (
            f"{element.name}"
            f"[name='{name}']"
        )

    return (
        f"{element.name}"
        f"[index={index}]"
    )


def get_non_empty_attribute(
    element: Tag,
    attribute_name: str,
) -> str | None:
    """
    Retourne la valeur nettoyée d'un attribut texte non vide.
    """
    value = element.get(
        attribute_name
    )

    if (
        isinstance(value, str)
        and value.strip()
    ):
        return value.strip()

    return None


def get_labelledby_text(
    element: Tag,
    soup: BeautifulSoup,
) -> tuple[bool, str]:
    """
    Résout les éléments référencés par aria-labelledby.
    """
    value = get_non_empty_attribute(
        element,
        "aria-labelledby",
    )

    if value is None:
        return False, ""

    identifiers = value.split()

    texts: list[str] = []

    for identifier in identifiers:
        referenced = soup.find(
            id=identifier
        )

        if not isinstance(
            referenced,
            Tag,
        ):
            return False, ""

        text = referenced.get_text(
            " ",
            strip=True,
        )

        if not text:
            return False, ""

        texts.append(text)

    return True, " ".join(texts)


def has_aria_label(
    element: Tag,
) -> bool:
    return (
        get_non_empty_attribute(
            element,
            "aria-label",
        )
        is not None
    )


def has_title(
    element: Tag,
) -> bool:
    return (
        get_non_empty_attribute(
            element,
            "title",
        )
        is not None
    )


def get_matching_label(
    element: Tag,
    soup: BeautifulSoup,
) -> Tag | None:
    """
    Recherche un label explicitement lié par for/id.
    """
    element_id = get_non_empty_attribute(
        element,
        "id",
    )

    if element_id is None:
        return None

    label = soup.find(
        "label",
        attrs={
            "for": element_id,
        },
    )

    return (
        label
        if isinstance(label, Tag)
        else None
    )


def has_matching_label(
    element: Tag,
    soup: BeautifulSoup,
) -> bool:
    label = get_matching_label(
        element,
        soup,
    )

    if label is None:
        return False

    return bool(
        label.get_text(
            " ",
            strip=True,
        )
    )


def get_wrapping_label(
    element: Tag,
) -> Tag | None:
    """
    Recherche un label englobant directement le champ.
    """
    label = element.find_parent(
        "label"
    )

    if isinstance(label, Tag):
        return label

    return None


def has_wrapping_label(
    element: Tag,
) -> bool:
    label = get_wrapping_label(
        element
    )

    if label is None:
        return False

    return bool(
        label.get_text(
            " ",
            strip=True,
        )
    )


def get_labeling_evidence(
    element: Tag,
    soup: BeautifulSoup,
) -> list[str]:
    """
    Retourne les mécanismes d'étiquetage structurels détectés.

    Cette fonction collecte des preuves mais ne décide pas à elle seule
    de la conformité RGAA.
    """
    evidence: list[str] = []

    labelledby_valid, _ = (
        get_labelledby_text(
            element,
            soup,
        )
    )

    if labelledby_valid:
        evidence.append(
            "aria-labelledby"
        )

    if has_aria_label(element):
        evidence.append(
            "aria-label"
        )

    if has_matching_label(
        element,
        soup,
    ):
        evidence.append(
            "label-for"
        )

    if has_wrapping_label(
        element
    ):
        evidence.append(
            "label-wrapper"
        )

    if has_title(element):
        evidence.append(
            "title"
        )

    return evidence
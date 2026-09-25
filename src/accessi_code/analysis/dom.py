from __future__ import annotations

from bs4 import BeautifulSoup, Tag

FORM_FIELD_SELECTORS = (
    "input:not([type='hidden']):not([type='submit']):not([type='reset']):not([type='button']):not([type='image'])",
    "textarea",
    "select",
    "output",
    "progress",
    "meter",
    "[role='progressbar']",
    "[role='slider']",
    "[role='spinbutton']",
    "[role='textbox']",
    "[role='listbox']",
    "[role='searchbox']",
    "[role='combobox']",
    "[role='checkbox']",
    "[role='radio']",
    "[role='switch']",
)


LABELABLE_NATIVE_ELEMENTS = {
    "input",
    "textarea",
    "select",
    "output",
    "progress",
    "meter",
}


def find_form_fields(
    soup: BeautifulSoup,
) -> list[Tag]:
    """
    Retourne les champs de formulaire entrant dans le périmètre
    des contrôles d'étiquetage.
    """
    fields: list[Tag] = []
    seen: set[int] = set()

    for selector in FORM_FIELD_SELECTORS:
        for element in soup.select(selector):
            element_id = id(element)

            if element_id in seen:
                continue

            seen.add(element_id)
            fields.append(element)

    return fields


def get_element_identifier(
    element: Tag,
    index: int,
) -> str:
    element_id = element.get("id")

    if isinstance(element_id, str) and element_id.strip():
        return f"{element.name}#{element_id}"

    name = element.get("name")

    if isinstance(name, str) and name.strip():
        return f"{element.name}[name='{name}']"

    role = element.get("role")

    if isinstance(role, str) and role.strip():
        return f"[role='{role}'][index={index}]"

    return f"{element.name}[index={index}]"


def get_non_empty_attribute(
    element: Tag,
    attribute_name: str,
) -> str | None:
    value = element.get(attribute_name)

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def get_labelledby_text(
    element: Tag,
    soup: BeautifulSoup,
) -> tuple[bool, str]:
    """
    Résout aria-labelledby.

    Chaque identifiant doit exister une seule fois et référencer
    un passage de texte non vide.
    """
    value = get_non_empty_attribute(
        element,
        "aria-labelledby",
    )

    if value is None:
        return False, ""

    texts: list[str] = []

    for identifier in value.split():
        matches = soup.find_all(id=identifier)

        if len(matches) != 1:
            return False, ""

        referenced = matches[0]

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
    Recherche un label explicitement associé via for/id.
    """
    if element.name not in LABELABLE_NATIVE_ELEMENTS:
        return None

    element_id = get_non_empty_attribute(
        element,
        "id",
    )

    if element_id is None:
        return None

    labels = soup.find_all(
        "label",
        attrs={
            "for": element_id,
        },
    )

    if len(labels) != 1:
        return None

    label = labels[0]

    return label if isinstance(label, Tag) else None


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
    label = element.find_parent("label")

    return label if isinstance(label, Tag) else None


def has_wrapping_label(
    element: Tag,
) -> bool:
    label = get_wrapping_label(element)

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
    *,
    include_wrapping_label: bool = False,
) -> list[str]:
    """
    Retourne les mécanismes d'étiquetage structurels détectés.

    Pour le test RGAA 11.1.1, include_wrapping_label doit rester False :
    la méthodologie officielle cite explicitement label[for].
    """
    evidence: list[str] = []

    labelledby_valid, _ = get_labelledby_text(
        element,
        soup,
    )

    if labelledby_valid:
        evidence.append("aria-labelledby")

    if has_aria_label(element):
        evidence.append("aria-label")

    if has_matching_label(
        element,
        soup,
    ):
        evidence.append("label-for")

    if include_wrapping_label and has_wrapping_label(element):
        evidence.append("label-wrapper")

    if has_title(element):
        evidence.append("title")

    return evidence

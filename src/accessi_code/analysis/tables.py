from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def find_tables(
    soup: BeautifulSoup,
) -> list[Tag]:
    """
    Retourne les tableaux HTML natifs et les tableaux ARIA.
    """
    return list(
        soup.select(
            "table, [role='table']"
        )
    )


def get_table_rows(
    table: Tag,
) -> list[Tag]:
    """
    Retourne les lignes d'un tableau natif ou ARIA.
    """
    rows: list[Tag] = []

    for element in table.find_all(
        [
            "tr",
            "div",
        ]
    ):
        if element.name == "tr":
            rows.append(element)

        elif (
            element.get("role")
            == "row"
        ):
            rows.append(element)

    return rows


def get_row_cells(
    row: Tag,
) -> list[Tag]:
    """
    Retourne les cellules directes d'une ligne HTML ou ARIA.
    """
    cells: list[Tag] = []

    for element in row.find_all(
        recursive=False
    ):
        if not isinstance(
            element,
            Tag,
        ):
            continue

        if element.name in {
            "th",
            "td",
        }:
            cells.append(element)

        elif element.get(
            "role"
        ) in {
            "cell",
            "columnheader",
            "rowheader",
        }:
            cells.append(element)

    return cells


def get_int_attribute(
    element: Tag,
    attribute_name: str,
) -> int:
    """
    Retourne un attribut entier strictement positif.

    Une valeur manquante ou invalide correspond à 1.
    """
    value = element.get(
        attribute_name
    )

    try:
        parsed = int(
            str(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return 1

    return (
        parsed
        if parsed > 0
        else 1
    )


def is_header_cell(
    cell: Tag,
) -> bool:
    """
    Détermine si une cellule représente un en-tête.
    """
    return (
        cell.name == "th"
        or cell.get("role")
        in {
            "columnheader",
            "rowheader",
        }
    )


def has_complex_header_structure(
    table: Tag,
) -> bool:
    """
    Détecte plusieurs indices de structure potentiellement complexe.

    Il s'agit volontairement d'une heuristique et non d'un verdict RGAA.
    """
    rows = get_table_rows(
        table
    )

    if not rows:
        return False

    for row_index, row in enumerate(
        rows
    ):
        cells = get_row_cells(
            row
        )

        for cell in cells:
            if not is_header_cell(
                cell
            ):
                continue

            rowspan = get_int_attribute(
                cell,
                "rowspan",
            )

            colspan = get_int_attribute(
                cell,
                "colspan",
            )

            if (
                rowspan > 1
                or colspan > 1
            ):
                return True

            if row_index > 0:
                return True

    return False


def get_referenced_text(
    element: Tag,
    soup: BeautifulSoup,
    attribute_name: str = "aria-describedby",
) -> tuple[bool, str]:
    """
    Résout une liste d'identifiants référencés par un attribut ARIA.
    """
    value = element.get(
        attribute_name
    )

    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        return False, ""

    texts: list[str] = []

    for identifier in value.split():
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


def get_table_summary_evidence(
    table: Tag,
    soup: BeautifulSoup,
) -> list[str]:
    """
    Retourne les mécanismes de description/résumé détectés.

    Cette fonction collecte uniquement des preuves structurelles.
    """
    evidence: list[str] = []

    caption = table.find(
        "caption",
        recursive=False,
    )

    if (
        isinstance(caption, Tag)
        and caption.get_text(
            " ",
            strip=True,
        )
    ):
        evidence.append(
            "caption"
        )

    summary = table.get(
        "summary"
    )

    if (
        isinstance(summary, str)
        and summary.strip()
    ):
        evidence.append(
            "summary"
        )

    aria_valid, _ = (
        get_referenced_text(
            table,
            soup,
            "aria-describedby",
        )
    )

    if aria_valid:
        evidence.append(
            "aria-describedby"
        )

    return evidence
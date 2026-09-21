
from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def find_tables(soup: BeautifulSoup) -> list[Tag]:
    """Retourne les tableaux HTML et les éléments role=table."""

    # Les tableaux natifs et les tableaux ARIA doivent être analysés.
    return soup.select("table, [role='table']")


def get_table_rows(table: Tag) -> list[Tag]:
    """
    Retourne les lignes d'un tableau.

    Supporte les tableaux HTML natifs et les structures
    utilisant role=table.
    """

    return table.find_all("tr")


def get_row_cells(row: Tag) -> list[Tag]:
    """Retourne les cellules d'une ligne."""

    return row.find_all(["th", "td"], recursive=False)


def get_int_attribute(
    element: Tag,
    attribute_name: str,
) -> int:
    """Retourne un attribut entier positif ou 1 par défaut."""

    value = element.get(attribute_name)

    try:
        parsed = int(str(value))
        return parsed if parsed > 0 else 1
    except (TypeError, ValueError):
        return 1


def has_complex_header_structure(table: Tag) -> bool:
    """
    Heuristique pour détecter un tableau potentiellement complexe.

    Indices utilisés :
    - Une cellule th après la première ligne.
    - Un rowspan ou colspan supérieur à 1.
    """

    rows = get_table_rows(table)

    if not rows:
        return False

    has_header = False

    for row_index, row in enumerate(rows):
        cells = get_row_cells(row)

        for column_index, cell in enumerate(cells):
            if cell.name != "th":
                continue

            has_header = True

            # Une fusion de cellules révèle une structure de relations entre
            # plusieurs lignes ou colonnes, caractéristique d'un tableau complexe.
            rowspan = get_int_attribute(cell, "rowspan")
            colspan = get_int_attribute(cell, "colspan")

            if rowspan > 1 or colspan > 1:
                return True

            if row_index > 0:
                return True

    return False if has_header else False


def get_referenced_text(
    element: Tag,
    soup: BeautifulSoup,
) -> tuple[bool, str]:
    """
    Résout les identifiants d'un attribut aria-describedby.

    Retourne :
        (références présentes et non vides, texte)
    """

    value = element.get("aria-describedby")

    if not isinstance(value, str) or not value.strip():
        return False, ""

    identifiers = value.split()
    referenced_elements: list[Tag] = []

    for identifier in identifiers:
        # Toutes les références doivent être résolues pour que le nom associé
        # au tableau soit considéré comme exploitable.
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


def get_table_summary_evidence(
    table: Tag,
    soup: BeautifulSoup,
) -> list[str]:
    """
    Retourne les mécanismes de résumé détectés pour un tableau.

    Mécanismes :
    - caption
    - summary (ancien HTML/XHTML)
    - aria-describedby
    """

    evidence: list[str] = []

    # Plusieurs mécanismes peuvent coexister : on conserve toutes les preuves.
    caption = table.find("caption", recursive=False)

    if isinstance(caption, Tag):
        if caption.get_text(" ", strip=True):
            evidence.append("caption")

    summary = table.get("summary")

    if isinstance(summary, str) and summary.strip():
        evidence.append("summary")

    aria_valid, _ = get_referenced_text(table, soup)

    if aria_valid:
        evidence.append("aria-describedby")

    return evidence
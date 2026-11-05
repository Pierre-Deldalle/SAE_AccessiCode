from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def find_tables(
    soup: BeautifulSoup,
) -> list[Tag]:
    return list(soup.select("table, [role='table']"))


def get_table_rows(
    table: Tag,
) -> list[Tag]:
    rows: list[Tag] = []

    for element in table.find_all(
        [
            "tr",
            "div",
        ]
    ):
        if element.name == "tr":
            rows.append(element)

        elif element.get("role") == "row":
            rows.append(element)

    return rows


def get_row_cells(
    row: Tag,
) -> list[Tag]:
    cells: list[Tag] = []

    for element in row.find_all(recursive=False):
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

        elif element.get("role") in {
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
    value = element.get(attribute_name)

    try:
        parsed = int(str(value))

    except (
        TypeError,
        ValueError,
    ):
        return 1

    return parsed if parsed > 0 else 1


def is_header_cell(
    cell: Tag,
) -> bool:
    return cell.name == "th" or cell.get("role") in {
        "columnheader",
        "rowheader",
    }


def has_complex_header_structure(
    table: Tag,
) -> bool:
    """
    Recherche des indices structurels correspondant à la définition
    RGAA d'un tableau de données complexe.

    Ce test reste volontairement prudent : il analyse la structure
    déclarée par l'auteur, pas l'intention visuelle.
    """
    role = table.get("role")

    if role in {
        "presentation",
        "none",
    }:
        return False

    rows = get_table_rows(table)

    if not rows:
        return False

    for row_index, row in enumerate(rows):
        cells = get_row_cells(row)

        for column_index, cell in enumerate(cells):
            if is_header_cell(cell):
                rowspan = get_int_attribute(
                    cell,
                    "rowspan",
                )

                colspan = get_int_attribute(
                    cell,
                    "colspan",
                )

                if rowspan > 1 or colspan > 1:
                    return True

                scope = cell.get("scope")

                if scope in {
                    "rowgroup",
                    "colgroup",
                }:
                    return True

                # Un en-tête ailleurs que sur la première ligne
                # ou la première colonne indique une structure imbriquée.
                if row_index > 0 and column_index > 0:
                    return True

            headers = cell.get("headers")

            if isinstance(
                headers,
                list,
            ):
                header_ids = [str(value) for value in headers]

            elif isinstance(
                headers,
                str,
            ):
                header_ids = headers.split()

            else:
                header_ids = []

            if len(header_ids) > 1:
                return True

    return False


def get_referenced_text(
    element: Tag,
    soup: BeautifulSoup,
    attribute_name: str = "aria-describedby",
) -> tuple[bool, str]:
    value = element.get(attribute_name)

    if not isinstance(value, str) or not value.strip():
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


def get_table_summary_evidence(
    table: Tag,
    soup: BeautifulSoup,
    *,
    allow_legacy_summary: bool = False,
) -> list[str]:
    """
    Retourne les mécanismes de résumé utilisables pour le test 5.1.1.
    """
    evidence: list[str] = []

    caption = table.find(
        "caption",
        recursive=False,
    )

    if isinstance(caption, Tag) and caption.get_text(
        " ",
        strip=True,
    ):
        evidence.append("caption")

    if allow_legacy_summary:
        summary = table.get("summary")

        if isinstance(summary, str) and summary.strip():
            evidence.append("summary")

    aria_valid, _ = get_referenced_text(
        table,
        soup,
    )

    if aria_valid:
        evidence.append("aria-describedby")

    return evidence

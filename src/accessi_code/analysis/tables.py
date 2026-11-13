from __future__ import annotations

from dataclasses import dataclass

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


# Classement des cellules selon leur position (critères 5.6 et 5.7).

COLUMN_HEADER = "column_header"
ROW_HEADER = "row_header"
DATA = "data"

_HEADER_ROLES = {"columnheader", "rowheader"}
_IGNORED_ROW_CHILDREN = {"script", "style", "template"}


@dataclass(frozen=True, slots=True)
class TableSlot:
    """Une position dans un tableau et l'élément qui l'occupe."""

    item: Tag
    kind: str
    table_index: int
    row_index: int
    col_index: int

    @property
    def selector(self) -> str:
        item_id = self.item.get("id")
        if isinstance(item_id, str) and item_id.strip():
            return f"#{item_id.strip()}"
        return (
            f"table[index={self.table_index}] > tr:nth-of-type({self.row_index + 1})"
            f" > *:nth-child({self.col_index + 1})"
        )


def cell_role(item: Tag) -> str:
    return str(item.get("role", "")).strip().lower()


def is_header_like(item: Tag) -> bool:
    return item.name == "th" or cell_role(item) in _HEADER_ROLES


def is_data_like(item: Tag) -> bool:
    return not is_header_like(item) and (item.name == "td" or cell_role(item) == "cell")


def get_row_items(row: Tag) -> list[Tag]:
    """Éléments placés directement dans une ligne, cellules ou non."""
    return [
        child
        for child in row.find_all(recursive=False)
        if isinstance(child, Tag) and child.name not in _IGNORED_ROW_CHILDREN
    ]


def is_in_thead(row: Tag, table: Tag) -> bool:
    parent = row.parent
    while isinstance(parent, Tag) and parent is not table:
        if parent.name == "thead":
            return True
        parent = parent.parent
    return False


def is_presentation_table(table: Tag) -> bool:
    """Tableau explicitement déclaré comme tableau de mise en forme."""
    return cell_role(table) in {"presentation", "none"}


def classify_table_cells(table: Tag, table_index: int) -> list[TableSlot]:
    """
    Classe chaque élément d'un tableau selon sa position, sans tenir compte
    de la balise utilisée (th, td, span…) :

    - éléments d'une ligne de <thead>, ou d'une première ligne entièrement
      composée d'en-têtes : en-têtes de colonne ;
    - premier élément d'une ligne contenant des données, s'il n'est ni une
      cellule de donnée ni une cellule référençant des en-têtes : en-tête de ligne ;
    - le reste : cellules de données.
    """
    rows = get_table_rows(table)
    items_by_row = [get_row_items(row) for row in rows]

    first_row = items_by_row[0] if items_by_row else []
    first_row_is_header_row = bool(first_row) and all(is_header_like(item) for item in first_row)

    slots: list[TableSlot] = []

    for row_index, (row, items) in enumerate(zip(rows, items_by_row)):
        is_header_row = is_in_thead(row, table) or (row_index == 0 and first_row_is_header_row)

        for col_index, item in enumerate(items):
            if is_header_row:
                kind = COLUMN_HEADER
            elif (
                col_index == 0
                and not is_data_like(item)
                and not (item.has_attr("headers") and not is_header_like(item))
                and any(is_data_like(other) for other in items[1:])
            ):
                kind = ROW_HEADER
            else:
                kind = DATA

            slots.append(TableSlot(item, kind, table_index, row_index, col_index))

    return slots


def table_grid(table: Tag) -> dict[int, tuple[Tag, int, int, int, int]]:
    """
    Position réelle de chaque cellule dans la grille du tableau.

    Retourne id(cellule) -> (cellule, ligne, colonne, rowspan, colspan), en
    tenant compte des cellules fusionnées (colspan, rowspan) des lignes
    précédentes, comme le fait un navigateur.
    """
    occupied: set[tuple[int, int]] = set()
    positions: dict[int, tuple[Tag, int, int, int, int]] = {}

    for row_index, row in enumerate(get_table_rows(table)):
        col_index = 0
        for cell in get_row_cells(row):
            while (row_index, col_index) in occupied:
                col_index += 1
            rowspan = get_int_attribute(cell, "rowspan")
            colspan = get_int_attribute(cell, "colspan")
            for dr in range(rowspan):
                for dc in range(colspan):
                    occupied.add((row_index + dr, col_index + dc))
            positions[id(cell)] = (cell, row_index, col_index, rowspan, colspan)
            col_index += colspan

    return positions


def associated_headers(table: Tag, cell: Tag) -> list[Tag]:
    """
    En-têtes associés à une cellule d'après la structure du tableau :
    en-têtes de colonne situés au-dessus et en-têtes de ligne situés à
    gauche, sur les colonnes et les lignes réellement couvertes.
    """
    positions = table_grid(table)
    if id(cell) not in positions:
        return []
    kinds = {id(slot.item): slot.kind for slot in classify_table_cells(table, 0)}
    _, row, col, rowspan, colspan = positions[id(cell)]

    headers: list[Tag] = []
    for other, other_row, other_col, other_rowspan, other_colspan in positions.values():
        if other is cell:
            continue
        kind = kinds.get(id(other))
        same_columns = other_col < col + colspan and col < other_col + other_colspan
        same_rows = other_row < row + rowspan and row < other_row + other_rowspan
        if kind == COLUMN_HEADER and other_row + other_rowspan <= row and same_columns:
            headers.append(other)
        elif kind == ROW_HEADER and other_col + other_colspan <= col and same_rows:
            headers.append(other)
    return headers


# Textes soumis à l'IA (critères 5.2, 5.3 et 5.5).

_PREVIEW_ROWS = 4
_LINEARIZED_LIMIT = 1500


def table_identifier(table: Tag, index: int) -> str:
    """Identifiant lisible d'un tableau dans les observations."""
    table_id = table.get("id")
    if isinstance(table_id, str) and table_id.strip():
        return f"table#{table_id.strip()}"
    return f"table[index={index}]"


def has_header_cells(table: Tag) -> bool:
    """Tableau contenant au moins une cellule d'en-tête (th, columnheader, rowheader)."""
    return any(is_header_cell(cell) for row in get_table_rows(table) for cell in get_row_cells(row))


def _text(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def table_titles(table: Tag, soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    Titres associés au tableau (RGAA 5.4) : liste de (mécanisme, texte) non vides.

    Mécanismes : caption, title, aria-label, aria-labelledby.
    """
    titles: list[tuple[str, str]] = []
    caption = table.find("caption", recursive=False)
    if isinstance(caption, Tag) and _text(caption):
        titles.append(("caption", _text(caption)))
    for attribute in ("title", "aria-label"):
        value = " ".join(str(table.get(attribute) or "").split())
        if value:
            titles.append((attribute, value))
    valid, text = get_referenced_text(table, soup, "aria-labelledby")
    if valid:
        titles.append(("aria-labelledby", " ".join(text.split())))
    return titles


def table_summaries(table: Tag, soup: BeautifulSoup, *, allow_legacy_summary: bool) -> list[tuple[str, str]]:
    """
    Résumés disponibles pour un tableau complexe (RGAA 5.1) : liste de (mécanisme, texte).

    Mécanismes : caption, aria-describedby et, hors HTML5, l'attribut summary.
    """
    summaries: list[tuple[str, str]] = []
    caption = table.find("caption", recursive=False)
    if isinstance(caption, Tag) and _text(caption):
        summaries.append(("caption", _text(caption)))
    valid, text = get_referenced_text(table, soup, "aria-describedby")
    if valid:
        summaries.append(("aria-describedby", " ".join(text.split())))
    if allow_legacy_summary:
        summary = " ".join(str(table.get("summary") or "").split())
        if summary:
            summaries.append(("summary", summary))
    return summaries


def table_preview(table: Tag, rows: int = _PREVIEW_ROWS) -> str:
    """En-têtes et premières lignes du tableau, une ligne par rangée (« | » entre cellules)."""
    lines = []
    for row in get_table_rows(table)[:rows]:
        cells = [_text(cell) for cell in get_row_cells(row)]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def linearized_table_text(table: Tag, limit: int = _LINEARIZED_LIMIT) -> str:
    """
    Contenu d'un tableau lu dans l'ordre du code, cellule par cellule
    (ce que restitue un lecteur d'écran pour un tableau de mise en forme).
    """
    parts: list[str] = []
    for row in get_table_rows(table):
        for cell in get_row_cells(row):
            text = _text(cell)
            if text:
                parts.append(text)
    if not parts:
        parts = [_text(table)] if _text(table) else []
    return "\n".join(parts)[:limit]


def has_single_header_axis(table: Tag) -> bool:
    """
    Tous les en-têtes sont sur une seule ligne ou dans une seule colonne
    (cas particulier du RGAA 5.7 : th sans scope admis).
    """
    rows_with_headers: set[int] = set()
    columns_with_headers: set[int] = set()
    for row_index, row in enumerate(get_table_rows(table)):
        col_index = 0
        for cell in get_row_cells(row):
            if is_header_cell(cell):
                rows_with_headers.add(row_index)
                columns_with_headers.add(col_index)
            col_index += get_int_attribute(cell, "colspan")
    if not rows_with_headers:
        return False
    return len(rows_with_headers) == 1 or len(columns_with_headers) == 1

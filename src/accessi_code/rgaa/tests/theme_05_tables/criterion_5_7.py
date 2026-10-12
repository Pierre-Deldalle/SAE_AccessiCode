from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.tables import (
    get_table_rows,
    get_row_cells,
    get_int_attribute,
    is_header_cell,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test571(RGAATest):
    test_id = "5.7.1"
    criterion_id = "5.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.7.1 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables = []
        for table in tables:
            if self._has_header_cells(table):
                data_tables.append(table)

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        header_findings: list[Finding] = []
        total_headers_entire = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    if is_header_cell(cell):
                        if self._applies_to_entire_column(cell, table, row_index, col_index) or \
                           self._applies_to_entire_row(cell, table, row_index, col_index):
                            total_headers_entire += 1

                            if not self._has_proper_header_identification(cell):
                                table_id = table.get("id")
                                row_id = row.get("id")
                                cell_id = cell.get("id")

                                if isinstance(cell_id, str) and cell_id.strip():
                                    element = f"#{cell_id}"
                                elif isinstance(row_id, str) and row_id.strip():
                                    element = f"#{row_id} > *[{self._get_cell_index_string(row, col_index)}]"
                                elif isinstance(table_id, str) and table_id.strip():
                                    element = f"#{table_id} > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"
                                else:
                                    element = f"table[index={table_index}] > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"

                                header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'en-tête de ligne ou de colonne doit avoir un identifiant unique (id), un attribut scope ou un rôle role='rowheader' ou role='columnheader'."),
                                        recommendation=("Ajouter un attribut id unique, un attribut scope approprié (row/col) ou un rôle role='rowheader'/'columnheader' à cet en-tête."),
                                    )
                                )

        if total_headers_entire == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun en-tête de ligne ou de colonne s'appliquant à la totalité de la ligne ou de la colonne détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_headers_entire} en-tête(s) de ligne/colonne s'appliquant à la totalité de la ligne/colonne, {len(header_findings)} non conforme(s)."),
            findings=header_findings,
            tested_elements=total_headers_entire,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "headers_entire_checked": total_headers_entire,
            },
        )

    def _has_header_cells(self, table: Tag) -> bool:
        """Check if table has any header cells."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if is_header_cell(cell):
                    return True
        return False

    def _applies_to_entire_column(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire column.
        Applies to entire column if:
        - columnspan == 1 (doesn't span multiple columns)
        - AND it's positioned to header a column (typically in header area of table)
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if colspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return rowspan == 1 and colspan == 1

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Applies to entire row if:
        - rowspan == 1 (doesn't span multiple rows)
        - AND it's positioned to header a row (typically in first column of table)
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if rowspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        rows = get_table_rows(table)
        if rows:
            first_col_is_header_like = True
            for r_idx, r in enumerate(rows):
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    first_cell = r_cells[0]
                    if not is_header_cell(first_cell):
                        first_col_is_header_like = False
                        break
                else:
                    continue

            if first_col_is_header_like and col_index == 0:
                return True

        if col_index == 0 and len(get_row_cells(rows[0]) if rows else []) > 0:
            first_row_cells = get_row_cells(rows[0]) if rows else []
            if first_row_cells:
                header_count_first_row = sum(1 for c in first_row_cells if is_header_cell(c))
                if header_count_first_row >= len(first_row_cells) * 0.5:  # Majority are headers
                    row_header_like_count = 0
                    total_data_rows = 0
                    for r_idx in range(1, min(len(rows), 4)):  # Check first few data rows
                        r_cells = get_row_cells(rows[r_idx])
                        if len(r_cells) > 0:
                            total_data_rows += 1
                            if is_header_cell(r_cells[0]):
                                row_header_like_count += 1

                    if total_data_rows > 0 and row_header_like_count >= total_data_rows * 0.5:
                        return True

        return rowspan == 1 and colspan == 1

    def _has_proper_header_identification(self, cell: Tag) -> bool:
        """Check if header has proper identification: unique id OR scope OR role='rowheader'/'columnheader'."""
        cell_id = cell.get("id")
        if isinstance(cell_id, str) and cell_id.strip():
            return True

        scope = cell.get("scope")
        if isinstance(scope, str) and scope.strip():
            scope_value = scope.strip().lower()
            if scope_value in ["row", "col", "rowgroup", "colgroup"]:
                return True

        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() in ["rowheader", "columnheader"]:
            return True

        return False

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"


class Test572(RGAATest):
    test_id = "5.7.2"
    criterion_id = "5.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.7.2 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables = []
        for table in tables:
            if self._has_header_cells(table):
                data_tables.append(table)

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        header_findings: list[Finding] = []
        total_headers_with_scope = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    if is_header_cell(cell):
                        if (self._applies_to_entire_column(cell, table, row_index, col_index) or \
                           self._applies_to_entire_row(cell, table, row_index, col_index)) and \
                           self._has_scope_attribute(cell):
                            total_headers_with_scope += 1

                            if not self._has_appropriate_scope_value(cell, table, row_index, col_index):
                                table_id = table.get("id")
                                row_id = row.get("id")
                                cell_id = cell.get("id")

                                if isinstance(cell_id, str) and cell_id.strip():
                                    element = f"#{cell_id}"
                                elif isinstance(row_id, str) and row_id.strip():
                                    element = f"#{row_id} > *[{self._get_cell_index_string(row, col_index)}]"
                                elif isinstance(table_id, str) and table_id.strip():
                                    element = f"#{table_id} > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"
                                else:
                                    element = f"table[index={table_index}] > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"

                                header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'attribut scope de l'en-tête de ligne ou de colonne n'est pas approprié."),
                                        recommendation=("Utiliser scope='row' pour un en-tête de ligne ou scope='col' pour un en-tête de colonne."),
                                    )
                                )

        if total_headers_with_scope == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun en-tête de ligne ou de colonne avec attribut scope détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_headers_with_scope} en-tête(s) de ligne/colonne avec scope, {len(header_findings)} non conforme(s)."),
            findings=header_findings,
            tested_elements=total_headers_with_scope,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "headers_with_scope_checked": total_headers_with_scope,
            },
        )

    def _has_header_cells(self, table: Tag) -> bool:
        """Check if table has any header cells."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if is_header_cell(cell):
                    return True
        return False

    def _applies_to_entire_column(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire column.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if colspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return rowspan == 1 and colspan == 1

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if rowspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        rows = get_table_rows(table)
        if rows:
            first_col_is_header_like = True
            for r_idx, r in enumerate(rows):
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    first_cell = r_cells[0]
                    if not is_header_cell(first_cell):
                        first_col_is_header_like = False
                        break
                else:
                    continue

            if first_col_is_header_like and col_index == 0:
                return True

        if col_index == 0 and len(get_row_cells(rows[0]) if rows else []) > 0:
            first_row_cells = get_row_cells(rows[0]) if rows else []
            if first_row_cells:
                header_count_first_row = sum(1 for c in first_row_cells if is_header_cell(c))
                if header_count_first_row >= len(first_row_cells) * 0.5:  # Majority are headers
                    row_header_like_count = 0
                    total_data_rows = 0
                    for r_idx in range(1, min(len(rows), 4)):  # Check first few data rows
                        r_cells = get_row_cells(rows[r_idx])
                        if len(r_cells) > 0:
                            total_data_rows += 1
                            if is_header_cell(r_cells[0]):
                                row_header_like_count += 1

                    if total_data_rows > 0 and row_header_like_count >= total_data_rows * 0.5:
                        return True

        return rowspan == 1 and colspan == 1

    def _has_scope_attribute(self, cell: Tag) -> bool:
        """Check if cell has a scope attribute."""
        scope = cell.get("scope")
        return isinstance(scope, str) and scope.strip() != ""

    def _has_appropriate_scope_value(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Check if the scope value is appropriate for row/column header."""
        scope = cell.get("scope")
        if not isinstance(scope, str):
            return False

        scope_value = scope.strip().lower()

        is_row_header = self._is_row_header(cell, table, row_index, col_index)
        is_column_header = self._is_column_header(cell, table, row_index, col_index)

        if is_row_header:
            return scope_value == "row"
        elif is_column_header:
            return scope_value == "col"
        else:
            return scope_value in ["row", "col", "rowgroup", "colgroup"]

    def _is_row_header(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Determine if a header cell is a row header."""
        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() == "rowheader":
            return True

        scope = cell.get("scope")
        if isinstance(scope, str) and scope.strip().lower() == "row":
            return True

        rows = get_table_rows(table)
        if rows and col_index == 0:
            first_col_header_count = 0
            total_rows_with_cells = 0
            for r in rows:
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    total_rows_with_cells += 1
                    if is_header_cell(r_cells[0]):
                        first_col_header_count += 1

            if total_rows_with_cells > 0 and first_col_header_count >= total_rows_with_cells * 0.5:
                return True

        return False

    def _is_column_header(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Determine if a header cell is a column header."""
        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() == "columnheader":
            return True

        scope = cell.get("scope")
        if isinstance(scope, str) and scope.strip().lower() == "col":
            return True

        rows = get_table_rows(table)
        if rows and row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return False

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"


class Test573(RGAATest):
    test_id = "5.7.3"
    criterion_id = "5.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.7.3 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables = []
        for table in tables:
            if self._has_header_cells(table):
                data_tables.append(table)

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        header_findings: list[Finding] = []
        total_headers_not_entire = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    if is_header_cell(cell):
                        if not (self._applies_to_entire_column(cell, table, row_index, col_index) or \
                               self._applies_to_entire_row(cell, table, row_index, col_index)):
                            total_headers_not_entire += 1

                            if not self._meets_criteria_573(cell):
                                table_id = table.get("id")
                                row_id = row.get("id")
                                cell_id = cell.get("id")

                                if isinstance(cell_id, str) and cell_id.strip():
                                    element = f"#{cell_id}"
                                elif isinstance(row_id, str) and row_id.strip():
                                    element = f"#{row_id} > *[{self._get_cell_index_string(row, col_index)}]"
                                elif isinstance(table_id, str) and table_id.strip():
                                    element = f"#{table_id} > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"
                                else:
                                    element = f"table[index={table_index}] > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"

                                header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'en-tête qui ne s'applique pas à la totalité de la ligne ou de la colonne doit avoir un id unique et ne pas avoir d'attribut scope ni de rôle role='rowheader'/'columnheader'."),
                                        recommendation=("Ajouter un attribut id unique et supprimer les attributs scope et rôle role='rowheader'/'columnheader' inappropriés."),
                                    )
                                )

        if total_headers_not_entire == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun en-tête ne s'appliquant pas à la totalité de la ligne ou de la colonne détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_headers_not_entire} en-tête(s) ne s'appliquant pas à la totalité de la ligne/colonne, {len(header_findings)} non conforme(s)."),
            findings=header_findings,
            tested_elements=total_headers_not_entire,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "headers_not_entire_checked": total_headers_not_entire,
            },
        )

    def _has_header_cells(self, table: Tag) -> bool:
        """Check if table has any header cells."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if is_header_cell(cell):
                    return True
        return False

    def _applies_to_entire_column(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire column.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if colspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return rowspan == 1 and colspan == 1

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if rowspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        rows = get_table_rows(table)
        if rows:
            first_col_is_header_like = True
            for r_idx, r in enumerate(rows):
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    first_cell = r_cells[0]
                    if not is_header_cell(first_cell):
                        first_col_is_header_like = False
                        break
                else:
                    continue

            if first_col_is_header_like and col_index == 0:
                return True

        if col_index == 0 and len(get_row_cells(rows[0]) if rows else []) > 0:
            first_row_cells = get_row_cells(rows[0]) if rows else []
            if first_row_cells:
                header_count_first_row = sum(1 for c in first_row_cells if is_header_cell(c))
                if header_count_first_row >= len(first_row_cells) * 0.5:  # Majority are headers
                    row_header_like_count = 0
                    total_data_rows = 0
                    for r_idx in range(1, min(len(rows), 4)):  # Check first few data rows
                        r_cells = get_row_cells(rows[r_idx])
                        if len(r_cells) > 0:
                            total_data_rows += 1
                            if is_header_cell(r_cells[0]):
                                row_header_like_count += 1

                    if total_data_rows > 0 and row_header_like_count >= total_data_rows * 0.5:
                        return True

        return rowspan == 1 and colspan == 1

    def _meets_criteria_573(self, cell: Tag) -> bool:
        """Check if header meets criteria 5.7.3: unique id AND no scope AND no role='rowheader'/'columnheader'."""
        cell_id = cell.get("id")
        has_unique_id = isinstance(cell_id, str) and cell_id.strip() != ""

        scope = cell.get("scope")
        has_no_scope = not (isinstance(scope, str) and scope.strip() != "")

        role = cell.get("role")
        has_no_inappropriate_role = not (
            isinstance(role, str) and
            role.strip().lower() in ["rowheader", "columnheader"]
        )

        return has_unique_id and has_no_scope and has_no_inappropriate_role

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"


class Test574(RGAATest):
    test_id = "5.7.4"
    criterion_id = "5.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.7.4 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables = []
        for table in tables:
            if self._has_header_cells(table):
                data_tables.append(table)

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        cell_findings: list[Finding] = []
        total_associated_cells = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    if self._is_data_or_header_cell(cell):
                        if self._is_associated_with_headers_having_id(cell, soup):
                            total_associated_cells += 1

                            if not self._has_proper_headers_attribute(cell, soup):
                                table_id = table.get("id")
                                row_id = row.get("id")
                                cell_id = cell.get("id")

                                if isinstance(cell_id, str) and cell_id.strip():
                                    element = f"#{cell_id}"
                                elif isinstance(row_id, str) and row_id.strip():
                                    element = f"#{row_id} > *[{self._get_cell_index_string(row, col_index)}]"
                                elif isinstance(table_id, str) and table_id.strip():
                                    element = f"#{table_id} > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"
                                else:
                                    element = f"table[index={table_index}] > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"

                                cell_findings.append(
                                    Finding(
                                        element=element,
                                        message=("La cellule associée à un ou plusieurs en-têtes possédant un id doit avoir un attribut headers contenant la liste des ids des en-têtes associés."),
                                        recommendation=("Ajouter un attribut headers contenant la liste des ids des en-têtes associés à cette cellule."),
                                    )
                                )

        if total_associated_cells == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune cellule associée à un ou plusieurs en-têtes possédant un id détectée.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if cell_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_associated_cells} cellule(s) associée(s) à un(en) en-tête(s) possédant un id, {len(cell_findings)} non conforme(s)."),
            findings=cell_findings,
            tested_elements=total_associated_cells,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "associated_cells_checked": total_associated_cells,
            },
        )

    def _has_header_cells(self, table: Tag) -> bool:
        """Check if table has any header cells."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if is_header_cell(cell):
                    return True
        return False

    def _is_data_or_header_cell(self, cell: Tag) -> bool:
        """Check if cell is a data cell (td or th) or header cell."""
        return cell.name in ["td", "th"]

    def _is_associated_with_headers_having_id(self, cell: Tag, soup: BeautifulSoup) -> bool:
        """Check if cell is associated with one or more headers that have id attributes."""
        headers_attr = cell.get("headers")
        if not headers_attr:
            return self._is_implicitly_associated_with_headers_having_id(cell, soup)

        if isinstance(headers_attr, str):
            header_ids = headers_attr.split()
        elif isinstance(headers_attr, list):
            header_ids = headers_attr
        else:
            return False

        for header_id in header_ids:
            header_elem = soup.find(id=header_id)
            if header_elem and isinstance(header_elem.get("id"), str) and header_elem.get("id").strip():
                return True

        return False

    def _is_implicitly_associated_with_headers_having_id(self, cell: Tag, soup: BeautifulSoup) -> bool:
        """Check if cell is implicitly associated with headers that have id attributes."""
        table = cell.find_parent("table")
        if not table:
            return False

        rows = get_table_rows(table)
        cell_row_index = -1
        cell_col_index = -1

        for row_idx, row in enumerate(rows):
            cells = get_row_cells(row)
            for col_idx, cell_in_row in enumerate(cells):
                if cell_in_row is cell:
                    cell_row_index = row_idx
                    cell_col_index = col_idx
                    break
            if cell_row_index != -1:
                break

        if cell_row_index == -1 or cell_col_index == -1:
            return False

        for row_idx in range(cell_row_index):
            row = rows[row_idx]
            cells = get_row_cells(row)
            if cell_col_index < len(cells):
                header_cell = cells[cell_col_index]
                if is_header_cell(header_cell):
                    header_id = header_cell.get("id")
                    if isinstance(header_id, str) and header_id.strip():
                        return True

        row = rows[cell_row_index]
        cells = get_row_cells(row)
        for col_idx in range(cell_col_index):
            header_cell = cells[col_idx]
            if is_header_cell(header_cell):
                header_id = header_cell.get("id")
                if isinstance(header_id, str) and header_id.strip():
                    return True

        return False

    def _has_proper_headers_attribute(self, cell: Tag, soup: BeautifulSoup) -> bool:
        """Check if cell has headers attribute containing the list of associated header ids."""
        headers_attr = cell.get("headers")
        if not headers_attr:
            return False

        associated_header_ids = self._get_associated_header_ids(cell, soup)
        if not associated_header_ids:
            return False

        if isinstance(headers_attr, str):
            header_ids = headers_attr.split()
        elif isinstance(headers_attr, list):
            header_ids = headers_attr
        else:
            return False

        return set(header_ids) == set(associated_header_ids)

    def _get_associated_header_ids(self, cell: Tag, soup: BeautifulSoup) -> list[str]:
        """Get the ids of headers associated with this cell."""
        associated_ids = []

        table = cell.find_parent("table")
        if not table:
            return associated_ids

        rows = get_table_rows(table)
        cell_row_index = -1
        cell_col_index = -1

        for row_idx, row in enumerate(rows):
            cells = get_row_cells(row)
            for col_idx, cell_in_row in enumerate(cells):
                if cell_in_row is cell:
                    cell_row_index = row_idx
                    cell_col_index = col_idx
                    break
            if cell_row_index != -1:
                break

        if cell_row_index == -1 or cell_col_index == -1:
            return associated_ids

        for row_idx in range(cell_row_index):
            row = rows[row_idx]
            cells = get_row_cells(row)
            if cell_col_index < len(cells):
                header_cell = cells[cell_col_index]
                if is_header_cell(header_cell):
                    header_id = header_cell.get("id")
                    if isinstance(header_id, str) and header_id.strip():
                        associated_ids.append(header_id)

        row = rows[cell_row_index]
        cells = get_row_cells(row)
        for col_idx in range(cell_col_index):
            header_cell = cells[col_idx]
            if is_header_cell(header_cell):
                header_id = header_cell.get("id")
                if isinstance(header_id, str) and header_id.strip():
                    associated_ids.append(header_id)

        return associated_ids

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"


class Test575(RGAATest):
    test_id = "5.7.5"
    criterion_id = "5.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 5.7.5 nécessite un DOM.")

        soup = context.dom

        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        data_tables = []
        for table in tables:
            if self._has_header_cells(table):
                data_tables.append(table)

        if not data_tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau de données détecté.",
                metadata={
                    "total_tables": len(tables),
                },
            )

        header_findings: list[Finding] = []
        total_role_headers_entire = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    role = cell.get("role")
                    if isinstance(role, str) and role.strip().lower() in ["rowheader", "columnheader"]:
                        if self._applies_to_entire_column(cell, table, row_index, col_index) or \
                           self._applies_to_entire_row(cell, table, row_index, col_index):
                            total_role_headers_entire += 1

                            if not self._has_correct_role_value(cell, table, row_index, col_index):
                                table_id = table.get("id")
                                row_id = row.get("id")
                                cell_id = cell.get("id")

                                if isinstance(cell_id, str) and cell_id.strip():
                                    element = f"#{cell_id}"
                                elif isinstance(row_id, str) and row_id.strip():
                                    element = f"#{row_id} > *[{self._get_cell_index_string(row, col_index)}]"
                                elif isinstance(table_id, str) and table_id.strip():
                                    element = f"#{table_id} > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"
                                else:
                                    element = f"table[index={table_index}] > *:nth-child({row_index + 1}) > *:nth-child({col_index + 1})"

                                header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'élément avec role='rowheader' ou role='columnheader' doit avoir la valeur appropriée selon qu'il s'applique à une ligne ou une colonne."),
                                        recommendation=("Utiliser role='rowheader' pour un en-tête de ligne ou role='columnheader' pour un en-tête de colonne."),
                                    )
                                )

        if total_role_headers_entire == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun élément avec role='rowheader' ou role='columnheader' s'appliquant à la totalité de la ligne ou de la colonne détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_role_headers_entire} élément(s) avec role='rowheader'/'columnheader' s'appliquant à la totalité de la ligne/colonne, {len(header_findings)} non conforme(s)."),
            findings=header_findings,
            tested_elements=total_role_headers_entire,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "role_headers_entire_checked": total_role_headers_entire,
            },
        )

    def _has_header_cells(self, table: Tag) -> bool:
        """Check if table has any header cells."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                if is_header_cell(cell):
                    return True
        return False

    def _applies_to_entire_column(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire column.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if colspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return rowspan == 1 and colspan == 1

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Same logic as in Test571.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        if rowspan > 1:
            return False

        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        rows = get_table_rows(table)
        if rows:
            first_col_is_header_like = True
            for r_idx, r in enumerate(rows):
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    first_cell = r_cells[0]
                    if not is_header_cell(first_cell):
                        first_col_is_header_like = False
                        break
                else:
                    continue

            if first_col_is_header_like and col_index == 0:
                return True

        if col_index == 0 and len(get_row_cells(rows[0]) if rows else []) > 0:
            first_row_cells = get_row_cells(rows[0]) if rows else []
            if first_row_cells:
                header_count_first_row = sum(1 for c in first_row_cells if is_header_cell(c))
                if header_count_first_row >= len(first_row_cells) * 0.5:  # Majority are headers
                    row_header_like_count = 0
                    total_data_rows = 0
                    for r_idx in range(1, min(len(rows), 4)):  # Check first few data rows
                        r_cells = get_row_cells(rows[r_idx])
                        if len(r_cells) > 0:
                            total_data_rows += 1
                            if is_header_cell(r_cells[0]):
                                row_header_like_count += 1

                    if total_data_rows > 0 and row_header_like_count >= total_data_rows * 0.5:
                        return True

        return rowspan == 1 and colspan == 1

    def _has_correct_role_value(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Check if the role value is appropriate for row/column header."""
        role = cell.get("role")
        if not isinstance(role, str):
            return False

        role_value = role.strip().lower()

        is_row_header = self._is_row_header(cell, table, row_index, col_index)
        is_column_header = self._is_column_header(cell, table, row_index, col_index)

        if is_row_header:
            return role_value == "rowheader"
        elif is_column_header:
            return role_value == "columnheader"
        else:
            return False

    def _is_row_header(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Determine if a header cell is a row header."""
        scope = cell.get("scope")
        if isinstance(scope, str) and scope.strip().lower() == "row":
            return True

        rows = get_table_rows(table)
        if rows and col_index == 0:
            first_col_header_count = 0
            total_rows_with_cells = 0
            for r in rows:
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    total_rows_with_cells += 1
                    if is_header_cell(r_cells[0]):
                        first_col_header_count += 1

            if total_rows_with_cells > 0 and first_col_header_count >= total_rows_with_cells * 0.5:
                return True

        return False

    def _is_column_header(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """Determine if a header cell is a column header."""
        scope = cell.get("scope")
        if isinstance(scope, str) and scope.strip().lower() == "col":
            return True

        rows = get_table_rows(table)
        if rows and row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        return False

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"

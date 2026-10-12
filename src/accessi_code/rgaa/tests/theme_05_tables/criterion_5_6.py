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


class Test561(RGAATest):
    test_id = "5.6.1"
    criterion_id = "5.6"

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
            raise ValueError("Le test 5.6.1 nécessite un DOM.")

        soup = context.dom

        # Find all tables (including role="table")
        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        # Only consider data tables (those with header cells)
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

        column_header_findings: list[Finding] = []
        total_column_headers = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            # Process each row to find column headers
            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    # Check if this is a header cell
                    if is_header_cell(cell):
                        # Check if this header applies to an entire column
                        if self._applies_to_entire_column(cell, table, row_index, col_index):
                            total_column_headers += 1

                            # Check if it's properly structured (th or role="columnheader")
                            if not self._is_properly_structured_column_header(cell):
                                # Generate element identifier
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

                                column_header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'en-tête de colonne n'est pas correctement déclaré."),
                                        recommendation=("Utiliser un élément <th> ou un élément avec l'attribut role='columnheader' pour déclarer cet en-tête de colonne."),
                                    )
                                )

        if total_column_headers == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun en-tête de colonne s'appliquant à la totalité de la colonne détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if column_header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_column_headers} en-tête(s) de colonne s'appliquant à la totalité de la colonne, {len(column_header_findings)} non conforme(s)."),
            findings=column_header_findings,
            tested_elements=total_column_headers,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "column_headers_checked": total_column_headers,
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

        # Must not span multiple columns
        if colspan > 1:
            return False

        # Additional heuristics to determine if it's a column header:
        # 1. If it has explicit column header role or scope
        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        # 2. If it's in thead or first few rows (typical column header location)
        # Check if ancestor is thead
        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        # 3. If it's in first row and table has thead/tbody structure, likely column header
        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            # Check if second row exists and has td/th cells (suggests data rows)
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                # If first row has header-like cells and second row has data-like cells,
                # first row likely contains column headers
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        # 4. Default: if it's a header cell with colspan=1 and rowspan=1, assume it applies to entire column
        # This is a simplification - in practice, we'd need more sophisticated table structure analysis
        return rowspan == 1 and colspan == 1

    def _is_properly_structured_column_header(self, cell: Tag) -> bool:
        """Check if column header is properly structured (th or role='columnheader')."""
        # Check if it's a th element
        if cell.name == "th":
            return True

        # Check if it has role="columnheader"
        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() == "columnheader":
            return True

        return False


class Test562(RGAATest):
    test_id = "5.6.2"
    criterion_id = "5.6"

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
            raise ValueError("Le test 5.6.2 nécessite un DOM.")

        soup = context.dom

        # Find all tables (including role="table")
        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        # Only consider data tables (those with header cells)
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

        row_header_findings: list[Finding] = []
        total_row_headers = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            # Process each row to find row headers
            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    # Check if this is a header cell
                    if is_header_cell(cell):
                        # Check if this header applies to an entire row
                        if self._applies_to_entire_row(cell, table, row_index, col_index):
                            total_row_headers += 1

                            # Check if it's properly structured (th or role="rowheader")
                            if not self._is_properly_structured_row_header(cell):
                                # Generate element identifier
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

                                row_header_findings.append(
                                    Finding(
                                        element=element,
                                        message=("L'en-tête de ligne n'est pas correctement déclaré."),
                                        recommendation=("Utiliser un élément <th> ou un élément avec l'attribut role='rowheader' pour déclarer cet en-tête de ligne."),
                                    )
                                )

        if total_row_headers == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun en-tête de ligne s'appliquant à la totalité de la ligne détecté.",
                metadata={
                    "total_tables": len(tables),
                    "data_tables": len(data_tables),
                },
            )

        status = TestStatus.FAIL if row_header_findings else TestStatus.PASS

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            (f"{total_row_headers} en-tête(s) de ligne s'appliquant à la totalité de la ligne, {len(row_header_findings)} non conforme(s)."),
            findings=row_header_findings,
            tested_elements=total_row_headers,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "row_headers_checked": total_row_headers,
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

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Applies to entire row if:
        - rowspan == 1 (doesn't span multiple rows)
        - AND it's positioned to header a row (typically in first column of table)
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        # Must not span multiple rows
        if rowspan > 1:
            return False

        # Additional heuristics to determine if it's a row header:
        # 1. If it has explicit row header role or scope
        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        # 2. If it's in first column (typical row header location)
        # Check if it's likely in first column by position and table structure
        rows = get_table_rows(table)
        if rows:
            first_col_is_header_like = True
            # Check if first column in this row and similar rows tend to be headers
            for r_idx, r in enumerate(rows):
                r_cells = get_row_cells(r)
                if len(r_cells) > 0:
                    first_cell = r_cells[0]
                    if not is_header_cell(first_cell):
                        first_col_is_header_like = False
                        break
                else:
                    # Empty row, skip
                    continue

            if first_col_is_header_like and col_index == 0:
                return True

        # 3. If it's in first column and table structure suggests row headers
        if col_index == 0 and len(get_row_cells(rows[0]) if rows else []) > 0:
            # Check if first row looks like it contains column headers (not row headers)
            first_row_cells = get_row_cells(rows[0]) if rows else []
            if first_row_cells:
                header_count_first_row = sum(1 for c in first_row_cells if is_header_cell(c))
                # If first row has many headers, it's likely column headers, so first column might be row headers
                if header_count_first_row >= len(first_row_cells) * 0.5:  # Majority are headers
                    # Check if subsequent rows have header-like first cell
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

        # 4. Default: if it's a header cell with rowspan=1 and colspan=1, assume it applies to entire row
        # This is a simplification - in practice, we'd need more sophisticated table structure analysis
        return rowspan == 1 and colspan == 1

    def _is_properly_structured_row_header(self, cell: Tag) -> bool:
        """Check if row header is properly structured (th or role='rowheader')."""
        # Check if it's a th element
        if cell.name == "th":
            return True

        # Check if it has role="rowheader"
        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() == "rowheader":
            return True

        return False


class Test563(RGAATest):
    test_id = "5.6.3"
    criterion_id = "5.6"

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
            raise ValueError("Le test 5.6.3 nécessite un DOM.")

        soup = context.dom

        # Find all tables (including role="table")
        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        # Only consider data tables (those with header cells)
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
        total_special_headers = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            # Process each row to find headers
            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    # Check if this is a header cell
                    if is_header_cell(cell):
                        # Check if this header does NOT apply to entire row or column
                        if not self._applies_to_entire_column(cell, table, row_index, col_index) or \
                           not self._applies_to_entire_row(cell, table, row_index, col_index):
                            total_special_headers += 1

                            # Check if it's properly structured (must be th)
                            if not self._is_th_element(cell):
                                # Generate element identifier
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
                                        message=("L'en-tête ne s'appliquant pas à la totalité de la ligne ou de la colonne doit être un élément <th>."),
                                        recommendation=("Utiliser un élément <th> pour déclarer cet en-tête."),
                                    )
                                )

        if total_special_headers == 0:
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
            (f"{total_special_headers} en-tête(s) ne s'appliquant pas à la totalité de la ligne ou de la colonne, {len(header_findings)} non conforme(s)."),
            findings=header_findings,
            tested_elements=total_special_headers,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "special_headers_checked": total_special_headers,
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
        Same logic as in Test561.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        # Must not span multiple columns
        if colspan > 1:
            return False

        # Additional heuristics to determine if it's a column header:
        role = cell.get("role")
        scope = cell.get("scope")

        if role == "columnheader" or scope == "col":
            return True

        # Check if ancestor is thead
        parent = cell.parent
        while parent and parent != table:
            if parent.name == "thead":
                return True
            parent = parent.parent

        # If it's in first row and table has thead/tbody structure, likely column header
        rows = get_table_rows(table)
        if row_index == 0 and len(rows) > 1:
            second_row_cells = get_row_cells(rows[1])
            if second_row_cells:
                first_row_cells = get_row_cells(rows[0])
                header_count = sum(1 for c in first_row_cells if is_header_cell(c))
                data_count = sum(1 for c in second_row_cells if c.name == "td" or c.get("role") == "cell")
                if header_count > 0 and data_count > 0:
                    return True

        # Default: if it's a header cell with colspan=1 and rowspan=1, assume it applies to entire column
        return rowspan == 1 and colspan == 1

    def _applies_to_entire_row(self, cell: Tag, table: Tag, row_index: int, col_index: int) -> bool:
        """
        Check if a header cell applies to an entire row.
        Same logic as in Test562.
        """
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")

        # Must not span multiple rows
        if rowspan > 1:
            return False

        # Additional heuristics to determine if it's a row header:
        role = cell.get("role")
        scope = cell.get("scope")

        if role == "rowheader" or scope == "row":
            return True

        # Check if it's in first column and table structure suggests row headers
        if col_index == 0:
            rows = get_table_rows(table)
            if rows:
                # Check if first column tends to contain headers
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

        # Default: if it's a header cell with rowspan=1 and colspan=1, assume it applies to entire row
        return rowspan == 1 and colspan == 1

    def _is_th_element(self, cell: Tag) -> bool:
        """Check if cell is a th element."""
        return cell.name == "th"


class Test564(RGAATest):
    test_id = "5.6.4"
    criterion_id = "5.6"

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
            raise ValueError("Le test 5.6.4 nécessite un DOM.")

        soup = context.dom

        # Find all tables (including role="table")
        tables = soup.select("table, [role='table']")

        if not tables:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun tableau détecté.",
            )

        # Only consider data tables (those with header cells)
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
        total_multi_header_cells = 0

        for table_index, table in enumerate(data_tables):
            rows = get_table_rows(table)

            # Process each row to find cells
            for row_index, row in enumerate(rows):
                cells = get_row_cells(row)

                for col_index, cell in enumerate(cells):
                    # Check if this is a data cell (td or role="cell")
                    if self._is_data_cell(cell):
                        # Check if this cell is associated with multiple headers
                        if self._is_associated_with_multiple_headers(cell, table, soup):
                            total_multi_header_cells += 1

                            # Check if it's properly structured (td or th)
                            if not self._is_td_or_th_element(cell):
                                # Generate element identifier
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
                                        message=("La cellule associée à plusieurs en-têtes doit être structurée au moyen d'un élément <td> ou <th>."),
                                        recommendation=("Utiliser un élément <td> ou <th> pour structurer cette cellule."),
                                    )
                                )

        if total_multi_header_cells == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune cellule associée à plusieurs en-têtes détectée.",
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
            (f"{total_multi_header_cells} cellule(s) associée(s) à plusieurs en-têtes, {len(cell_findings)} non conforme(s)."),
            findings=cell_findings,
            tested_elements=total_multi_header_cells,
            metadata={
                "total_tables": len(tables),
                "data_tables": len(data_tables),
                "multi_header_cells_checked": total_multi_header_cells,
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

    def _is_data_cell(self, cell: Tag) -> bool:
        """Check if cell is a data cell (td or role='cell')."""
        if cell.name == "td":
            return True
        role = cell.get("role")
        if isinstance(role, str) and role.strip().lower() == "cell":
            return True
        return False

    def _is_associated_with_multiple_headers(self, cell: Tag, table: Tag, soup: BeautifulSoup) -> bool:
        """
        Check if a cell is associated with multiple headers.
        A cell is associated with multiple headers if:
        1. It has a headers attribute referencing multiple header elements, OR
        2. It spans multiple columns or rows (colspan > 1 or rowspan > 1), OR
        3. The table has colgroup/rowgroup scopes (indicating potential complex header association)
        """
        # Check 1: Explicit headers attribute with multiple references
        headers_attr = cell.get("headers")
        if isinstance(headers_attr, str):
            header_ids = headers_attr.split()
            if len(header_ids) > 1:
                # Verify that at least two of the referenced elements exist and are headers
                valid_header_count = 0
                for header_id in header_ids:
                    header_elem = soup.find(id=header_id)
                    if header_elem and is_header_cell(header_elem):
                        valid_header_count += 1
                if valid_header_count >= 2:
                    return True
        elif isinstance(headers_attr, list):
            if len(headers_attr) > 1:
                # Verify that at least two of the referenced elements exist and are headers
                valid_header_count = 0
                for header_elem in headers_attr:
                    if isinstance(header_elem, Tag) and is_header_cell(header_elem):
                        valid_header_count += 1
                if valid_header_count >= 2:
                    return True

        # Check 2: Cell spans multiple columns or rows (indicates complex association with multiple headers)
        colspan = get_int_attribute(cell, "colspan")
        rowspan = get_int_attribute(cell, "rowspan")
        if colspan > 1 or rowspan > 1:
            return True

        # Check 3: Table has colgroup/rowgroup scopes (may indicate complex header association)
        if self._table_has_colrowgroup_scopes(table):
            # In tables with colgroup/rowgroup scopes, data cells may be associated with multiple headers
            # Check if table is sufficiently complex to warrant this assumption
            rows = get_table_rows(table)
            if len(rows) > 1:
                first_row_cells = get_row_cells(rows[0])
                if len(first_row_cells) > 1:
                    return True

        return False

    def _table_has_colrowgroup_scopes(self, table: Tag) -> bool:
        """Check if table has any header element with scope='colgroup' or scope='rowgroup'."""
        rows = get_table_rows(table)
        for row in rows:
            cells = get_row_cells(row)
            for cell in cells:
                # Check if this is a header cell
                if is_header_cell(cell):
                    scope = cell.get("scope")
                    if isinstance(scope, str) and scope.strip().lower() in ["colgroup", "rowgroup"]:
                        return True
        return False

    def _is_td_or_th_element(self, cell: Tag) -> bool:
        """Check if cell is a td or th element."""
        return cell.name in ["td", "th"]

    def _get_cell_index_string(self, row: Tag, col_index: int) -> str:
        """Get a string representation of cell's position within its row for error reporting."""
        cells = get_row_cells(row)
        if col_index < len(cells):
            return f"[index={col_index}]"
        return f"[index={col_index}]"
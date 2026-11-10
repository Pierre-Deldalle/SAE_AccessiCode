"""
Critère 5.6 : pour chaque tableau de données, chaque en-tête de colonne
et chaque en-tête de ligne sont-ils correctement déclarés ?

Le rôle d'une cellule (en-tête de colonne, en-tête de ligne ou donnée) est
déduit de sa position dans le tableau, et non de la balise utilisée : c'est
justement la balise que ces tests vérifient. Les éléments placés directement
dans une ligne sans être des cellules (<span>, <div>…) sont aussi examinés,
car ils correspondent à des cellules mal structurées.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.tables import (
    COLUMN_HEADER,
    ROW_HEADER,
    TableSlot,
    cell_role,
    classify_table_cells,
    find_tables,
    get_int_attribute,
    is_header_like,
    is_presentation_table,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


def _collect_slots(context: AuditContext, test_id: str) -> tuple[list[Tag], list[TableSlot]] | None:
    if not isinstance(context.dom, BeautifulSoup):
        raise ValueError(f"Le test {test_id} nécessite un DOM.")

    tables = find_tables(context.dom)
    if not tables:
        return None

    slots: list[TableSlot] = []
    for table_index, table in enumerate(tables):
        if not is_presentation_table(table):
            slots.extend(classify_table_cells(table, table_index))

    return tables, slots


def _build_result(
    test: RGAATest,
    tables: list[Tag],
    tested: list[TableSlot],
    failing: list[TableSlot],
    *,
    message: str,
    recommendation: str,
    empty_summary: str,
    summary_label: str,
) -> TestResult:
    if not tested:
        return TestResult(
            test.test_id,
            test.criterion_id,
            TestStatus.NOT_APPLICABLE,
            empty_summary,
            metadata={"total_tables": len(tables)},
        )

    findings = [
        Finding(
            element=slot.selector,
            message=message,
            recommendation=recommendation,
            evidence={"tag": slot.item.name, "role": cell_role(slot.item) or None},
        )
        for slot in failing
    ]

    return TestResult(
        test.test_id,
        test.criterion_id,
        TestStatus.FAIL if findings else TestStatus.PASS,
        f"{len(tested)} {summary_label}, {len(findings)} non conforme(s).",
        findings=findings,
        tested_elements=len(tested),
        metadata={
            "total_tables": len(tables),
            "checked": len(tested),
        },
    )


class Test561(RGAATest):
    """
    Test 5.6.1 : chaque en-tête de colonne s'appliquant à la totalité de la
    colonne est-il structuré avec <th> ou role="columnheader" ?
    """

    test_id = "5.6.1"
    criterion_id = "5.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None) -> TestResult:
        collected = _collect_slots(context, self.test_id)
        if collected is None:
            return TestResult(self.test_id, self.criterion_id, TestStatus.NOT_APPLICABLE, "Aucun tableau détecté.")

        tables, slots = collected
        tested = [s for s in slots if s.kind == COLUMN_HEADER and get_int_attribute(s.item, "colspan") == 1]
        failing = [s for s in tested if not (s.item.name == "th" or cell_role(s.item) == "columnheader")]

        return _build_result(
            self,
            tables,
            tested,
            failing,
            message="L'en-tête de colonne n'est pas correctement déclaré.",
            recommendation=(
                "Utiliser un élément <th> ou un élément avec l'attribut role='columnheader' "
                "pour déclarer cet en-tête de colonne."
            ),
            empty_summary="Aucun en-tête de colonne s'appliquant à la totalité de la colonne détecté.",
            summary_label="en-tête(s) de colonne s'appliquant à la totalité de la colonne",
        )


class Test562(RGAATest):
    """
    Test 5.6.2 : chaque en-tête de ligne s'appliquant à la totalité de la
    ligne est-il structuré avec <th> ou role="rowheader" ?
    """

    test_id = "5.6.2"
    criterion_id = "5.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None) -> TestResult:
        collected = _collect_slots(context, self.test_id)
        if collected is None:
            return TestResult(self.test_id, self.criterion_id, TestStatus.NOT_APPLICABLE, "Aucun tableau détecté.")

        tables, slots = collected
        tested = [s for s in slots if s.kind == ROW_HEADER and get_int_attribute(s.item, "rowspan") == 1]
        failing = [s for s in tested if not (s.item.name == "th" or cell_role(s.item) == "rowheader")]

        return _build_result(
            self,
            tables,
            tested,
            failing,
            message="L'en-tête de ligne n'est pas correctement déclaré.",
            recommendation=(
                "Utiliser un élément <th> ou un élément avec l'attribut role='rowheader' "
                "pour déclarer cet en-tête de ligne."
            ),
            empty_summary="Aucun en-tête de ligne s'appliquant à la totalité de la ligne détecté.",
            summary_label="en-tête(s) de ligne s'appliquant à la totalité de la ligne",
        )


class Test563(RGAATest):
    """
    Test 5.6.3 : chaque en-tête ne s'appliquant pas à la totalité de la ligne
    ou de la colonne est-il structuré avec <th> ?

    Sont concernés les en-têtes qui couvrent plusieurs colonnes (colspan)
    ou plusieurs lignes (rowspan).
    """

    test_id = "5.6.3"
    criterion_id = "5.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None) -> TestResult:
        collected = _collect_slots(context, self.test_id)
        if collected is None:
            return TestResult(self.test_id, self.criterion_id, TestStatus.NOT_APPLICABLE, "Aucun tableau détecté.")

        tables, slots = collected
        tested = [
            s
            for s in slots
            if (s.kind == COLUMN_HEADER and get_int_attribute(s.item, "colspan") > 1)
            or (s.kind == ROW_HEADER and get_int_attribute(s.item, "rowspan") > 1)
        ]
        failing = [s for s in tested if s.item.name != "th"]

        return _build_result(
            self,
            tables,
            tested,
            failing,
            message=(
                "L'en-tête ne s'appliquant pas à la totalité de la ligne ou de la colonne doit être un élément <th>."
            ),
            recommendation="Utiliser un élément <th> pour déclarer cet en-tête.",
            empty_summary="Aucun en-tête ne s'appliquant pas à la totalité de la ligne ou de la colonne détecté.",
            summary_label="en-tête(s) ne s'appliquant pas à la totalité de la ligne ou de la colonne",
        )


class Test564(RGAATest):
    """
    Test 5.6.4 : chaque cellule associée à plusieurs en-têtes est-elle
    structurée avec <td> ou <th> ?

    Une cellule est considérée comme associée à plusieurs en-têtes si son
    attribut headers référence au moins deux en-têtes, ou si elle couvre
    plusieurs colonnes ou plusieurs lignes.
    """

    test_id = "5.6.4"
    criterion_id = "5.6"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None) -> TestResult:
        collected = _collect_slots(context, self.test_id)
        if collected is None:
            return TestResult(self.test_id, self.criterion_id, TestStatus.NOT_APPLICABLE, "Aucun tableau détecté.")

        tables, slots = collected
        tested = [s for s in slots if s.kind != COLUMN_HEADER and _is_multi_header_cell(s.item)]
        failing = [s for s in tested if s.item.name not in {"td", "th"}]

        return _build_result(
            self,
            tables,
            tested,
            failing,
            message="La cellule associée à plusieurs en-têtes doit être structurée au moyen d'un élément <td> ou <th>.",
            recommendation="Utiliser un élément <td> ou <th> pour structurer cette cellule.",
            empty_summary="Aucune cellule associée à plusieurs en-têtes détectée.",
            summary_label="cellule(s) associée(s) à plusieurs en-têtes",
        )


def _is_multi_header_cell(item: Tag) -> bool:
    if is_header_like(item):
        return False

    headers = item.get("headers")
    header_ids = headers.split() if isinstance(headers, str) else list(headers or [])
    if len(header_ids) >= 2:
        return True

    return get_int_attribute(item, "colspan") > 1 or get_int_attribute(item, "rowspan") > 1

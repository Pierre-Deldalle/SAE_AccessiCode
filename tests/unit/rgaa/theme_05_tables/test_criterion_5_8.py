from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_8 import (
    Test581 as RGAA581,
)

SIMPLE_LAYOUT_TABLE_WO_ROLE = """
<table>
    <tr>
        <td>Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

SIMPLE_LAYOUT_TABLE_WITH_ROLE = """
<table role="presentation">
    <tr>
        <td>Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_SUMMARY = """
<table summary="Ce tableau est utilisé pour la mise en page">
    <tr>
        <td>Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_EMPTY_SUMMARY = """
<table summary="">
    <tr>
        <td>Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_CAPTION = """
<table>
    <caption>Titre du tableau</caption>
    <tr>
        <td>Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_TH = """
<table>
    <tr>
        <th>Logo</th>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_THEAD = """
<table>
    <thead>
        <tr>
            <td>Logo</td>
            <td>Menu</td>
            <td>Search</td>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td colspan="3">Main Content</td>
        </tr>
    </tbody>
</table>
"""

LAYOUT_TABLE_WITH_TFOOT = """
<table>
    <tbody>
        <tr>
            <td>Logo</td>
            <td>Menu</td>
            <td>Search</td>
        </tr>
        <tr>
            <td colspan="3">Main Content</td>
        </tr>
    </tbody>
    <tfoot>
        <tr>
            <td>Footer</td>
        </tr>
    </tfoot>
</table>
"""

LAYOUT_TABLE_WITH_ROLE_ROWHEADER = """
<table>
    <tr>
        <td role="rowheader">Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_ROLE_COLUMNHEADER = """
<table>
    <tr>
        <td>Logo</td>
        <td role="columnheader">Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_SCOPE_ON_TD = """
<table>
    <tr>
        <td>Logo</td>
        <td scope="row">Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_HEADERS_ON_TD = """
<table>
    <tr>
        <td id="logo">Logo</td>
        <td>Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td headers="logo">Contenu principal</td>
        <td>Info</td>
        <td>Details</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_AXIS_ON_TD = """
<table>
    <tr>
        <td>Logo</td>
        <td axis="x">Menu</td>
        <td>Search</td>
    </tr>
    <tr>
        <td colspan="3">Main Content</td>
    </tr>
</table>
"""

DATA_TABLE_SIMPLE = """
<table>
    <tr>
        <th>Nom</th>
        <th>Prénom</th>
    </tr>
    <tr>
        <td>Dupont</td>
        <td>Jean</td>
    </tr>
</table>
"""

DATA_TABLE_COMPLEX = """
<table>
    <thead>
        <tr>
            <th rowspan="2" scope="col">Produit</th>
            <th colspan="2" scope="colgroup">Semestre</th>
        </tr>
        <tr>
            <th scope="col">S1</th>
            <th scope="col">S2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <th scope="row">Ordinateurs</th>
            <td>150</td>
            <td>200</td>
        </tr>
    </tbody>
</table>
"""


def test_581_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_581_only_data_tables_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(DATA_TABLE_SIMPLE)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_581_simple_layout_table_without_role_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_LAYOUT_TABLE_WO_ROLE)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_581_layout_table_with_role_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_LAYOUT_TABLE_WITH_ROLE)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_581_layout_table_with_non_empty_summary_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_SUMMARY)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "l'attribut summary n'est pas vide" in result.findings[0].message


def test_581_layout_table_with_empty_summary_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_EMPTY_SUMMARY)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_581_layout_table_with_caption_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_CAPTION)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément <caption>" in result.findings[0].message


def test_581_layout_table_with_th_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_TH)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément <th>" in result.findings[0].message


def test_581_layout_table_with_thead_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_THEAD)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément <thead>" in result.findings[0].message


def test_581_layout_table_with_tfoot_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_TFOOT)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément <tfoot>" in result.findings[0].message


def test_581_layout_table_with_role_rowheader_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_ROLE_ROWHEADER)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément avec role='rowheader'" in result.findings[0].message


def test_581_layout_table_with_role_columnheader_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_ROLE_COLUMNHEADER)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "contient un élément avec role='columnheader'" in result.findings[0].message


def test_581_layout_table_with_scope_on_td_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_SCOPE_ON_TD)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "une cellule <td> possède l'attribut scope" in result.findings[0].message


def test_581_layout_table_with_headers_on_td_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_HEADERS_ON_TD)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "une cellule <td> possède l'attribut headers" in result.findings[0].message


def test_581_layout_table_with_axis_on_td_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_AXIS_ON_TD)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "une cellule <td> possède l'attribut axis" in result.findings[0].message


def test_581_mixed_tables_evaluates_correctly(
    context_factory,
    run_rgaa,
):
    html = DATA_TABLE_SIMPLE + SIMPLE_LAYOUT_TABLE_WITH_ROLE + LAYOUT_TABLE_WITH_TH
    context = context_factory(html)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.FAIL  # One layout table fails (has th)
    assert len(result.findings) == 1
    assert result.tested_elements == 2  # Two layout tables total (one data table ignored)


def test_581_all_good_layout_tables_passes(
    context_factory,
    run_rgaa,
):
    html = SIMPLE_LAYOUT_TABLE_WITH_ROLE + """
    <table role="presentation">
        <tr>
            <td>Banner publicité</td>
            <td>Zone de contenu</td>
        </tr>
    </table>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA581(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2

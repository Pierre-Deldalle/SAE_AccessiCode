from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_3 import (
    Test531 as RGAA531,
)

# Test HTML samples for criterion 5.3
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

LAYOUT_TABLE_WITH_INCOMPREHENSIBLE_CONTENT = """
<table role="presentation">
    <tr>
        <td>Cellule 1</td>
        <td>Cellule 2</td>
    </tr>
    <tr>
        <td>Cellule 3</td>
        <td>Cellule 4</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_REPETITIVE_CONTENT = """
<table role="presentation">
    <tr>
        <td>Item</td>
        <td>Item</td>
        <td>Item</td>
    </tr>
    <tr>
        <td>Data</td>
        <td>Data</td>
        <td>Data</td>
    </tr>
</table>
"""

LAYOUT_TABLE_WITH_MEANINGFUL_CONTENT = """
<table role="presentation">
    <tr>
        <td>En-tête du site</td>
        <td>Navigation principale</td>
    </tr>
    <tr>
        <td colspan="2">Contenu principal de la page</td>
    </tr>
    <tr>
        <td>Pied de page - Links utiles</td>
        <td>Pied de page - Contacts</td>
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

EMPTY_TABLE = """
<table></table>
"""


def test_531_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_531_only_data_tables_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(DATA_TABLE_SIMPLE)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_531_layout_table_without_role_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_LAYOUT_TABLE_WO_ROLE)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "l'attribut role='presentation' est manquant" in result.findings[0].message


def test_531_layout_table_with_role_but_incomprehensible_content_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_INCOMPREHENSIBLE_CONTENT)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "le contenu linéarisé n'est pas compréhensible" in result.findings[0].message


def test_531_layout_table_with_role_and_comprehensible_content_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_MEANINGFUL_CONTENT)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_531_layout_table_with_repetitive_content_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_WITH_REPETITIVE_CONTENT)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "le contenu linéarisé n'est pas compréhensible" in result.findings[0].message


def test_531_mixed_tables_evaluates_correctly(
    context_factory,
    run_rgaa,
):
    html = DATA_TABLE_SIMPLE + LAYOUT_TABLE_WITH_MEANINGFUL_CONTENT + SIMPLE_LAYOUT_TABLE_WO_ROLE
    context = context_factory(html)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.FAIL  # One layout table fails (missing role)
    assert len(result.findings) == 1
    assert result.tested_elements == 2  # Two layout tables total


def test_531_all_good_layout_tables_passes(
    context_factory,
    run_rgaa,
):
    html = LAYOUT_TABLE_WITH_MEANINGFUL_CONTENT + """
    <table role="presentation">
        <tr>
            <td>Banner publicité</td>
            <td>Zone de contenu</td>
        </tr>
    </table>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2


def test_531_presentation_table_from_51_test_is_not_applicable_for_53(
    context_factory,
    run_rgaa,
):
    """This is the table from the 5.1 test file that has role='presentation'"""
    context = context_factory('<table role="presentation"><tr><td>Cellule 1</td><td>Cellule 2</td></tr></table>')
    result = run_rgaa(RGAA531(), context)
    assert result.status == Status.FAIL  # Has role but content is not comprehensible
    assert len(result.findings) == 1
    assert "le contenu linéarisé n'est pas compréhensible" in result.findings[0].message
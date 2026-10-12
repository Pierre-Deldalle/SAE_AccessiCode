from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_4 import (
    Test541 as RGAA541,
)

# Test HTML samples for criterion 5.4
SIMPLE_TABLE_NO_TITLE = """
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

SIMPLE_TABLE_WITH_CAPTION = """
<table>
    <caption>Liste des employés</caption>
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

SIMPLE_TABLE_WITH_TITLE_ATTR = """
<table title="Informations sur les utilisateurs">
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

SIMPLE_TABLE_WITH_ARIA_LABEL = """
<table aria-label="Données du personnel">
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

SIMPLE_TABLE_WITH_ARIA_LABELLEDBY = """
<div id="table-title">Informations sur les employés</div>
<table aria-labelledby="table-title">
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

DATA_TABLE_COMPLEX_NO_TITLE = """
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

DATA_TABLE_COMPLEX_WITH_CAPTION = """
<table>
    <caption>Évolution des ventes par produit et par semestre</caption>
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

LAYOUT_TABLE_NO_TITLE_NEEDED = """
<table role="presentation">
    <tr>
        <td>Logo</td>
        <td>Menu</td>
    </tr>
</table>
"""

EMPTY_TABLE = """
<table></table>
"""


def test_541_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_541_layout_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(LAYOUT_TABLE_NO_TITLE_NEEDED)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_541_simple_table_without_title_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE_NO_TITLE)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "Aucun titre associé à ce tableau de données." in result.findings[0].message


def test_541_simple_table_with_caption_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE_WITH_CAPTION)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_541_simple_table_with_title_attr_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE_WITH_TITLE_ATTR)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_541_simple_table_with_aria_label_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE_WITH_ARIA_LABEL)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_541_simple_table_with_aria_labelledby_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE_WITH_ARIA_LABELLEDBY)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_541_complex_table_without_title_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(DATA_TABLE_COMPLEX_NO_TITLE)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "Aucun titre associé à ce tableau de données." in result.findings[0].message


def test_541_complex_table_with_caption_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(DATA_TABLE_COMPLEX_WITH_CAPTION)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_541_mixed_tables_evaluates_correctly(
    context_factory,
    run_rgaa,
):
    html = SIMPLE_TABLE_NO_TITLE + SIMPLE_TABLE_WITH_CAPTION + LAYOUT_TABLE_NO_TITLE_NEEDED
    context = context_factory(html)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.FAIL  # One simple table fails (no title)
    assert len(result.findings) == 1
    assert result.tested_elements == 2  # Two data tables total (simple tables only)


def test_541_all_good_tables_passes(
    context_factory,
    run_rgaa,
):
    html = SIMPLE_TABLE_WITH_CAPTION + """
    <table title="Autre tableau">
        <tr>
            <th>Produit</th>
            <th>Quantité</th>
        </tr>
        <tr>
            <td>Ordinateurs</td>
            <td>150</td>
        </tr>
    </table>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA541(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2
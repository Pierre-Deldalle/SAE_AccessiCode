from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_2 import (
    Test521 as RGAA521,
)

# Test HTML samples for criterion 5.2
# Note: For a table to be considered "complex" for RGAA 5.1/5.2, it needs structural complexity
# such as rowspan/colspan > 1, scope=rowgroup/colgroup, or headers with multiple references

TABLE_WITH_NON_PERTINENT_SUMMARY = """
<table>
    <caption>Tableau</caption>
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

TABLE_WITH_WEAK_SUMMARY = """
<table>
    <caption>Données</caption>
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

TABLE_WITH_GOOD_SUMMARY = """
<table>
    <caption>Évolution des ventes de produits informatiques sur les deux semestres de l'année</caption>
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

TABLE_WITH_ARIA_DESCRIBEDBY_NON_PERTINENT = """
<div id="non-pertinent-summary">Info</div>
<table aria-describedby="non-pertinent-summary">
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

TABLE_WITH_ARIA_DESCRIBEDBY_GOOD = """
<div id="good-summary">Tableau montrant les ventes mensuelles par région et par produit</div>
<table aria-describedby="good-summary">
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

COMPLEX_TABLE_WITH_NON_PERTINENT_SUMMARY = """
<table>
    <caption>Tableau</caption>
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

COMPLEX_TABLE_WITH_GOOD_SUMMARY = """
<table>
    <caption>Évolution des ventes de produits informatiques sur les deux semestres de l'année</caption>
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

SIMPLE_TABLE_NO_SUMMARY_NEEDED = """
<table>
    <tr>
        <th>Nom</th>
        <th>Age</th>
    </tr>
    <tr>
        <td>Dupont</td>
        <td>30</td>
    </tr>
</table>
"""


def test_521_no_complex_tables_not_applicable(
    context_factory,
    run_rgaa,
):
    """Test when there are no complex tables."""
    context = context_factory("<main><p>Aucun tableau ici.</p></main>")
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_521_simple_tables_not_applicable(
    context_factory,
    run_rgaa,
):
    """Test when there are only simple tables (no complex structure)."""
    context = context_factory(SIMPLE_TABLE_NO_SUMMARY_NEEDED)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_521_complex_table_with_non_pertinent_caption_fails(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with a non-pertinent caption fails."""
    context = context_factory(TABLE_WITH_NON_PERTINENT_SUMMARY)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "résumé du tableau de données complexe n'est pas pertinent" in result.findings[0].message


def test_521_complex_table_with_weak_summary_fails(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with a weak summary fails."""
    context = context_factory(TABLE_WITH_WEAK_SUMMARY)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_521_complex_table_with_good_caption_passes(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with a good caption passes."""
    context = context_factory(TABLE_WITH_GOOD_SUMMARY)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.PASS
    assert result.findings == []


def test_521_complex_table_with_non_pertinent_aria_describedby_fails(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with non-pertinent aria-describedby fails."""
    context = context_factory(TABLE_WITH_ARIA_DESCRIBEDBY_NON_PERTINENT)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_521_complex_table_with_good_aria_describedby_passes(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with good aria-describedby passes."""
    context = context_factory(TABLE_WITH_ARIA_DESCRIBEDBY_GOOD)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.PASS
    assert result.findings == []


def test_521_complex_table_with_non_pertinent_summary_fails(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with non-pertinent summary attribute fails (legacy doctype)."""
    doctype = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    html = doctype + COMPLEX_TABLE_WITH_NON_PERTINENT_SUMMARY
    context = context_factory(html, doctype=doctype)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_521_complex_table_with_good_summary_passes(
    context_factory,
    run_rgaa,
):
    """Test that a complex table with good summary attribute passes (legacy doctype)."""
    doctype = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    html = doctype + COMPLEX_TABLE_WITH_GOOD_SUMMARY
    context = context_factory(html, doctype=doctype)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.PASS
    assert result.findings == []


def test_521_mixed_good_and_bad_summaries_fails(
    context_factory,
    run_rgaa,
):
    """Test that when there are multiple complex tables, one bad summary makes the whole test fail."""
    html = TABLE_WITH_GOOD_SUMMARY + TABLE_WITH_NON_PERTINENT_SUMMARY
    context = context_factory(html)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1  # Only the bad one should generate a finding


def test_521_all_good_summaries_passes(
    context_factory,
    run_rgaa,
):
    """Test that when all complex tables have good summaries, the test passes."""
    html = TABLE_WITH_GOOD_SUMMARY + COMPLEX_TABLE_WITH_GOOD_SUMMARY
    context = context_factory(html)
    result = run_rgaa(RGAA521(), context)
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Both complex tables should be tested
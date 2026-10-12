from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_5 import (
    Test551 as RGAA551,
)

SIMPLE_TABLE = """
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


def table_with_caption(*, caption: str = "") -> str:
    return f"""
    <table>
        {caption}
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


def test_551_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_551_simple_table_without_caption_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE)

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_551_table_with_pertinent_caption_passes(
    context_factory,
    run_rgaa,
):
    html = table_with_caption(caption="<caption>Liste des employés avec leur nom et prénom.</caption>")
    context = context_factory(html)

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_551_table_with_non_pertinent_caption_fails(
    context_factory,
    run_rgaa,
):
    # Test with generic caption like "Tableau" or "Données"
    html = table_with_caption(caption="<caption>Tableau</caption>")
    context = context_factory(html)

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "Le titre du tableau de données n'est pas pertinent" in result.findings[0].message


def test_551_table_with_empty_caption_is_not_counted(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_caption(caption="<caption>   </caption>"))

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_551_table_with_very_short_caption_fails(
    context_factory,
    run_rgaa,
):
    html = table_with_caption(caption="<caption>AB</caption>")
    context = context_factory(html)

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1


def test_551_multiple_tables_mixed_results(
    context_factory,
    run_rgaa,
):
    # One table with pertinent caption, one with non-pertinent caption
    html = '''
    <table>
        <caption>Liste des produits avec leur prix et catégorie.</caption>
        <tr>
            <th>Produit</th>
            <th>Prix</th>
            <th>Catégorie</th>
        </tr>
        <tr>
            <td>Ordinateur</td>
            <td>800€</td>
            <td>Electronique</td>
        </tr>
    </table>
    <table>
        <caption>Données</caption>
        <tr>
            <th>Nom</th>
            <th>Valeur</th>
        </tr>
        <tr>
            <td>Test</td>
            <td>100</td>
        </tr>
    </table>
    '''
    context = context_factory(html)

    result = run_rgaa(RGAA551(), context)

    assert result.status == Status.FAIL  # FAIL takes precedence
    assert len(result.findings) == 1
    assert result.tested_elements == 2
    assert "2 tableau(x) avec titre, 1 avec titre non pertinent" in result.summary
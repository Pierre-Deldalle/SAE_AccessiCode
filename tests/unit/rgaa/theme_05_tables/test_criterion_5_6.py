from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_6 import (
    Test561 as RGAA561,
    Test562 as RGAA562,
    Test563 as RGAA563,
    Test564 as RGAA564,
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


def table_with_th_column_headers() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th>Nom</th>
                <th>Prénom</th>
                <th>Âge</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
                <td>25</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_role_columnheader() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th role="columnheader">Nom</th>
                <th role="columnheader">Prénom</th>
                <th role="columnheader">Âge</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
                <td>25</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_improper_column_header() -> str:
    return """
    <table>
        <thead>
            <tr>
                <span>Nom</span>
                <span>Prénom</span>
                <span>Âge</span>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
                <td>25</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_th_row_headers() -> str:
    return """
    <table>
        <tbody>
            <tr>
                <th>Nom</th>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
            <tr>
                <th>Profession</th>
                <td>Ingénieur</td>
                <td>Développeur</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_role_rowheader() -> str:
    return """
    <table>
        <tbody>
            <tr>
                <th role="rowheader">Nom</th>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
            <tr>
                <th role="rowheader">Profession</th>
                <td>Ingénieur</td>
                <td>Développeur</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_improper_row_header() -> str:
    return """
    <table>
        <tbody>
            <tr>
                <span>Nom</span>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
            <tr>
                <span>Profession</span>
                <td>Ingénieur</td>
                <td>Développeur</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_spanning_header() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th colspan="2">En-tête spanning deux colonnes</th>
                <th>Colonne normale</th>
            </tr>
            <tr>
                <th>Sous-colonne 1</th>
                <th>Sous-colonne 2</th>
                <th>Donnée</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Valeur 1</td>
                <td>Valeur 2</td>
                <td>Donnée</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_headers_attribute() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th id="nom">Nom</th>
                <th id="prenom">Prénom</th>
                <th id="age">Âge</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td headers="nom prenom">Dupont Jean</td>
                <td>25</td>
                <td>Masculin</td>
            </tr>
        </tbody>
    </table>
    """


def test_561_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA561(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_561_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA561(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_561_table_with_th_column_headers_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_th_column_headers())

    result = run_rgaa(RGAA561(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3  # Three column headers


def test_561_table_with_role_columnheader_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_role_columnheader())

    result = run_rgaa(RGAA561(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3  # Three column headers


def test_561_table_with_improper_column_header_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_improper_column_header())

    result = run_rgaa(RGAA561(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 3  # Three improper column headers
    assert result.tested_elements == 3
    assert all("L'en-tête de colonne n'est pas correctement déclaré." in f.message for f in result.findings)


def test_562_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA562(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_562_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA562(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_562_table_with_th_row_headers_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_th_row_headers())

    result = run_rgaa(RGAA562(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two row headers


def test_562_table_with_role_rowheader_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_role_rowheader())

    result = run_rgaa(RGAA562(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two row headers


def test_562_table_with_improper_row_header_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_improper_row_header())

    result = run_rgaa(RGAA562(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 2  # Two improper row headers
    assert result.tested_elements == 2
    assert all("L'en-tête de ligne n'est pas correctement déclaré." in f.message for f in result.findings)


def test_563_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA563(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_563_simple_table_no_special_headers_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE)

    result = run_rgaa(RGAA563(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_563_table_with_spanning_header_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_spanning_header())

    result = run_rgaa(RGAA563(), context)


    html = """
    <table>
        <thead>
            <tr>
                <td colspan="2">En-tête spanning deux colonnes</td>
                <th>Colonne normale</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Donnée 1</td>
                <td>Donnée 2</td>
                <td>Donnée 3</td>
            </tr>
        </tbody>
    </table>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA563(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements >= 1
    assert any("L'en-tête ne s'appliquant pas à la totalité de la ligne ou de la colonne doit être un élément <th>." in f.message for f in result.findings)


def test_564_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_564_table_without_multi_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE)

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_564_table_with_td_or_th_multi_header_cells_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_headers_attribute())

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1  # One multi-header cell


def test_564_table_with_improper_multi_header_cell_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th id="nom">Nom</th>
                <th id="prenom">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <span headers="nom prenom">Dupont Jean</span>
                <td>25</td>
            </tr>
        </tbody>
    </table>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements >= 1
    assert any("La cellule associée à plusieurs en-têtes doit être structurée au moyen d'un élément <td> ou <th>." in f.message for f in result.findings)


def test_564_table_with_colspan_rowspan_multi_header_cell_passes(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <tr>
            <th>Colonne 1</th>
            <th>Colonne 2</th>
        </tr>
        <tr>
            <td colspan="2">Donnée spanning deux colonnes</td>
        </tr>
    </table>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1  # One multi-header cell (the td with colspan=2)


def test_564_table_with_colspan_rowspan_improper_multi_header_cell_fails(
    context_factory,
    run_rgaa,
    ):
    html = """
    <table>
        <tr>
            <th>Colonne 1</th>
            <th>Colonne 2</th>
        </tr>
        <tr>
            <span colspan="2">Donnée spanning deux colonnes</span>
        </tr>
    </table>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA564(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements >= 1
    assert any("La cellule associée à plusieurs en-têtes doit être structurée au moyen d'un élément <td> ou <th>." in f.message for f in result.findings)

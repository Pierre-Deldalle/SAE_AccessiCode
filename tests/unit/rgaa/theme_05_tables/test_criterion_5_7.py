from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_7 import (
    Test571 as RGAA571,
    Test572 as RGAA572,
    Test573 as RGAA573,
    Test574 as RGAA574,
    Test575 as RGAA575,
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


def table_with_id_headers() -> str:
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


def table_with_improper_headers_attribute() -> str:
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
                <td headers="nom">Dupont Jean</td>
                <td>25</td>
                <td>Masculin</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_scope_column_headers() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th scope="col">Nom</th>
                <th scope="col">Prénom</th>
                <th scope="col">Âge</th>
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


def table_with_scope_row_headers() -> str:
    return """
    <table>
        <tbody>
            <tr>
                <th scope="row">Nom</th>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
            <tr>
                <th scope="row">Profession</th>
                <td>Ingénieur</td>
                <td>Développeur</td>
            </tr>
        </tbody>
    </table>
    """


def table_with_wrong_scope() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th scope="row">Nom</th>
                <th scope="row">Prénom</th>
                <th scope="row">Âge</th>
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


def table_with_wrong_role() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th role="rowheader">Nom</th>
                <th role="rowheader">Prénom</th>
                <th role="rowheader">Âge</th>
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


def table_with_unique_id_headers_no_scope_no_role() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th id="header1">Nom</th>
                <th id="header2">Prénom</th>
                <th id="header3">Âge</th>
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


def table_with_header_that_is_not_entire_row_or_col() -> str:
    return """
    <table>
        <thead>
            <tr>
                <th id="header1">Nom</th>
                <th id="header2">Prénom</th>
                <th id="header3">Âge</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th id="header4">Spécial</th>
                <td>Donnée</td>
                <td>Info</td>
                <td>Extra</td>
            </tr>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
                <td>25</td>
                <td>Homme</td>
            </tr>
        </tbody>
    </table>
    """


def test_571_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_571_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_571_table_with_id_header_passes(
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
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two headers with id


def test_571_table_with_scope_header_passes(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th scope="col">Nom</th>
                <th scope="col">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two headers with scope


def test_571_table_with_role_header_passes(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th role="columnheader">Nom</th>
                <th role="columnheader">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two headers with role


def test_571_table_with_missing_identification_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th>Nom</th>
                <th>Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA571(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 2  # Two headers missing identification
    assert result.tested_elements == 2
    assert all("L'en-tête de ligne ou de colonne doit avoir un identifiant unique (id), un attribut scope ou un rôle role='rowheader' ou role='columnheader'." in f.message for f in result.findings)


def test_572_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA572(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_572_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA572(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_572_table_with_scope_column_headers_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_scope_column_headers())

    result = run_rgaa(RGAA572(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3  # Three column headers with scope="col"


def test_572_table_with_scope_row_headers_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_scope_row_headers())

    result = run_rgaa(RGAA572(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two row headers with scope="row"


def test_572_table_with_wrong_scope_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_wrong_scope())

    result = run_rgaa(RGAA572(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 3  # Three headers with wrong scope
    assert result.tested_elements == 3
    assert all("L'attribut scope de l'en-tête de ligne ou de colonne n'est pas approprié." in f.message for f in result.findings)


def test_573_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_573_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_573_table_with_unique_id_no_scope_no_role_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_unique_id_headers_no_scope_no_role())

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3  # Three headers with unique id, no scope, no role


def test_573_table_with_header_missing_id_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th>Nom</th>
                <th id="prenom">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1  # At least the header without id should fail
    assert result.tested_elements >= 1
    assert any("L'en-tête qui ne s'applique pas à la totalité de la ligne ou de la colonne doit avoir un id unique et ne pas avoir d'attribut scope ni de rôle role='rowheader'/'columnheader'." in f.message for f in result.findings)


def test_573_table_with_header_with_scope_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th id="nom" scope="col">Nom</th>
                <th id="prenom">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1  # At least the header with scope should fail
    assert result.tested_elements >= 1
    assert any("L'en-tête qui ne s'applique pas à la totalité de la ligne ou de la colonne doit avoir un id unique et ne pas avoir d'attribut scope ni de rôle role='rowheader'/'columnheader'." in f.message for f in result.findings)


def test_573_table_with_header_with_role_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <table>
        <thead>
            <tr>
                <th id="nom" role="columnheader">Nom</th>
                <th id="prenom">Prénom</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dupont</td>
                <td>Jean</td>
            </tr>
        </tbody>
    </table>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA573(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1  # At least the header with role should fail
    assert result.tested_elements >= 1
    assert any("L'en-tête qui ne s'applique pas à la totalité de la ligne ou de la colonne doit avoir un id unique et ne pas avoir d'attribut scope ni de rôle role='rowheader'/'columnheader'." in f.message for f in result.findings)


def test_574_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA574(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_574_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA574(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_574_table_with_proper_headers_attribute_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_id_headers())

    result = run_rgaa(RGAA574(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1  # One cell with proper headers attribute


def test_574_table_with_improper_headers_attribute_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_improper_headers_attribute())

    result = run_rgaa(RGAA574(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements >= 1
    assert any("La cellule associée à un ou plusieurs en-têtes possédant un id doit avoir un attribut headers contenant la liste des ids des en-têtes associés." in f.message for f in result.findings)


def test_575_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA575(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_575_table_without_header_cells_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))

    result = run_rgaa(RGAA575(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_575_table_with_correct_role_columnheader_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_role_columnheader())

    result = run_rgaa(RGAA575(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3  # Three column headers with correct role


def test_575_table_with_correct_role_rowheader_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_role_rowheader())

    result = run_rgaa(RGAA575(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2  # Two row headers with correct role


def test_575_table_with_wrong_role_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(table_with_wrong_role())

    result = run_rgaa(RGAA575(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 3  # Three headers with wrong role
    assert result.tested_elements == 3
    assert all("L'élément avec role='rowheader' ou role='columnheader' doit avoir la valeur appropriée selon qu'il s'applique à une ligne ou une colonne." in f.message for f in result.findings)

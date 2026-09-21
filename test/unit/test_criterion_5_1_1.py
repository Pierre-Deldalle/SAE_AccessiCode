
from accessi_code.models.result import TestStatus
from accessi_code.tests.theme_05_tableaux.criterion_5_1_1 import (
    Criterion511,
)


# Un tableau avec une seule ligne d'en-têtes n'est pas considéré comme complexe.
def test_simple_table_not_applicable():
    html = """
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

    result = Criterion511().run(html)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert result.tested_elements == 1


# Une légende caption fournit le résumé attendu pour un tableau complexe.
def test_complex_table_with_caption():
    html = """
    <table>
        <caption>Informations des utilisateurs par catégorie</caption>
        <tr>
            <th colspan="2">Informations personnelles</th>
        </tr>
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

    result = Criterion511().run(html)

    assert result.status == TestStatus.PASS
    assert len(result.findings) == 0


# Un tableau complexe sans mécanisme de résumé doit échouer.
def test_complex_table_without_summary():
    html = """
    <table>
        <tr>
            <th colspan="2">Informations personnelles</th>
        </tr>
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

    result = Criterion511().run(html)

    assert result.status == TestStatus.FAIL
    assert len(result.findings) == 1


# Une description référencée par aria-describedby est également acceptée.
def test_complex_table_with_aria_describedby():
    html = """
    <p id="table-description">
        Tableau présentant les informations des utilisateurs
        regroupées par catégorie.
    </p>

    <table aria-describedby="table-description">
        <tr>
            <th colspan="2">Informations personnelles</th>
        </tr>
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

    result = Criterion511().run(html)

    assert result.status == TestStatus.PASS
    assert len(result.findings) == 0


# Une page sans tableau ne relève pas du périmètre de ce critère.
def test_no_tables():
    html = """
    <main>
        <h1>Page sans tableau</h1>
    </main>
    """

    result = Criterion511().run(html)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert result.tested_elements == 0
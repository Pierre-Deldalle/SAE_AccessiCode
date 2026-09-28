from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_1 import (
    Test511 as RGAA511,
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


def complex_table(*, extra_attributes: str = "", caption: str = "") -> str:
    return f"""
    <table {extra_attributes}>
        {caption}
        <thead>
            <tr>
                <th rowspan="2" scope="col">Projet</th>
                <th colspan="2" scope="colgroup">Résultats</th>
            </tr>
            <tr>
                <th scope="col">Succès</th>
                <th scope="col">Erreurs</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th scope="row">Projet A</th>
                <td>20</td>
                <td>2</td>
            </tr>
        </tbody>
    </table>
    """


def test_511_no_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Pas de tableau.</p></main>")

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_511_simple_table_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(SIMPLE_TABLE)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_511_complex_table_with_caption_passes(
    context_factory,
    run_rgaa,
):
    html = complex_table(caption=("<caption>Résultats par projet et par catégorie.</caption>"))
    context = context_factory(html)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_511_complex_table_without_summary_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(complex_table())

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_511_empty_caption_does_not_count_as_summary(
    context_factory,
    run_rgaa,
):
    context = context_factory(complex_table(caption="<caption>   </caption>"))

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.FAIL


def test_511_complex_table_with_valid_aria_describedby_passes(
    context_factory,
    run_rgaa,
):
    html = '<p id="summary">Ce tableau regroupe les résultats par projet et par catégorie.</p>' + complex_table(
        extra_attributes='aria-describedby="summary"'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.PASS


def test_511_missing_aria_describedby_target_does_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory(complex_table(extra_attributes='aria-describedby="missing-summary"'))

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.FAIL


def test_511_html5_summary_attribute_is_not_accepted(
    context_factory,
    run_rgaa,
):
    html = "<!DOCTYPE html>" + complex_table(extra_attributes='summary="Résumé historique du tableau"')
    context = context_factory(html)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.FAIL


def test_511_pre_html5_summary_attribute_is_accepted(
    context_factory,
    run_rgaa,
):
    doctype = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    html = doctype + complex_table(extra_attributes='summary="Structure du tableau par projet"')
    context = context_factory(html, doctype=doctype)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.PASS


def test_511_presentation_table_is_outside_scope(
    context_factory,
    run_rgaa,
):
    context = context_factory(complex_table(extra_attributes='role="presentation"'))

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_511_one_missing_summary_makes_the_test_fail(
    context_factory,
    run_rgaa,
):
    html = complex_table(caption="<caption>Résumé du premier tableau</caption>") + complex_table()
    context = context_factory(html)

    result = run_rgaa(RGAA511(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1

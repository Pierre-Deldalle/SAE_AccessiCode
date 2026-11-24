"""
Non-régressions : faux positifs trouvés en auditant test_files/site_conforme.

Chaque cas est une construction conforme au RGAA qui était signalée à tort.
"""

import pytest
from tests.ai_fakes import structure, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_7 import Test574
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_1 import Test713
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_5 import Test751, Test752, Test753
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_1 import Test1012, Test1013
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_3 import Test1031

# Tableau à en-têtes fusionnés associés par headers / id (technique RGAA 5.7.4).
COMPLEX_TABLE = """
<table>
    <caption>Contrôles par trimestre</caption>
    <thead>
        <tr>
            <th id="domaine" rowspan="2">Domaine</th>
            <th id="t1" colspan="2">Premier trimestre</th>
        </tr>
        <tr>
            <th id="t1-ok" headers="t1">Conformes</th>
            <th id="t1-ko" headers="t1">À vérifier</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <th id="structure" headers="domaine">Structure</th>
            <td headers="structure t1 t1-ok">18</td>
            <td headers="structure t1 t1-ko">0</td>
        </tr>
    </tbody>
</table>
"""


def test_574_merged_headers_are_associated_by_real_position(context_factory, run_rgaa):
    result = run_rgaa(Test574(), context_factory(COMPLEX_TABLE))

    assert result.status == Status.PASS
    assert result.findings == []


def test_574_missing_header_in_merged_table_still_fails(context_factory, run_rgaa):
    html = COMPLEX_TABLE.replace('headers="structure t1 t1-ok"', 'headers="structure t1-ok"')

    result = run_rgaa(Test574(), context_factory(html))

    assert result.status == Status.FAIL


def test_713_aria_labelledby_with_several_ids(context_factory, run_rgaa):
    html = """
    <svg role="img" aria-labelledby="titre desc" xmlns="http://www.w3.org/2000/svg">
        <title id="titre">Progression</title><desc id="desc">Cent pour cent</desc>
    </svg>
    <button role="button" aria-labelledby="titre desc">Progression</button>
    """

    result = run_rgaa(Test713(), context_factory(html), text_services())

    assert result.status == Status.PASS


def test_713_status_messages_are_not_interface_components(context_factory, run_rgaa):
    html = '<div role="status">Enregistré.</div><div role="alert">Erreur.</div><nav role="navigation"></nav>'

    result = run_rgaa(Test713(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("test_class", [Test751, Test752, Test753])
def test_75_page_title_and_svg_title_are_not_messages(test_class, context_factory, run_rgaa):
    html = """
    <html><head><title>Étape terminée, chargement réussi, erreur</title></head>
    <body><h1>Inscription terminée</h1>
    <svg><title>Barre de progression</title></svg></body></html>
    """

    result = run_rgaa(test_class(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE


def test_75_each_message_is_judged_by_its_own_category(context_factory, run_rgaa):
    html = """
    <div role="status">Votre demande a bien été enregistrée.</div>
    <div role="alert">Erreur : le champ adresse email est obligatoire.</div>
    <div role="log">Étape 3 terminée.</div>
    """
    context = context_factory(html)
    # L'IA confirme que les messages des autres catégories ne relèvent pas du test.
    ai = text_services(structure_answer=structure(False))

    assert run_rgaa(Test751(), context, ai).status == Status.PASS
    assert run_rgaa(Test752(), context, ai).status == Status.PASS
    assert run_rgaa(Test753(), context, ai).status == Status.PASS


def test_1012_dimension_attributes_allowed_by_html5(context_factory, run_rgaa):
    html = """
    <iframe title="Carte" src="carte.html" width="400" height="300"></iframe>
    <video src="v.mp4" width="320" height="180"></video>
    <input type="image" src="ok.png" alt="Valider" width="80" height="40">
    <svg width="40" height="20"><rect width="40" height="20"></rect></svg>
    """

    result = run_rgaa(Test1012(), context_factory(html))

    assert result.status == Status.PASS


def test_1012_width_on_paragraph_still_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1012(), context_factory('<table width="100%"><tr><td>x</td></tr></table>'))

    assert result.status == Status.FAIL


def test_1013_ordinary_sentence_is_not_letter_spacing(context_factory, run_rgaa):
    html = "<p>Ce site conforme a bien été vérifié, il y a 3 jours.</p>"

    result = run_rgaa(Test1013(), context_factory(html))

    assert not any(f.evidence.get("pattern_type") == "letter_spacing" for f in result.findings)


def test_1013_spaced_out_word_is_still_detected(context_factory, run_rgaa):
    result = run_rgaa(Test1013(), context_factory("<p>I M P O R T A N T : lire la suite.</p>"))

    assert any(f.evidence.get("pattern_type") == "letter_spacing" for f in result.findings)


def test_1031_image_button_does_not_need_a_label(context_factory, run_rgaa):
    html = '<form><label for="q">Recherche</label><input id="q"><input type="image" src="ok.png" alt="Lancer"></form>'

    result = run_rgaa(Test1031(), context_factory(html))

    assert result.status == Status.PASS

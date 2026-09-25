import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_1 import (
    Test1111 as RGAA1111,
)


def test_1111_field_with_label_for_passes(
    context_factory,
    run_rgaa,
):
    html = """
    <form>
        <label for="email">Adresse e-mail</label>
        <input id="email" type="email">
    </form>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_1111_field_with_aria_label_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="text" aria-label="Nom">')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS


def test_1111_field_with_aria_labelledby_passes(
    context_factory,
    run_rgaa,
):
    html = """
    <span id="email-label">Adresse e-mail</span>
    <input type="email" aria-labelledby="email-label">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS


def test_1111_multiple_aria_labelledby_references_pass_when_all_are_valid(
    context_factory,
    run_rgaa,
):
    html = """
    <span id="first">Date</span>
    <span id="second">de naissance</span>
    <input type="text" aria-labelledby="first second">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS


def test_1111_field_with_title_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="text" title="Nom complet">')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS


def test_1111_field_without_label_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="text" id="username">')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_1111_invalid_aria_labelledby_reference_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="text" aria-labelledby="missing-label">')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL


def test_1111_one_missing_aria_labelledby_reference_invalidates_the_mechanism(
    context_factory,
    run_rgaa,
):
    html = """
    <span id="first">Date</span>
    <input type="text" aria-labelledby="first missing">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL


def test_1111_duplicate_referenced_id_is_not_unambiguous(
    context_factory,
    run_rgaa,
):
    html = """
    <span id="field-label">Premier texte</span>
    <span id="field-label">Deuxième texte</span>
    <input type="text" aria-labelledby="field-label">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL


def test_1111_empty_label_attributes_do_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="text" aria-label="   " title="">')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL


def test_1111_wrapping_label_without_for_is_not_the_rgaa_111_mechanism(
    context_factory,
    run_rgaa,
):
    context = context_factory('<label>Nom <input type="text"></label>')

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL


@pytest.mark.parametrize(
    "field_html",
    [
        '<textarea aria-label="Message"></textarea>',
        '<select aria-label="Pays"><option>France</option></select>',
        '<output aria-label="Résultat">42</output>',
        '<progress aria-label="Progression" max="100" value="50"></progress>',
        '<meter aria-label="Niveau" min="0" max="10" value="5"></meter>',
        '<div role="textbox" aria-label="Commentaire"></div>',
        '<div role="slider" aria-label="Volume"></div>',
        '<div role="combobox" aria-label="Ville"></div>',
        '<input type="checkbox" aria-label="Accepter">',
        '<input type="radio" aria-label="Option A">',
        '<input type="file" aria-label="Pièce jointe">',
    ],
)
def test_1111_supported_form_field_types_are_checked(
    context_factory,
    run_rgaa,
    field_html,
):
    context = context_factory(field_html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1111_non_form_fields_are_ignored(
    context_factory,
    run_rgaa,
):
    html = """
    <input type="submit" value="Envoyer">
    <input type="reset" value="Réinitialiser">
    <input type="hidden" value="secret">
    <input type="image" src="send.png" alt="Envoyer">
    <input type="button" value="Action">
    <button>Valider</button>
    <div role="button">Action ARIA</div>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1111_one_unlabelled_field_makes_multiple_fields_fail(
    context_factory,
    run_rgaa,
):
    html = """
    <label for="email">E-mail</label>
    <input id="email" type="email">

    <input type="search" aria-label="Recherche">

    <input id="phone" type="tel">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert len(result.findings) == 1


def test_1111_no_form_fields_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><h1>Page sans formulaire</h1></main>")

    result = run_rgaa(RGAA1111(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0

"""Tests unitaires du critère RGAA 11.2, sans IA ni réseau."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_2 import (
    Test1121,
    Test1122,
    Test1123,
    Test1124,
    Test1125,
    Test1126,
)


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test1121, '<label for="a">Adresse e-mail</label><input id="a" type="email">'),
        (Test1121, '<label>Adresse e-mail<input type="email"></label>'),
        (Test1122, '<input type="email" title="Adresse e-mail">'),
        (Test1123, '<input type="email" aria-label="Adresse e-mail">'),
        (Test1124, '<span id="lab">Adresse e-mail</span><input type="email" aria-labelledby="lab">'),
        (Test1124, '<span id="a">Adresse</span><span id="b">e-mail</span><input type="email" aria-labelledby="a b">'),
    ],
)
def test_1121_to_1124_clear_relevance_passes(context_factory, run_rgaa, test_class, html):
    result = run_rgaa(test_class(), context_factory(html))
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test1121, '<label for="a"></label><input id="a" type="text">'),
        (Test1122, '<input type="text" title="  ">'),
        (Test1123, '<input type="text" aria-label="">'),
        (Test1124, '<input type="text" aria-labelledby="missing">'),
        (Test1124, '<span id="x">Nom</span><input aria-labelledby="x missing">'),
        (Test1124, '<span id="x">Nom</span><span id="x">Prénom</span><input aria-labelledby="x">'),
    ],
)
def test_1121_to_1124_certain_invalid_labels_fail(context_factory, run_rgaa, test_class, html):
    result = run_rgaa(test_class(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert result.findings
    assert result.findings[0].element
    assert result.findings[0].message
    assert result.findings[0].recommendation


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test1121, '<label for="x">Nom</label><input id="x" type="text">'),
        (Test1122, '<input type="text" title="Nom complet">'),
        (Test1123, '<input type="text" aria-label="Nom complet">'),
        (Test1124, '<span id="x">Nom complet</span><input type="text" aria-labelledby="x">'),
    ],
)
def test_1121_to_1124_ambiguous_semantics_need_review(context_factory, run_rgaa, test_class, html):
    result = run_rgaa(test_class(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings


@pytest.mark.parametrize("test_class", [Test1121, Test1122, Test1123, Test1124])
def test_1121_to_1124_no_candidate_not_applicable(context_factory, run_rgaa, test_class):
    result = run_rgaa(test_class(), context_factory('<input type="text">'))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1122_title_not_used_when_label_present(context_factory, run_rgaa):
    html = '<label for="x">Nom</label><input id="x" title="Autre nom">'
    assert run_rgaa(Test1122(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1123_aria_label_overridden_by_aria_labelledby(context_factory, run_rgaa):
    html = '<span id="x">Nom</span><input aria-label="Autre" aria-labelledby="x">'
    assert run_rgaa(Test1123(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1121_mixed_fields_fail_over_review(context_factory, run_rgaa):
    html = '''
    <label for="a">Nom</label><input id="a">
    <label for="b"></label><input id="b">
    '''
    result = run_rgaa(Test1121(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert result.metadata["failed"] == 1
    assert result.metadata["needs_review"] == 1


def test_1125_visible_label_contained_in_aria_label_passes(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n" aria-label="Nom complet">'
    result = run_rgaa(Test1125(), context_factory(html))
    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1125_punctuation_and_case_can_be_ignored(context_factory, run_rgaa):
    html = '<label for="n">NOM :</label><input id="n" aria-label="Nom complet">'
    assert run_rgaa(Test1125(), context_factory(html)).status == Status.PASS


def test_1125_mismatch_fails_with_evidence(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n" aria-label="Adresse e-mail">'
    result = run_rgaa(Test1125(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert result.findings[0].evidence["visible_label"] == "Nom"
    assert result.findings[0].evidence["accessible_label"] == "Adresse e-mail"


def test_1125_checks_title_even_if_aria_label_matches(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n" aria-label="Nom complet" title="Adresse">'
    result = run_rgaa(Test1125(), context_factory(html))
    assert result.status == Status.FAIL
    assert any(f.evidence.get("mechanism") == "title" for f in result.findings)


def test_1125_aria_labelledby_matches_visible_label(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><span id="l">Nom complet</span><input id="n" aria-labelledby="l">'
    assert run_rgaa(Test1125(), context_factory(html)).status == Status.PASS


def test_1125_missing_reference_needs_review(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n" aria-labelledby="missing">'
    result = run_rgaa(Test1125(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings


def test_1125_symbol_special_case_needs_review(context_factory, run_rgaa):
    html = '<label for="b">&gt;</label><input id="b" aria-label="Suivant">'
    assert run_rgaa(Test1125(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1125_aria_label_without_known_visible_label_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1125(), context_factory('<input aria-label="Nom">'))
    assert result.status == Status.NEEDS_REVIEW


def test_1125_no_label_or_accessible_name_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test1125(), context_factory('<input type="text">'))
    assert result.status == Status.NOT_APPLICABLE


def test_1125_fail_has_priority_over_review(context_factory, run_rgaa):
    html = '''
    <label for="a">Nom</label><input id="a" aria-label="Email">
    <input aria-label="Téléphone">
    '''
    result = run_rgaa(Test1125(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 2


def test_1126_adjacent_button_needs_review(context_factory, run_rgaa):
    html = '<div><input type="search"><button>Rechercher</button></div>'
    result = run_rgaa(Test1126(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].evidence["button_text"] == "Rechercher"


def test_1126_adjacent_input_submit_needs_review(context_factory, run_rgaa):
    html = '<div><input type="search"><input type="submit" value="Chercher"></div>'
    assert run_rgaa(Test1126(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1126_no_adjacent_button_not_applicable(context_factory, run_rgaa):
    html = '<div><label for="n">Nom</label><input id="n"></div>'
    result = run_rgaa(Test1126(), context_factory(html))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1126_button_in_unrelated_container_is_not_adjacent(context_factory, run_rgaa):
    html = '<div><input type="search"></div><div><button>Chercher</button></div>'
    assert run_rgaa(Test1126(), context_factory(html)).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("test_class", [Test1121, Test1122, Test1123, Test1124, Test1125, Test1126])
def test_112_all_empty_page_not_applicable(context_factory, run_rgaa, test_class):
    result = run_rgaa(test_class(), context_factory('<main><h1>Accueil</h1></main>'))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0

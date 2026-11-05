"""Tests unitaires RGAA 11.3, sans réseau ni IA."""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_3 import (
    Test1131,
    Test1132,
)


def test_1131_identical_labels_pass(context_factory, run_rgaa):
    html = '''
    <label for="a">Adresse e-mail</label><input id="a" name="email">
    <label for="b">Adresse e-mail</label><input id="b" name="email">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.PASS
    assert result.tested_elements == 2
    assert result.findings == []


def test_1131_synonyms_pass(context_factory, run_rgaa):
    html = '''
    <input type="email" autocomplete="email" aria-label="E-mail">
    <input type="email" autocomplete="email" aria-label="Courriel">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.PASS
    assert result.metadata["confirmed_groups"] == 1


def test_1131_accents_and_punctuation_pass(context_factory, run_rgaa):
    html = '''
    <input name="postal" aria-label="Code postal :">
    <input name="postal" aria-label="CODE POSTAL">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.PASS


def test_1131_clear_contradiction_fail(context_factory, run_rgaa):
    html = '''
    <input autocomplete="email" aria-label="Adresse e-mail">
    <input autocomplete="email" aria-label="Téléphone">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert result.findings[0].message
    assert result.findings[0].recommendation
    assert result.findings[0].evidence["function_key"] == "autocomplete:email"
    assert len(result.findings[0].evidence["labels"]) == 2


def test_1131_different_labels_without_clear_semantics_review(context_factory, run_rgaa):
    html = '''
    <input name="reference" aria-label="Référence dossier">
    <input name="reference" aria-label="Identifiant dossier">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings


def test_1131_empty_label_review(context_factory, run_rgaa):
    html = '''
    <input name="email" aria-label="Courriel">
    <input name="email" aria-label="">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW


def test_1131_missing_labels_review(context_factory, run_rgaa):
    html = '<input name="email"><input name="email">'
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1131_no_fields_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test1131(), context_factory('<main>Accueil</main>'))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1131_unique_fields_not_applicable(context_factory, run_rgaa):
    html = '<input name="email" aria-label="Email"><input name="phone" aria-label="Téléphone">'
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.NOT_APPLICABLE


def test_1131_radio_choices_not_mistaken_for_same_label(context_factory, run_rgaa):
    html = '''
    <label><input type="radio" name="payment">Carte</label>
    <label><input type="radio" name="payment">Espèces</label>
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1131_shipping_and_billing_are_separate(context_factory, run_rgaa):
    html = '''
    <input autocomplete="shipping postal-code" aria-label="Code postal">
    <input autocomplete="billing postal-code" aria-label="Ville">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1131_fail_priority_over_review(context_factory, run_rgaa):
    html = '''
    <input autocomplete="email" aria-label="Email">
    <input autocomplete="email" aria-label="Téléphone">
    <input name="ref" aria-label="Référence">
    <input name="ref" aria-label="Numéro de dossier">
    '''
    result = run_rgaa(Test1131(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.metadata["failed_groups"] == 1
    assert result.metadata["review_groups"] == 1
    assert result.tested_elements == 4


def test_1131_aria_labelledby_resolves(context_factory, run_rgaa):
    html = '''
    <span id="a">Courriel</span><input name="email" aria-labelledby="a">
    <span id="b">E-mail</span><input name="email" aria-labelledby="b">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.PASS


def test_1131_broken_aria_labelledby_review(context_factory, run_rgaa):
    html = '''
    <input name="email" aria-labelledby="absent">
    <input name="email" aria-label="Courriel">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1131_label_for_and_wrapping_label(context_factory, run_rgaa):
    html = '''
    <label for="a">Courriel</label><input id="a" name="email">
    <label>E-mail<input name="email"></label>
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.PASS


def test_1131_title_labels(context_factory, run_rgaa):
    html = '''
    <input name="email" title="Courriel">
    <input name="email" title="E-mail">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.PASS


def test_1131_placeholder_not_a_label(context_factory, run_rgaa):
    html = '''
    <input name="email" placeholder="Courriel">
    <input name="email" placeholder="E-mail">
    '''
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NEEDS_REVIEW


def _with_pages(context_factory, html_by_page):
    context = context_factory(next(iter(html_by_page.values())))
    context.page_doms = {
        page: BeautifulSoup(html, "html.parser")
        for page, html in html_by_page.items()
    }
    return context


def test_1132_without_page_doms_review(context_factory, run_rgaa):
    context = context_factory('<input name="search" aria-label="Recherche">')
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0


def test_1132_only_one_page_review(context_factory, run_rgaa):
    context = _with_pages(context_factory, {'a': '<input name="search" aria-label="Recherche">'})
    assert run_rgaa(Test1132(), context).status == Status.NEEDS_REVIEW


def test_1132_consistent_labels_pass(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input name="search" aria-label="Recherche">',
        'b.html': '<input name="search" aria-label="Rechercher">',
    })
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 2
    assert result.metadata['pages_analyzed'] == 2


def test_1132_inconsistent_labels_fail(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input autocomplete="email" aria-label="Courriel">',
        'b.html': '<input autocomplete="email" aria-label="Téléphone">',
    })
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.FAIL
    assert result.findings[0].evidence['labels'][0]['page'] == 'a.html'
    assert result.findings[0].evidence['labels'][1]['page'] == 'b.html'


def test_1132_ambiguous_labels_review(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input name="ref" aria-label="Référence">',
        'b.html': '<input name="ref" aria-label="Numéro de dossier">',
    })
    assert run_rgaa(Test1132(), context).status == Status.NEEDS_REVIEW


def test_1132_no_repetition_between_pages_not_applicable(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input name="email" aria-label="Courriel">',
        'b.html': '<input name="search" aria-label="Recherche">',
    })
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1132_repeated_only_on_one_page_not_applicable(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input name="email" aria-label="Courriel"><input name="email" aria-label="Téléphone">',
        'b.html': '<input name="search" aria-label="Recherche">',
    })
    assert run_rgaa(Test1132(), context).status == Status.NOT_APPLICABLE


def test_1132_invalid_page_dom_review(context_factory, run_rgaa):
    context = context_factory('<input name="email" aria-label="Courriel">')
    context.page_doms = {'a.html': context.dom, 'b.html': None}
    assert run_rgaa(Test1132(), context).status == Status.NEEDS_REVIEW


def test_1132_fail_priority_over_review(context_factory, run_rgaa):
    context = _with_pages(context_factory, {
        'a.html': '<input autocomplete="email" aria-label="Courriel"><input name="ref" aria-label="Référence">',
        'b.html': '<input autocomplete="email" aria-label="Téléphone"><input name="ref" aria-label="Numéro de dossier">',
    })
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.FAIL
    assert result.metadata['failed_groups'] == 1
    assert result.metadata['review_groups'] == 1


@pytest.mark.parametrize('test_class', [Test1131, Test1132])
def test_test_ids(test_class):
    assert test_class.criterion_id == '11.3'
    assert test_class.test_id.startswith('11.3.')


def test_1131_same_name_but_opposing_labels_requires_review(context_factory, run_rgaa):
    html = '<input name="contact" aria-label="Courriel"><input name="contact" aria-label="Téléphone">'
    assert run_rgaa(Test1131(), context_factory(html)).status == Status.NEEDS_REVIEW

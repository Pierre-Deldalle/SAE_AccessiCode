"""Critère RGAA 11.1 : présence et association des étiquettes."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_1 import Test1111, Test1112, Test1113


@pytest.mark.parametrize("cls", [Test1111, Test1112, Test1113])
def test_no_field_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


# ---- 11.1.1 ----------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        '<label for="n">Nom</label><input id="n">',
        '<input aria-label="Nom">',
        '<span id="l">Nom</span><input aria-labelledby="l">',
        '<input title="Nom">',
    ],
)
def test_1111_labelled_field_passes(html, context_factory, run_rgaa):
    assert run_rgaa(Test1111(), context_factory(html)).status == Status.PASS


def test_1111_unlabelled_field_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1111(), context_factory('<input id="n" placeholder="Nom">'))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "input#n"


def test_1111_wrapping_label_is_not_a_label_for(context_factory, run_rgaa):
    result = run_rgaa(Test1111(), context_factory("<label>Nom <input></label>"))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["wrapping_label"] is True


def test_1111_two_labels_for_the_same_field_pass(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n"><label for="n">(obligatoire)</label>'
    assert run_rgaa(Test1111(), context_factory(html)).status == Status.PASS


def test_1111_broken_labelledby_fails(context_factory, run_rgaa):
    assert run_rgaa(Test1111(), context_factory('<input aria-labelledby="absent">')).status == Status.FAIL


# ---- 11.1.2 ----------------------------------------------------------


def test_1112_label_for_matching_unique_id_passes(context_factory, run_rgaa):
    assert run_rgaa(Test1112(), context_factory('<label for="n">Nom</label><input id="n">')).status == Status.PASS


@pytest.mark.parametrize(
    ("html", "message"),
    [
        ('<label for="x">Nom</label><input id="n">', "Aucun champ"),
        ('<label for="n">Nom</label><input id="n"><input id="n">', "pas unique"),
        ('<label for="n">Nom</label><p id="n">Texte</p>', "n'est pas un champ"),
        ('<label for="">Nom</label><input id="n">', "vide"),
    ],
)
def test_1112_broken_association_fails(html, message, context_factory, run_rgaa):
    result = run_rgaa(Test1112(), context_factory(html))
    assert result.status == Status.FAIL
    assert message in result.findings[0].message


# ---- 11.1.3 ----------------------------------------------------------


def test_1113_visible_label_is_out_of_scope(context_factory, run_rgaa):
    html = '<label for="n">Nom</label><input id="n">'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1113_aria_label_without_title_nor_adjacent_text_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1113(), context_factory('<div><input aria-label="Rechercher"></div>'))
    assert result.status == Status.FAIL


def test_1113_aria_label_with_title_passes(context_factory, run_rgaa):
    html = '<div><input aria-label="Rechercher" title="Rechercher sur le site"></div>'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.PASS


def test_1113_aria_label_with_adjacent_visible_text_passes(context_factory, run_rgaa):
    html = '<p>Votre e-mail : <input aria-label="Votre e-mail"></p>'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.PASS


def test_1113_hidden_label_fails(context_factory, run_rgaa):
    html = '<div><label class="sr-only" for="n">Nom</label></div><div><input id="n"></div>'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.FAIL


def test_1113_distant_labelledby_needs_review(context_factory, run_rgaa):
    html = '<h2 id="t">Recherche</h2><section><div><input aria-labelledby="t"></div></section>'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1113_adjacent_labelledby_is_out_of_scope(context_factory, run_rgaa):
    html = '<div><span id="t">Recherche</span><input aria-labelledby="t"></div>'
    assert run_rgaa(Test1113(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1113_browser_layout_evidence(context_factory, run_rgaa):
    html = '<h2 id="t">Recherche</h2><section><div><input id="q" aria-labelledby="t"></div></section>'
    context = context_factory(html)
    context.form_label_layout = {"input#q": {"verified": True, "adjacent": True}}
    assert run_rgaa(Test1113(), context).status == Status.PASS

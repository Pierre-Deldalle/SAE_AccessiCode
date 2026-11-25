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


@pytest.mark.parametrize(
    ("cls", "html", "line", "snippet"),
    [
        (Test1111, '<p>Intro</p>\n<input id="q" name="q">', 2, '<input id="q" name="q">'),
        (Test1112, '<p>Intro</p>\n<label for="absent">Nom</label>', 2, '<label for="absent">Nom</label>'),
        (Test1113, '<p>Intro</p>\n<input id="q" aria-label="Nom">', 2, '<input id="q" aria-label="Nom">'),
    ],
)
def test_fail_gives_line_and_snippet(cls, html, line, snippet, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory(html))
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (line, snippet)


# Exemples « avant / après » ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("html", "after"),
    [
        (
            '<input name="nom" placeholder="Nom">',
            '<input name="nom" placeholder="Nom"> → <label for="nom">Nom</label>'
            '<input name="nom" placeholder="Nom" id="nom">',
        ),
        (
            '<input type="radio" name="g" value="f"> Femme',
            '<input type="radio" name="g" value="f"> Femme → '
            '<input type="radio" name="g" value="f" id="g-f"> <label for="g-f">Femme</label>',
        ),
        (
            '<p id="nom">x</p><input name="nom">',
            '<input name="nom"> → <label for="nom-2">[intitulé du champ]</label><input name="nom" id="nom-2">',
        ),
        (
            '<div role="progressbar" aria-valuenow="60"></div>',
            '<div role="progressbar" aria-valuenow="60"> → '
            '<div role="progressbar" aria-valuenow="60" aria-label="[intitulé du champ]">',
        ),
    ],
    ids=["placeholder", "radio", "id déjà pris", "composant ARIA"],
)
def test_1111_example_adds_a_label(html, after, context_factory, run_rgaa):
    result = run_rgaa(Test1111(), context_factory(html))
    assert result.findings[0].recommendation.endswith(f"Exemple : {after}")


@pytest.mark.parametrize(
    ("html", "after"),
    [
        ('<label for="x">Courriel</label><input id="mail" type="email">', '<label for="x"> → <label for="mail">'),
        (
            '<label for="mail">Courriel</label><input type="email">',
            '<input type="email"> → <input type="email" id="mail">',
        ),
        (
            '<label for="">Courriel</label><input type="email">',
            '<label for=""> … <input type="email"> → <label for="input"> … <input type="email" id="input">',
        ),
    ],
    ids=["for corrigé", "id ajouté", "for vide"],
)
def test_1112_example_links_the_label_to_its_field(html, after, context_factory, run_rgaa):
    result = run_rgaa(Test1112(), context_factory(html))
    assert result.findings[0].recommendation.endswith(f"Exemple : {after}")


@pytest.mark.parametrize(
    "html",
    [
        '<label for="d">A</label><input id="d"><span id="d"></span>',
        '<label for="x">A</label><label for="b">B</label><input id="b">',
    ],
    ids=["id en double", "champ déjà étiqueté"],
)
def test_1112_no_example_when_the_field_is_uncertain(html, context_factory, run_rgaa):
    result = run_rgaa(Test1112(), context_factory(html))
    assert result.status == Status.FAIL
    assert "Exemple" not in result.findings[0].recommendation


@pytest.mark.parametrize(
    ("html", "after"),
    [
        (
            '<input id="q" aria-label="Nom">',
            '<input id="q" aria-label="Nom"> → <input id="q" aria-label="Nom" title="Nom">',
        ),
        ('<label for="q" hidden>Nom</label><input id="q">', '<input id="q"> → <input id="q" title="Nom">'),
    ],
    ids=["aria-label", "label masqué"],
)
def test_1113_example_adds_a_title(html, after, context_factory, run_rgaa):
    result = run_rgaa(Test1113(), context_factory(html))
    assert result.findings[0].recommendation.endswith(f"Exemple : {after}")


def test_1113_remote_labelledby_has_no_example(context_factory, run_rgaa):
    html = '<p id="t">Nom</p><div><span>x</span></div><div><input id="q" aria-labelledby="t"></div>'
    result = run_rgaa(Test1113(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert "Exemple" not in result.findings[0].recommendation

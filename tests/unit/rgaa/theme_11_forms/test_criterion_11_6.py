"""Critère RGAA 11.6 : légende des regroupements."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_6 import Test1161

FIELDS = "<input aria-label='Rue'><input aria-label='Ville'>"


def test_no_group_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test1161(), context_factory("<form><input></form>")).status == Status.NOT_APPLICABLE


def test_fieldset_with_legend_passes(context_factory, run_rgaa):
    html = f"<fieldset><legend>Adresse</legend>{FIELDS}</fieldset>"
    assert run_rgaa(Test1161(), context_factory(html)).status == Status.PASS


def test_fieldset_without_legend_fails(context_factory, run_rgaa):
    assert run_rgaa(Test1161(), context_factory(f"<fieldset>{FIELDS}</fieldset>")).status == Status.FAIL


def test_aria_group_requires_a_label(context_factory, run_rgaa):
    ok = f'<div role="group" aria-label="Adresse">{FIELDS}</div>'
    ko = f'<div role="group">{FIELDS}</div>'
    assert run_rgaa(Test1161(), context_factory(ok)).status == Status.PASS
    assert run_rgaa(Test1161(), context_factory(ko)).status == Status.FAIL


def test_unstructured_radios_with_membership_on_each_field_pass(context_factory, run_rgaa):
    html = (
        '<form><input type="radio" name="c" title="Civilité : Monsieur">'
        '<input type="radio" name="c" title="Civilité : Madame"></form>'
    )
    assert run_rgaa(Test1161(), context_factory(html)).status == Status.PASS


def test_unstructured_radios_with_only_labels_fail(context_factory, run_rgaa):
    html = (
        '<form><label for="a">M.</label><input id="a" type="radio" name="c">'
        '<label for="b">Mme</label><input id="b" type="radio" name="c"></form>'
    )
    result = run_rgaa(Test1161(), context_factory(html))
    assert result.status == Status.FAIL
    assert "appartenance" in result.findings[0].message


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    html = f'<p>Intro</p>\n<fieldset id="g">{FIELDS}</fieldset>'
    finding = run_rgaa(Test1161(), context_factory(html)).findings[0]
    assert (finding.line, finding.snippet) == (2, f'<fieldset id="g">{FIELDS.replace(chr(39), chr(34))}</fieldset>')


@pytest.mark.parametrize(
    ("group", "closing", "after"),
    [
        (
            '<fieldset id="g">',
            "</fieldset>",
            '<fieldset id="g"> → <fieldset id="g"><legend>[nature commune des champs]</legend>',
        ),
        (
            '<fieldset id="g"><legend></legend>',
            "</fieldset>",
            "<legend></legend> → <legend>[nature commune des champs]</legend>",
        ),
        (
            '<div role="group">',
            "</div>",
            '<div role="group"> → <div role="group" aria-label="[nature commune des champs]">',
        ),
    ],
    ids=["fieldset", "legend vide", "groupe ARIA"],
)
def test_fail_shows_a_legend_example(group, closing, after, context_factory, run_rgaa):
    finding = run_rgaa(Test1161(), context_factory(f"{group}{FIELDS}{closing}")).findings[0]
    assert finding.recommendation.endswith(f"Exemple : {after}")

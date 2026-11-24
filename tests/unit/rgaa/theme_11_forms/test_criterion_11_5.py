"""Critère RGAA 11.5 : regroupement des champs de même nature."""

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_5 import Test1151
from tests.ai_fakes import relevance, text_services

RADIOS = '<input type="radio" name="civ" aria-label="M."><input type="radio" name="civ" aria-label="Mme">'
DATE = (
    "<form><label for='j'>Jour</label><input id='j'><label for='m'>Mois</label><input id='m'>"
    "<label for='a'>Année</label><input id='a'></form>"
)


def test_no_field_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test1151(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_single_field_is_not_applicable(context_factory, run_rgaa):
    html = "<form><label for='a'>Nom</label><input id='a'></form>"
    assert run_rgaa(Test1151(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_grouped_radios_pass(context_factory, run_rgaa):
    html = f"<form><fieldset><legend>Civilité</legend>{RADIOS}</fieldset></form>"
    assert run_rgaa(Test1151(), context_factory(html), text_services()).status == Status.PASS


def test_ungrouped_radios_fail_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test1151(), context_factory(f"<form>{RADIOS}</form>"), ai)
    assert result.status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_ungrouped_same_nature_fields_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, problems=["Jour, Mois, Année"]))
    result = run_rgaa(Test1151(), context_factory(DATE), ai)
    assert result.status == Status.FAIL
    assert "Jour, Mois, Année" in result.findings[0].message
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "field_grouping"
    assert "- Jour" in items[0].text


def test_independent_fields_pass(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1151(), context_factory(DATE), ai).status == Status.PASS


def test_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test1151(), context_factory(DATE), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1151(), context_factory(DATE)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1151(), context_factory(DATE), broken).status == Status.ERROR


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    finding = run_rgaa(Test1151(), context_factory(f"<p>Intro</p>\n{RADIOS}"), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<input type="radio" name="civ" aria-label="M.">')


def test_ai_fail_points_to_the_form(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    finding = run_rgaa(Test1151(), context_factory(f"<p>Intro</p>\n{DATE}"), ai).findings[0]
    assert finding.line == 2
    assert finding.snippet.startswith("<form>")


def test_radio_fail_shows_a_fieldset_example(context_factory, run_rgaa):
    finding = run_rgaa(Test1151(), context_factory(RADIOS), text_services()).findings[0]
    assert finding.recommendation.endswith(
        'Exemple : <input type="radio" name="civ" aria-label="M."> → <fieldset><legend>[nature commune des champs]'
        '</legend><input type="radio" name="civ" aria-label="M."> … </fieldset>'
    )

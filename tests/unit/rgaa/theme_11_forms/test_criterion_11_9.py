"""Critère RGAA 11.9 : intitulés des boutons."""

from unittest.mock import AsyncMock

import pytest

from accessi_code.ai.schemas import ImageProfile
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_9 import Test1191, Test1192
from tests.ai_fakes import relevance, text_services

BUTTON = "<form><input aria-label='Recherche'><button>Rechercher</button></form>"


def image_services(profile: ImageProfile | Exception):
    services = text_services()
    services.image_analyzer = AsyncMock()
    if isinstance(profile, Exception):
        services.image_analyzer.profile.side_effect = profile
    else:
        services.image_analyzer.profile.return_value = profile
    return services


def text_profile(text: str, confidence: str = "high") -> ImageProfile:
    return ImageProfile(
        information_bearing=True,
        is_captcha=False,
        contains_text=True,
        needs_detailed_description=False,
        explanation="ok",
        text_content=text,
        confidence=confidence,
    )


@pytest.mark.parametrize("cls", [Test1191, Test1192])
def test_no_button_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


# ---- 11.9.1 ----------------------------------------------------------


def test_1191_relevant_button_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1191(), context_factory(BUTTON), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "button"
    assert items[0].text == "Rechercher"


def test_1191_irrelevant_button_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test1191(), context_factory("<form><button>Bouton</button></form>"), ai).status == Status.FAIL


def test_1191_button_without_name_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(Test1191(), context_factory("<form><button></button></form>"), ai).status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1191_icon_button_uses_image_alt(context_factory, run_rgaa):
    ai = text_services()
    html = '<form><button><img src="loupe.png" alt="Rechercher"></button></form>'
    assert run_rgaa(Test1191(), context_factory(html), ai).status == Status.PASS
    assert ai.text_relevance_analyzer.analyze_relevance.call_args.args[1][0].text == "Rechercher"


def test_1191_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test1191(), context_factory(BUTTON), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1191(), context_factory(BUTTON)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1191(), context_factory(BUTTON), broken).status == Status.ERROR


# ---- 11.9.2 ----------------------------------------------------------


def test_1192_button_without_other_name_source_is_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test1192(), context_factory("<form><button>Envoyer</button></form>"))
    assert result.status == Status.NOT_APPLICABLE


def test_1192_aria_label_containing_visible_text_passes(context_factory, run_rgaa):
    html = '<form><button aria-label="Envoyer le message">Envoyer</button></form>'
    assert run_rgaa(Test1192(), context_factory(html)).status == Status.PASS


def test_1192_case_and_punctuation_are_ignored(context_factory, run_rgaa):
    html = '<form><input type="submit" value="Envoyer !" title="envoyer le formulaire"></form>'
    assert run_rgaa(Test1192(), context_factory(html)).status == Status.PASS


def test_1192_aria_label_not_containing_visible_text_fails(context_factory, run_rgaa):
    html = '<form><button aria-label="Fermer">Envoyer</button></form>'
    result = run_rgaa(Test1192(), context_factory(html))
    assert result.status == Status.FAIL
    assert "aria-label « Fermer »" in result.findings[0].message


def test_1192_symbol_needs_review(context_factory, run_rgaa):
    html = '<form><button aria-label="Fermer">×</button></form>'
    assert run_rgaa(Test1192(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1192_image_button_text_read_by_vlm(context_factory, run_rgaa):
    html = '<form><input type="image" src="ok.png" alt="Valider la commande"></form>'
    assert run_rgaa(Test1192(), context_factory(html), image_services(text_profile("Valider"))).status == Status.PASS
    ko = image_services(text_profile("Payer"))
    assert run_rgaa(Test1192(), context_factory(html), ko).status == Status.FAIL


def test_1192_image_button_uncertain_or_error(context_factory, run_rgaa):
    html = '<form><input type="image" src="ok.png" alt="Valider"></form>'
    low = image_services(text_profile("Valider", confidence="low"))
    assert run_rgaa(Test1192(), context_factory(html), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1192(), context_factory(html)).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1192(), context_factory(html), image_services(RuntimeError("x"))).status == Status.ERROR


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    html = '<form>\n<button id="b"></button>\n</form>'
    finding = run_rgaa(Test1191(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<button id="b"></button>')


def test_ai_suggestion_is_proposed_on_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Envoyer le message"))
    finding = run_rgaa(Test1191(), context_factory("<form><button>OK</button></form>"), ai).findings[0]
    assert finding.recommendation.endswith("Proposition : « Envoyer le message ».")


def test_visible_label_missing_from_name_shows_an_example(context_factory, run_rgaa):
    html = '<form><button aria-label="Valider">Envoyer</button></form>'
    finding = run_rgaa(Test1192(), context_factory(html)).findings[0]
    assert finding.recommendation.endswith('Exemple : <button aria-label="Valider"> → <button aria-label="Envoyer">')


def test_labelledby_name_has_no_example(context_factory, run_rgaa):
    html = '<form><span id="n">Valider</span><button aria-labelledby="n">Envoyer</button></form>'
    result = run_rgaa(Test1192(), context_factory(html))
    assert result.status == Status.FAIL
    assert "Exemple" not in result.findings[0].recommendation

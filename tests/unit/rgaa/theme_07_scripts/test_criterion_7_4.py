"""Critère RGAA 7.4 : changements de contexte initiés par un script (avertissement jugé par l'IA)."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_4 import Test741
from tests.ai_fakes import relevance, text_services

LANGUAGES = (
    '<label for="l">Langue</label><select id="l" onchange="location.href=this.value"><option>FR</option></select>'
)


def submitted(ai):
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "context_change_warning"
    return items


@pytest.mark.parametrize(
    "html",
    [
        "<p>Texte</p>",
        '<div onclick="toggle()">Menu</div>',
        '<select onchange="trier(this.value)"><option>Prix</option></select>',
    ],
)
def test_741_no_context_change_is_not_applicable(html, context_factory, run_rgaa):
    # Un gestionnaire qui ne change pas de contexte n'est pas concerné (l'ancien test le jugeait non conforme).
    assert run_rgaa(Test741(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "html",
    [
        "<button onclick=\"window.open('/aide')\">Aide</button>",
        '<input type="submit" value="Envoyer" onclick="form.submit()">',
        '<a href="/a" onclick="location.href=\'/b\'">Suite</a>',
    ],
)
def test_741_change_from_explicit_button_or_link_passes(html, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test741(), context_factory(html), ai)
    assert result.status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_741_select_without_any_text_fails_with_example(context_factory, run_rgaa):
    html = '\n<select onchange="location.href=this.value"><option>FR</option></select>'
    result = run_rgaa(Test741(), context_factory(html), text_services())
    finding = result.findings[0]
    assert result.status == Status.FAIL
    assert finding.evidence["change"] == "nouvelle page"
    assert finding.line == 2
    assert finding.recommendation.endswith(
        'Exemple : <select onchange="location.href=this.value"> → <select> suivi de '
        '<button type="button">Valider</button>, qui exécute l\'action.'
    )


def test_741_warning_text_is_judged_by_ai(context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(Test741(), context_factory(LANGUAGES), ai).status == Status.PASS
    [item] = submitted(ai)
    assert item.text.startswith("Langue")
    assert item.details["change"] == "nouvelle page"
    assert item.context == "Déclenché par un choix dans une liste ou un champ"


def test_741_insufficient_warning_fails_with_ai_proposal(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Le choix d'une langue ouvre la page traduite"))
    result = run_rgaa(Test741(), context_factory(LANGUAGES), ai)
    assert result.status == Status.FAIL
    assert "Proposition : « Le choix d'une langue ouvre la page traduite »." in result.findings[0].recommendation


@pytest.mark.parametrize(
    "ai", [None, text_services(relevance_answer=relevance(False, confidence="low"))], ids=["sans IA", "incertaine"]
)
def test_741_unknown_warning_needs_review(ai, context_factory, run_rgaa):
    result = run_rgaa(Test741(), context_factory(LANGUAGES), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert "Proposition" not in result.findings[0].recommendation


def test_741_clickable_div_that_navigates_suggests_a_link(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test741(), context_factory("<div onclick=\"location.href='/aide'\">Aide</div>"), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation.endswith(
        'Exemple : <div onclick="location.href=\'/aide\'"> → <a href="/aide">'
    )


def test_741_script_listener_on_known_element(context_factory, run_rgaa):
    html = (
        '<select id="tri"><option>A</option></select><script>document.getElementById("tri")'
        '.addEventListener("change", () => { form.submit(); });</script>'
    )
    result = run_rgaa(Test741(), context_factory(html), text_services())
    assert result.status == Status.FAIL
    assert result.findings[0].element == "select#tri"
    assert result.findings[0].evidence["change"] == "envoi de formulaire"


def test_741_listener_on_unknown_element_needs_review_with_script_line(context_factory, run_rgaa):
    html = '<script>\ninit();\nfoo().addEventListener("change", () => { form.submit(); });\n</script>'
    result = run_rgaa(Test741(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert (result.findings[0].element, result.findings[0].line) == ("script[index=0]", 3)


def test_741_missing_dom_raises_error(context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="7.4.1 nécessite un DOM"):
        asyncio.run(Test741().run(context))

"""Critère RGAA 2.2 : pertinence du titre de cadre."""

from tests.ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_2 import Test221

FRAME = '<h2>Nous trouver</h2><iframe src="https://maps.example/agence" title="Plan d\'accès à l\'agence"></iframe>'


def test_no_titled_frame_is_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test221(), context_factory('<iframe src="a.html"></iframe>'), text_services())
    assert result.status == Status.NOT_APPLICABLE


def test_relevant_title_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test221(), context_factory(FRAME), ai)
    assert result.status == Status.PASS
    assert result.findings == []
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "frame_title"
    assert items[0].text == "Plan d'accès à l'agence"
    assert items[0].details["src"] == "https://maps.example/agence"
    assert "Nous trouver" in items[0].context


def test_irrelevant_title_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test221(), context_factory('<iframe src="m.html" title="iframe"></iframe>'), ai)
    assert result.status == Status.FAIL
    assert "n'est pas pertinent" in result.findings[0].message


def test_empty_title_fails_without_ai_call(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test221(), context_factory('<iframe src="m.html" title="  "></iframe>'), ai)
    assert result.status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test221(), context_factory(FRAME), ai).status == Status.NEEDS_REVIEW


def test_unknown_relevance_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    assert run_rgaa(Test221(), context_factory(FRAME), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test221(), context_factory(FRAME))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test221(), context_factory(FRAME), ai).status == Status.ERROR


def test_mixed_results(context_factory, run_rgaa):
    html = FRAME + '<iframe src="pub.html" title="Publicité"></iframe><iframe src="x.html" title=""></iframe>'
    ai = text_services(relevance_answer=[relevance(True), relevance(None)])
    result = run_rgaa(Test221(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.metadata["statuses"] == {
        "fail": 1,
        "error": 0,
        "needs_review": 1,
        "not_tested": 0,
        "pass": 1,
        "not_applicable": 0,
    }


def test_item_limit(context_factory, run_rgaa, monkeypatch):
    monkeypatch.setenv("ACCESSICODE_AI_MAX_ITEMS", "1")
    html = '<iframe src="a.html" title="Carte"></iframe><iframe src="b.html" title="Vidéo"></iframe>'
    result = run_rgaa(Test221(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert "Limite" in result.findings[0].message

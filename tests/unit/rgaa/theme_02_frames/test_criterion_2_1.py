"""Critère RGAA 2.1 : présence d'un titre de cadre."""

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_1 import Test211


def test_no_frame_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test211(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_iframe_with_title_passes(context_factory, run_rgaa):
    assert run_rgaa(Test211(), context_factory('<iframe src="m.html" title="Carte"></iframe>')).status == Status.PASS


def test_empty_title_is_present_for_2_1_1(context_factory, run_rgaa):
    # La pertinence d'un titre vide relève du test 2.2.1.
    assert run_rgaa(Test211(), context_factory('<iframe src="m.html" title=""></iframe>')).status == Status.PASS


def test_iframe_without_title_fails(context_factory, run_rgaa):
    result = run_rgaa(Test211(), context_factory('<iframe id="carte" src="m.html"></iframe>'))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "iframe#carte"


def test_frame_without_title_fails(context_factory, run_rgaa):
    html = '<frameset><frame src="a.html" title="Menu"><frame src="b.html"></frameset>'
    result = run_rgaa(Test211(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert result.metadata["statuses"]["pass"] == 1

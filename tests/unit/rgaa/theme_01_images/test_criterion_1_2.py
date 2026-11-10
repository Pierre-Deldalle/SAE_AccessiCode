"""Non-régressions du critère RGAA 1.2."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_2 import (
    Test121,
    Test122,
    Test123,
    Test124,
    Test125,
    Test126,
)


@pytest.mark.parametrize("cls", [
    Test121,
    Test122,
    Test123,
    Test124,
    Test125,
    Test126,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_decorative_img_alt_empty_pass(context_factory, run_rgaa):
    assert run_rgaa(Test121(), context_factory('<img alt="" src="decoration.png">')).status == Status.PASS

def test_decorative_img_with_title_fails(context_factory, run_rgaa):
    assert run_rgaa(Test121(), context_factory('<img alt="" title="Décor">')).status == Status.FAIL

def test_decorative_svg_hidden_pass(context_factory, run_rgaa):
    assert run_rgaa(Test124(), context_factory('<svg aria-hidden="true"><path d="M0"/></svg>')).status == Status.PASS

def test_decorative_svg_with_title_fails(context_factory, run_rgaa):
    assert run_rgaa(Test124(), context_factory('<svg aria-hidden="true"><title>Décor</title></svg>')).status == Status.FAIL

def test_nonclickable_area_decorative_passes(context_factory, run_rgaa):
    assert run_rgaa(Test122(), context_factory('<area alt="">')).status == Status.PASS

def test_decorative_object_passes(context_factory, run_rgaa):
    assert run_rgaa(Test123(), context_factory('<object type="image/png" aria-hidden="true"></object>')).status == Status.PASS

def test_decorative_canvas_passes(context_factory, run_rgaa):
    assert run_rgaa(Test125(), context_factory('<canvas aria-hidden="true"></canvas>')).status == Status.PASS

def test_decorative_embed_passes(context_factory, run_rgaa):
    assert run_rgaa(Test126(), context_factory('<embed type="image/png" aria-hidden="true">')).status == Status.PASS

"""Non-régressions du critère RGAA 1.8."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_8 import (
    Test181,
    Test182,
    Test183,
    Test184,
    Test185,
    Test186,
)


@pytest.mark.parametrize("cls", [
    Test181,
    Test182,
    Test183,
    Test184,
    Test185,
    Test186,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_text_image_unknown_requires_review(context_factory, run_rgaa):
    assert run_rgaa(Test181(), context_factory('<img alt="Titre" src="title.png">')).status == Status.NEEDS_REVIEW

def test_svg_with_real_text_only_not_in_scope(context_factory, run_rgaa):
    html='<svg><text x="0" y="10">Texte réel</text></svg>'
    assert run_rgaa(Test186(), context_factory(html)).status == Status.NOT_APPLICABLE

def test_text_image_exception_not_applicable(context_factory, run_rgaa):
    html='<img id="logo" alt="Marque" src="logo.png">'
    ctx=context_factory(html, image_evidence={'img#logo': {'verified':True, 'is_text_image':True, 'special_case':True}})
    assert run_rgaa(Test181(), ctx).status == Status.NOT_APPLICABLE

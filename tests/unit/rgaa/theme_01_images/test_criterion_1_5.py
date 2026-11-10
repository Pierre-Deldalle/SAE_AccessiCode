"""Non-régressions du critère RGAA 1.5."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_5 import (
    Test151,
    Test152,
)


@pytest.mark.parametrize("cls", [
    Test151,
    Test152,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_captcha_alternative_requires_proof(context_factory, run_rgaa):
    html='<img id="captcha" alt="Captcha">'
    assert run_rgaa(Test151(), context_factory(html)).status == Status.NEEDS_REVIEW
    ctx=context_factory(html, image_evidence={'img#captcha': {'verified':True,'accessible_captcha_alternative':True}})
    assert run_rgaa(Test151(), ctx).status == Status.PASS

def test_captcha_input_alternative(context_factory, run_rgaa):
    html='<input id="captcha" type="image" alt="Captcha">'
    assert run_rgaa(Test152(), context_factory(html)).status == Status.NEEDS_REVIEW

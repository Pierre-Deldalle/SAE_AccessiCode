"""Non-régressions du critère RGAA 1.4."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_4 import (
    Test141,
    Test142,
    Test143,
    Test144,
    Test145,
    Test146,
    Test147,
)


@pytest.mark.parametrize("cls", [
    Test141,
    Test142,
    Test143,
    Test144,
    Test145,
    Test146,
    Test147,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_captcha_with_alt_needs_semantic_check(context_factory, run_rgaa):
    assert run_rgaa(Test141(), context_factory('<img id="captcha" alt="Code à saisir">')).status == Status.NEEDS_REVIEW

def test_captcha_area_semantics(context_factory, run_rgaa):
    html='<map id="captcha"><area href="/verify" alt="Choisir une image"></map>'
    assert run_rgaa(Test142(), context_factory(html)).status == Status.NEEDS_REVIEW

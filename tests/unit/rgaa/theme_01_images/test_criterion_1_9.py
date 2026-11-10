"""Non-régressions du critère RGAA 1.9."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_9 import (
    Test191,
    Test192,
    Test193,
    Test194,
    Test195,
)


@pytest.mark.parametrize("cls", [
    Test191,
    Test192,
    Test193,
    Test194,
    Test195,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_caption_figure_passes(context_factory, run_rgaa):
    html='<figure role="figure" aria-label="Légende"><img alt="Photo"><figcaption>Légende</figcaption></figure>'
    assert run_rgaa(Test191(), context_factory(html)).status == Status.PASS

def test_caption_missing_role_fails(context_factory, run_rgaa):
    html='<figure aria-label="Légende"><img alt="Photo"><figcaption>Légende</figcaption></figure>'
    assert run_rgaa(Test191(), context_factory(html)).status == Status.FAIL

def test_object_caption_pass(context_factory, run_rgaa):
    html='<figure role="group" aria-label="Légende"><object type="image/png"></object><figcaption>Légende</figcaption></figure>'
    assert run_rgaa(Test192(), context_factory(html)).status == Status.PASS

def test_svg_caption_pass(context_factory, run_rgaa):
    html='<figure role="figure" aria-label="Légende"><svg></svg><figcaption>Légende</figcaption></figure>'
    assert run_rgaa(Test194(), context_factory(html)).status == Status.PASS

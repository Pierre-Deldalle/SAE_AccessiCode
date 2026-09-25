from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_5 import (
    Test851 as RGAA851,
)


def test_851_title_element_present_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><head><title>Accueil</title></head><body></body></html>")

    result = run_rgaa(RGAA851(), context)

    assert result.status == Status.PASS


def test_851_empty_title_element_still_satisfies_presence_test(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><head><title></title></head><body></body></html>")

    result = run_rgaa(RGAA851(), context)

    assert result.status == Status.PASS


def test_851_missing_title_element_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><head></head><body></body></html>")

    result = run_rgaa(RGAA851(), context)

    assert result.status == Status.FAIL

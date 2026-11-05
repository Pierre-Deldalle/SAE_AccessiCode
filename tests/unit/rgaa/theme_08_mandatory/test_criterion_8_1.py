from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_1 import (
    Test811 as RGAA811,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_1 import (
    Test812 as RGAA812,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_1 import (
    Test813 as RGAA813,
)

# ---------------------------------------------------------------------------
# 8.1.1 : présence du DOCTYPE
# ---------------------------------------------------------------------------


def test_811_doctype_present_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE html><html><body></body></html>")

    result = run_rgaa(RGAA811(), context)

    assert result.status == Status.PASS


def test_811_missing_doctype_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body></body></html>")

    result = run_rgaa(RGAA811(), context)

    assert result.status == Status.FAIL


def test_811_presence_test_does_not_duplicate_validity_test(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE invalid><html><body></body></html>")

    result = run_rgaa(RGAA811(), context)

    assert result.status == Status.PASS


# ---------------------------------------------------------------------------
# 8.1.2 : validité du DOCTYPE
# ---------------------------------------------------------------------------


def test_812_html5_doctype_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE html><html><body></body></html>")

    result = run_rgaa(RGAA812(), context)

    assert result.status == Status.PASS


def test_812_doctype_is_case_insensitive_and_tolerates_whitespace(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!doctype   HTML>\n<html><body></body></html>")

    result = run_rgaa(RGAA812(), context)

    assert result.status == Status.PASS


def test_812_invalid_doctype_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE invalid><html><body></body></html>")

    result = run_rgaa(RGAA812(), context)

    assert result.status == Status.FAIL


def test_812_missing_doctype_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body></body></html>")

    result = run_rgaa(RGAA812(), context)

    assert result.status == Status.FAIL


# ---------------------------------------------------------------------------
# 8.1.3 : emplacement du DOCTYPE
# ---------------------------------------------------------------------------


def test_813_doctype_before_html_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE html><html><body></body></html>")

    result = run_rgaa(RGAA813(), context)

    assert result.status == Status.PASS


def test_813_doctype_after_html_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body></body></html><!DOCTYPE html>")

    result = run_rgaa(RGAA813(), context)

    assert result.status == Status.FAIL


def test_813_missing_doctype_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<html><body></body></html>")

    result = run_rgaa(RGAA813(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_813_doctype_without_html_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory("<!DOCTYPE html><body>Contenu</body>")

    result = run_rgaa(RGAA813(), context)

    assert result.status == Status.NEEDS_REVIEW

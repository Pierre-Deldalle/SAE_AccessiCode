
"""Tests unitaires du critère RGAA 6.2."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_06_links.criterion_6_2 import (
    Test621 as RGAA621,
)


def test_621_no_link_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main><p>Aucun lien.</p></main>"
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_621_text_link_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">Contact</a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_621_empty_link_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


@pytest.mark.parametrize(
    "html",
    [
        '<a href="/contact" aria-label="Contact"></a>',
        '<a href="/contact" title="Contact"></a>',
        '<a href="/contact"><span>Contact</span></a>',
        '<a href="/contact"><img src="contact.png" alt="Contact"></a>',
    ],
)
def test_621_link_with_label_passes(
    context_factory,
    run_rgaa,
    html,
):
    context = context_factory(html)

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_621_valid_aria_labelledby_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span id="label">Contact</span>'
        '<a href="/contact" aria-labelledby="label"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.PASS


def test_621_invalid_aria_labelledby_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact" aria-labelledby="missing"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_621_empty_image_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">'
        '<img src="contact.png" alt="">'
        "</a>"
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL


def test_621_whitespace_only_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">   </a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL


def test_621_position_anchor_is_ignored(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a id="section-contact"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_621_role_link_is_checked(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span role="link" aria-label="Contact"></span>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_621_empty_role_link_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span role="link"></span>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL


def test_621_svg_without_title_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">'
        '<svg><path d="M0 0 L10 10"/></svg>'
        "</a>"
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_621_dynamic_empty_link_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact" data-label="contact"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_621_failure_has_priority_over_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">Contact</a>'
        '<a href="/empty"></a>'
        '<a href="/dynamic" data-label="dynamic"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert result.metadata["links_without_label"] == 1
    assert result.metadata["needs_review"] == 1


def test_621_result_contains_recommendation(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a id="empty-link" href="/contact"></a>'
    )

    result = run_rgaa(RGAA621(), context)

    assert result.status == Status.FAIL
    assert result.findings[0].element == "a#empty-link"
    assert result.findings[0].recommendation is not None

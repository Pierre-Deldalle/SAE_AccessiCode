"""Critère RGAA 8.10 : changements du sens de lecture (contrôle déterministe, sans IA)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_10 import Test8101, Test8102

ARABIC = "مرحبا بكم"
HEBREW = "שלום עולם"


def page(body: str, direction: str = "") -> str:
    attribute = f' dir="{direction}"' if direction else ""
    return f'<html lang="fr"{attribute}><body>{body}</body></html>'


# ---------------------------------------------------------------------------
# 8.10.1
# ---------------------------------------------------------------------------


def test_8101_no_rtl_text_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test8101(), context_factory(page("<p>Bonjour</p>"))).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "body",
    [
        f'<p dir="rtl">{ARABIC}</p>',
        f'<div dir="rtl"><p>{HEBREW}</p></div>',
        f'<p>Bienvenue : <span lang="ar" dir="rtl">{ARABIC}</span></p>',
    ],
)
def test_8101_marked_rtl_text_passes(body, context_factory, run_rgaa):
    assert run_rgaa(Test8101(), context_factory(page(body))).status == Status.PASS


@pytest.mark.parametrize(
    "body",
    [
        f'<p id="ar">{ARABIC}</p>',
        f'<p id="ar" dir="auto">{ARABIC}</p>',
        f'<p id="ar">Bienvenue : {ARABIC}</p>',
    ],
)
def test_8101_unmarked_rtl_text_fails(body, context_factory, run_rgaa):
    result = run_rgaa(Test8101(), context_factory(page(body)))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "p#ar"
    assert 'dir="rtl"' in result.findings[0].message


def test_8101_rtl_page_requires_ltr_marking(context_factory, run_rgaa):
    passage = '<p id="en">Welcome to our website</p>'
    body = f"<p>{ARABIC}</p>\n{passage}"
    result = run_rgaa(Test8101(), context_factory(page(body, "rtl")))
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert finding.element == "p#en"
    assert (finding.line, finding.snippet) == (2, passage)
    assert finding.recommendation.endswith('\nAvant : <p id="en">\nAprès : <p dir="ltr" id="en">')


def test_8101_mixed_text_does_not_set_dir_on_the_whole_paragraph(context_factory, run_rgaa):
    result = run_rgaa(Test8101(), context_factory(page(f"<p>Bienvenue : {ARABIC}</p>")))
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert "Après :" not in finding.recommendation


def test_8101_hidden_text_is_ignored(context_factory, run_rgaa):
    assert run_rgaa(Test8101(), context_factory(page(f"<p hidden>{ARABIC}</p>"))).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 8.10.2
# ---------------------------------------------------------------------------


def test_8102_no_dir_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test8102(), context_factory(page("<p>Texte</p>", "ltr"))).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("value", ["auto", "right", ""])
def test_8102_invalid_value_fails(value, context_factory, run_rgaa):
    passage = f'<p dir="{value}">{ARABIC}</p>'
    result = run_rgaa(Test8102(), context_factory(page(f"\n{passage}")))
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert "n'est pas conforme" in finding.message
    assert (finding.line, finding.snippet) == (2, passage)
    assert finding.recommendation.endswith(f'\nAvant : <p dir="{value}">\nAprès : <p dir="rtl">')


@pytest.mark.parametrize(("value", "text"), [("rtl", ARABIC), ("ltr", "Hello"), ("rtl", HEBREW)])
def test_8102_relevant_value_passes(value, text, context_factory, run_rgaa):
    assert run_rgaa(Test8102(), context_factory(page(f'<p dir="{value}">{text}</p>'))).status == Status.PASS


def test_8102_irrelevant_value_fails(context_factory, run_rgaa):
    opening = '<p dir="rtl">'
    passage = f"{opening}{'Bonjour à tous. ' * 20}</p>"
    result = run_rgaa(Test8102(), context_factory(page(f"\n{passage}")))
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert "ne correspond pas au texte" in finding.message
    assert (finding.line, finding.snippet) == (2, opening)
    assert finding.recommendation.endswith('\nAvant : <p dir="rtl">\nAprès : <p dir="ltr">')


def test_8102_nested_dir_is_judged_separately(context_factory, run_rgaa):
    body = f'<div dir="ltr">Introduction <span dir="rtl">{ARABIC}</span> fin</div>'
    result = run_rgaa(Test8102(), context_factory(page(body)))
    assert result.status == Status.PASS
    assert result.tested_elements == 2


def test_8102_element_without_letters_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test8102(), context_factory(page('<p dir="rtl">2024</p>'))).status == Status.NOT_APPLICABLE

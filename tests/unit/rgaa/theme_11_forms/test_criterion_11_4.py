"""Tests unitaires du critère 11.4, sans navigateur ni Ollama."""
from __future__ import annotations

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_4 import (
    Test1141, Test1142, Test1143,
)


HTML_TEXT = '<label for="email">Courriel</label><input id="email" type="email">'
HTML_CHOICE = '<label for="agree">Accepter</label><input id="agree" type="checkbox">'


def run_with_layout(context_factory, run_rgaa, test, html, record, identifier="input#email"):
    context = context_factory(html)
    if record is not None:
        context.form_label_layout = {identifier: record}
    return run_rgaa(test, context)


def proof(*, adjacent=True, position="above", direction="ltr", label_text=None, **extra):
    result = {
        "verified": True, "source": "browser", "adjacent": adjacent,
        "position": position, "direction": direction,
    }
    if label_text is not None:
        result["label_text"] = label_text
    result.update(extra)
    return result


@pytest.mark.parametrize("test", [Test1141(), Test1142()])
def test_no_fields_not_applicable(context_factory, run_rgaa, test):
    result = run_rgaa(test, context_factory("<p>Bonjour</p>"))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1143_no_choice_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test1143(), context_factory(HTML_TEXT))
    assert result.status == Status.NOT_APPLICABLE


def test_1142_only_choices_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test1142(), context_factory(HTML_CHOICE))
    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("test,html,key", [
    (Test1141(), HTML_TEXT, "input#email"),
    (Test1142(), HTML_TEXT, "input#email"),
    (Test1143(), HTML_CHOICE, "input#agree"),
])
def test_without_visual_evidence_needs_review(context_factory, run_rgaa, test, html, key):
    result = run_with_layout(context_factory, run_rgaa, test, html, None, key)
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].element == key
    assert result.findings[0].message
    assert result.findings[0].recommendation


@pytest.mark.parametrize("test,html,key", [
    (Test1141(), HTML_TEXT, "input#email"),
    (Test1142(), HTML_TEXT, "input#email"),
    (Test1143(), HTML_CHOICE, "input#agree"),
])
def test_confirmed_non_adjacent_fail(context_factory, run_rgaa, test, html, key):
    result = run_with_layout(
        context_factory, run_rgaa, test, html,
        proof(adjacent=False, position="right"), key,
    )
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["adjacent"] is False
    assert result.findings[0].recommendation


def test_1141_verified_adjacency_pass(context_factory, run_rgaa):
    result = run_with_layout(context_factory, run_rgaa, Test1141(), HTML_TEXT, proof())
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert not result.findings


@pytest.mark.parametrize("position,direction", [
    ("above", "ltr"), ("left", "ltr"), ("above", "rtl"), ("right", "rtl"),
])
def test_1142_allowed_positions(context_factory, run_rgaa, position, direction):
    result = run_with_layout(
        context_factory, run_rgaa, Test1142(), HTML_TEXT,
        proof(position=position, direction=direction),
    )
    assert result.status == Status.PASS


@pytest.mark.parametrize("position,direction", [
    ("right", "ltr"), ("below", "ltr"), ("left", "rtl"), ("below", "rtl"),
])
def test_1142_disallowed_positions(context_factory, run_rgaa, position, direction):
    result = run_with_layout(
        context_factory, run_rgaa, Test1142(), HTML_TEXT,
        proof(position=position, direction=direction),
    )
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["position"] == position


@pytest.mark.parametrize("position,direction", [
    ("below", "ltr"), ("right", "ltr"), ("below", "rtl"), ("left", "rtl"),
])
def test_1143_allowed_positions(context_factory, run_rgaa, position, direction):
    result = run_with_layout(
        context_factory, run_rgaa, Test1143(), HTML_CHOICE,
        proof(position=position, direction=direction), "input#agree",
    )
    assert result.status == Status.PASS


@pytest.mark.parametrize("position,direction", [
    ("left", "ltr"), ("above", "ltr"), ("right", "rtl"), ("above", "rtl"),
])
def test_1143_disallowed_positions(context_factory, run_rgaa, position, direction):
    result = run_with_layout(
        context_factory, run_rgaa, Test1143(), HTML_CHOICE,
        proof(position=position, direction=direction), "input#agree",
    )
    assert result.status == Status.FAIL


@pytest.mark.parametrize("role", ["checkbox", "radio", "switch"])
def test_1143_aria_roles(context_factory, run_rgaa, role):
    html = f'<span id="l">Choix</span><div id="c" role="{role}" aria-labelledby="l" tabindex="0"></div>'
    result = run_with_layout(
        context_factory, run_rgaa, Test1143(), html,
        proof(position="right"), "div#c",
    )
    assert result.status == Status.PASS


@pytest.mark.parametrize("type_", ["checkbox", "radio"])
def test_1142_excludes_native_choices(context_factory, run_rgaa, type_):
    html = f'<label for="x">Choix</label><input id="x" type="{type_}">'
    result = run_rgaa(Test1142(), context_factory(html))
    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("exception", [
    "mixed_label_directions", "mixed_form_directions",
    "nonstandard_choice_appearance", "legitimate_alternative_placement",
])
def test_1143_verified_exception_not_applicable(context_factory, run_rgaa, exception):
    result = run_with_layout(
        context_factory, run_rgaa, Test1143(), HTML_CHOICE,
        proof(exception=exception, exception_verified=True), "input#agree",
    )
    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["verified_exceptions"] == 1


def test_1142_unverified_exception_review(context_factory, run_rgaa):
    result = run_with_layout(
        context_factory, run_rgaa, Test1142(), HTML_TEXT,
        proof(exception="legitimate_alternative_placement", exception_verified=False),
    )
    assert result.status == Status.NEEDS_REVIEW


def test_1141_exception_does_not_override_adjacency(context_factory, run_rgaa):
    result = run_with_layout(
        context_factory, run_rgaa, Test1141(), HTML_TEXT,
        proof(adjacent=False, exception="legitimate_alternative_placement", exception_verified=True),
    )
    assert result.status == Status.FAIL


@pytest.mark.parametrize("change", [
    {"verified": False}, {"source": "unknown"}, {"label_text": "Autre"},
])
def test_invalid_or_stale_proof_review(context_factory, run_rgaa, change):
    record = proof(label_text="Courriel")
    record.update(change)
    result = run_with_layout(context_factory, run_rgaa, Test1142(), HTML_TEXT, record)
    assert result.status == Status.NEEDS_REVIEW


def test_missing_adjacent_review(context_factory, run_rgaa):
    record = proof()
    del record["adjacent"]
    result = run_with_layout(context_factory, run_rgaa, Test1141(), HTML_TEXT, record)
    assert result.status == Status.NEEDS_REVIEW


@pytest.mark.parametrize("position,direction", [
    ("diagonal", "ltr"), ("above", "unknown"),
])
def test_missing_position_or_direction_review(context_factory, run_rgaa, position, direction):
    result = run_with_layout(
        context_factory, run_rgaa, Test1142(), HTML_TEXT,
        proof(position=position, direction=direction),
    )
    assert result.status == Status.NEEDS_REVIEW


def test_aria_label_without_visible_label_review(context_factory, run_rgaa):
    html = '<input id="email" aria-label="Courriel">'
    result = run_with_layout(context_factory, run_rgaa, Test1141(), html, proof())
    assert result.status == Status.NEEDS_REVIEW


def test_title_without_visible_label_review(context_factory, run_rgaa):
    html = '<input id="email" title="Courriel">'
    result = run_rgaa(Test1141(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW


def test_wrapping_label_supported(context_factory, run_rgaa):
    html = '<label>Courriel <input id="email"></label>'
    result = run_with_layout(context_factory, run_rgaa, Test1141(), html, proof())
    assert result.status == Status.PASS


def test_aria_labelledby_supported(context_factory, run_rgaa):
    html = '<span id="l">Courriel</span><input id="email" aria-labelledby="l">'
    result = run_with_layout(context_factory, run_rgaa, Test1141(), html, proof())
    assert result.status == Status.PASS


def test_duplicate_aria_labelledby_id_review(context_factory, run_rgaa):
    html = '<span id="l">Courriel</span><span id="l">Email</span><input id="email" aria-labelledby="l">'
    result = run_with_layout(context_factory, run_rgaa, Test1141(), html, proof())
    assert result.status == Status.NEEDS_REVIEW


def test_fail_priority_over_review(context_factory, run_rgaa):
    html = '''
    <label for="a">A</label><input id="a">
    <label for="b">B</label><input id="b">
    '''
    context = context_factory(html)
    context.form_label_layout = {"input#a": proof(adjacent=False)}
    result = run_rgaa(Test1141(), context)
    assert result.status == Status.FAIL
    assert result.metadata["failed_fields"] == 1
    assert result.metadata["review_fields"] == 1
    assert result.tested_elements == 2


def test_review_priority_over_pass(context_factory, run_rgaa):
    html = '''
    <label for="a">A</label><input id="a">
    <label for="b">B</label><input id="b">
    '''
    context = context_factory(html)
    context.form_label_layout = {"input#a": proof()}
    result = run_rgaa(Test1141(), context)
    assert result.status == Status.NEEDS_REVIEW


def test_hidden_input_not_in_scope(context_factory, run_rgaa):
    html = '<input type="hidden" id="secret">'
    result = run_rgaa(Test1141(), context_factory(html))
    assert result.status == Status.NOT_APPLICABLE


def test_nonstandard_aria_role_without_exception_review(context_factory, run_rgaa):
    html = '<label for="x">Option</label><div role="switch" id="x"></div>'
    result = run_rgaa(Test1143(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW


def test_duplicate_field_id_needs_review(context_factory, run_rgaa):
    html = '<label for="x">Un</label><input id="x"><input id="x">'
    context = context_factory(html)
    context.form_label_layout = {"input#x": proof()}
    result = run_rgaa(Test1141(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["review_fields"] == 2


def test_nonadjacent_without_direction_still_fail(context_factory, run_rgaa):
    record = proof(adjacent=False)
    del record["position"]
    del record["direction"]
    result = run_with_layout(context_factory, run_rgaa, Test1142(), HTML_TEXT, record)
    assert result.status == Status.FAIL


def test_nonstandard_choice_exception_not_for_standard(context_factory, run_rgaa):
    record = proof(exception="nonstandard_choice_appearance", exception_verified=True)
    result = run_with_layout(context_factory, run_rgaa, Test1142(), HTML_TEXT, record)
    assert result.status == Status.NEEDS_REVIEW

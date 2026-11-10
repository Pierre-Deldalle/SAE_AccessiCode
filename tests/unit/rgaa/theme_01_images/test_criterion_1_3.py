"""Non-régressions du critère RGAA 1.3."""
import pytest
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_3 import (
    Test131,
    Test132,
    Test133,
    Test134,
    Test135,
    Test136,
    Test137,
    Test138,
    Test139,
)

@pytest.mark.parametrize("cls", [
    Test131,
    Test132,
    Test133,
    Test134,
    Test135,
    Test136,
    Test137,
    Test138,
    Test139,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_semantic_requires_verified_evidence(context_factory, run_rgaa):
    html='<img id="logo" alt="Logo AccessiCode" src="logo.png">'
    assert run_rgaa(Test131(), context_factory(html)).status == Status.NEEDS_REVIEW
    ctx=context_factory(html, **{'img#logo': {'verified':True,'alternative_relevant':True}})
    assert run_rgaa(Test131(), ctx).status == Status.PASS

def test_unverified_proof_cannot_force_pass(context_factory, run_rgaa):
    html='<img id="logo" alt="Logo" src="logo.png">'
    ctx=context_factory(html, **{'img#logo': {'alternative_relevant':True}})
    assert run_rgaa(Test131(), ctx).status == Status.NEEDS_REVIEW

def test_area_title_semantics_are_checked(context_factory, run_rgaa):
    html='<area id="z" href="/x" title="Consulter">'
    assert run_rgaa(Test132(), context_factory(html)).status == Status.NEEDS_REVIEW
    ctx=context_factory(html, **{'area#z': {'verified':True, 'alternative_relevant':True}})
    assert run_rgaa(Test132(), ctx).status == Status.PASS

def test_canvas_fallback_requires_assistive_technology_check(context_factory, run_rgaa):
    assert run_rgaa(Test138(), context_factory('<canvas>Résultats</canvas>')).status == Status.NEEDS_REVIEW

def test_conciseness_requires_verified_proof(context_factory, run_rgaa):
    html='<img id="i" alt="Photo de la façade">'
    assert run_rgaa(Test139(), context_factory(html)).status == Status.NEEDS_REVIEW
    ctx=context_factory(html, **{'img#i': {'verified':True, 'concise':True}})
    assert run_rgaa(Test139(), ctx).status == Status.PASS

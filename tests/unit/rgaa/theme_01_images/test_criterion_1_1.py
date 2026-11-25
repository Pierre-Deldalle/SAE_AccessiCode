"""Critère RGAA 1.1 : présence d'une alternative textuelle."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111,
    Test112,
    Test113,
    Test114,
    Test115,
    Test116,
    Test117,
    Test118,
)
from tests.unit.rgaa.theme_01_images.image_fakes import profile, services

ALL = [Test111, Test112, Test113, Test114, Test115, Test116, Test117, Test118]


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


# ---- 1.1.1 -----------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        '<img src="a.png" alt="Logo">',
        '<img src="a.png" title="Logo">',
        '<img src="a.png" aria-label="Logo">',
        '<p id="l">Logo</p><img src="a.png" aria-labelledby="l">',
        '<div role="img" aria-label="Carte"></div>',
    ],
)
def test_111_alternative_passes_without_ai_call(html, context_factory, run_rgaa):
    ai = services()
    assert run_rgaa(Test111(), context_factory(html), ai).status == Status.PASS
    ai.image_analyzer.profile.assert_not_called()
    ai.image_analyzer.profile_element.assert_not_called()


def test_111_role_img_title_is_not_an_allowed_alternative(context_factory, run_rgaa):
    result = run_rgaa(Test111(), context_factory('<div role="img" title="Carte"></div>'), services())
    assert result.status == Status.FAIL


def test_111_informative_image_without_alternative_fails(context_factory, run_rgaa):
    result = run_rgaa(Test111(), context_factory('<img src="graph.png">'), services())
    assert result.status == Status.FAIL
    assert result.findings[0].element == "img[0]"


def test_111_decorative_image_without_alternative_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=False))
    assert run_rgaa(Test111(), context_factory('<img src="deco.png">'), ai).status == Status.NOT_APPLICABLE


def test_111_functional_image_fails_without_ai(context_factory, run_rgaa):
    result = run_rgaa(Test111(), context_factory('<a href="/">\n  <img src="home.png">\n</a>'))
    assert result.status == Status.FAIL
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == '<img src="home.png">'
    assert "Avant :" not in result.findings[0].recommendation


def test_111_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=True, confidence="low"))
    assert run_rgaa(Test111(), context_factory('<img src="x.png">'), ai).status == Status.NEEDS_REVIEW


def test_111_unknown_role_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=None))
    assert run_rgaa(Test111(), context_factory('<img src="x.png">'), ai).status == Status.NEEDS_REVIEW


def test_111_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test111(), context_factory('<img src="x.png">'))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_111_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(image_profile=RuntimeError("Ollama indisponible"))
    assert run_rgaa(Test111(), context_factory('<img src="x.png">'), ai).status == Status.ERROR


def test_111_uses_vlm_profile_when_file_exists(context_factory, run_rgaa):
    ai = services()
    run_rgaa(Test111(), context_factory('<img src="photo.png">'), ai)
    ai.image_analyzer.profile.assert_awaited_once()
    ai.image_analyzer.profile_element.assert_not_called()


def test_111_verified_evidence_has_priority(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=True))
    context = context_factory(
        '<img id="deco" src="x.png">', image_evidence={"img#deco": {"verified": True, "information_bearing": False}}
    )
    assert run_rgaa(Test111(), context, ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.profile.assert_not_called()


def test_111_mixed_results_fail_wins(context_factory, run_rgaa):
    html = '<img src="a.png" alt="A"><img src="b.png">'
    result = run_rgaa(Test111(), context_factory(html), services())
    assert result.status == Status.FAIL
    assert result.metadata["statuses"]["pass"] == 1
    assert result.metadata["statuses"]["fail"] == 1


# ---- 1.1.2 / 1.1.3 ---------------------------------------------------


def test_112_area_with_alt_passes(context_factory, run_rgaa):
    html = '<map name="m"><area href="/a" alt="Accueil"></map><img src="m.png" usemap="#m" alt="Plan">'
    assert run_rgaa(Test112(), context_factory(html), services()).status == Status.PASS


def test_112_clickable_area_without_alt_fails(context_factory, run_rgaa):
    assert run_rgaa(Test112(), context_factory('<map><area href="/a"></map>')).status == Status.FAIL


def test_112_area_without_href_is_out_of_scope(context_factory, run_rgaa):
    assert run_rgaa(Test112(), context_factory("<map><area></map>")).status == Status.NOT_APPLICABLE


def test_113_image_button(context_factory, run_rgaa):
    assert run_rgaa(Test113(), context_factory('<input type="image" src="ok.png" alt="Envoyer">')).status == Status.PASS
    assert run_rgaa(Test113(), context_factory('<input type="image" src="ok.png">')).status == Status.FAIL


# ---- 1.1.4 -----------------------------------------------------------


def test_114_server_side_map_without_other_links_fails(context_factory, run_rgaa):
    html = '<a href="/map.cgi"><img src="m.png" alt="Plan" ismap></a>'
    assert run_rgaa(Test114(), context_factory(html)).status == Status.FAIL


def test_114_server_side_map_with_links_needs_review(context_factory, run_rgaa):
    html = '<a href="/map.cgi"><img src="m.png" alt="Plan" ismap></a><a href="/nord">Nord</a>'
    assert run_rgaa(Test114(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_114_documented_evidence(context_factory, run_rgaa):
    html = '<a href="/map.cgi"><img id="m" src="m.png" alt="Plan" ismap></a><a href="/nord">Nord</a>'
    context = context_factory(html, image_evidence={"img#m": {"verified": True, "equivalent_destinations": True}})
    assert run_rgaa(Test114(), context).status == Status.PASS


# ---- 1.1.5 -----------------------------------------------------------


def test_115_svg_with_role_and_title_passes(context_factory, run_rgaa):
    html = '<svg role="img"><title>Graphique des ventes</title></svg>'
    assert run_rgaa(Test115(), context_factory(html), services()).status == Status.PASS


def test_115_svg_with_title_but_without_role_fails(context_factory, run_rgaa):
    result = run_rgaa(Test115(), context_factory("<svg><title>Ventes</title></svg>"), services())
    assert result.status == Status.FAIL
    assert 'role="img"' in result.findings[0].message
    assert 'Avant : <svg>\nAprès : <svg role="img">' in result.findings[0].recommendation


def test_115_hidden_svg_is_not_applicable(context_factory, run_rgaa):
    ai = services()
    assert run_rgaa(Test115(), context_factory('<svg aria-hidden="true"></svg>'), ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.profile_element.assert_not_called()


def test_115_decorative_svg_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=False))
    assert run_rgaa(Test115(), context_factory("<svg><path/></svg>"), ai).status == Status.NOT_APPLICABLE


# ---- 1.1.6 à 1.1.8 ---------------------------------------------------


def test_116_object_with_role_and_label_passes(context_factory, run_rgaa):
    html = '<object type="image/png" data="a.png" role="img" aria-label="Plan"></object>'
    assert run_rgaa(Test116(), context_factory(html), services()).status == Status.PASS


def test_116_object_with_adjacent_link_passes(context_factory, run_rgaa):
    html = '<div><object type="image/png" data="a.png"></object><a href="plan.html">Version texte</a></div>'
    assert run_rgaa(Test116(), context_factory(html), services()).status == Status.PASS


def test_116_object_label_without_role_fails(context_factory, run_rgaa):
    html = '<object type="image/png" data="a.png" aria-label="Plan"></object>'
    assert run_rgaa(Test116(), context_factory(html), services()).status == Status.FAIL


def test_116_non_image_object_is_out_of_scope(context_factory, run_rgaa):
    html = '<object type="application/pdf" data="a.pdf"></object>'
    assert run_rgaa(Test116(), context_factory(html), services()).status == Status.NOT_APPLICABLE


def test_117_embed(context_factory, run_rgaa):
    ok = '<embed type="image/svg+xml" src="a.svg" role="img" aria-label="Schéma">'
    ko = '<embed type="image/svg+xml" src="a.svg">'
    assert run_rgaa(Test117(), context_factory(ok), services()).status == Status.PASS
    assert run_rgaa(Test117(), context_factory(ko), services()).status == Status.FAIL


def test_118_canvas_fallback_content_passes(context_factory, run_rgaa):
    html = "<canvas>Ventes 2025 : hausse de 10 %</canvas>"
    assert run_rgaa(Test118(), context_factory(html), services()).status == Status.PASS


def test_118_canvas_role_img_requires_aria_label(context_factory, run_rgaa):
    ok = '<canvas role="img" aria-label="Ventes"></canvas>'
    ko = '<canvas role="img">Ventes</canvas>'
    assert run_rgaa(Test118(), context_factory(ok), services()).status == Status.PASS
    assert run_rgaa(Test118(), context_factory(ko), services()).status == Status.FAIL

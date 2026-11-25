"""Critère RGAA 1.7 : pertinence des descriptions détaillées."""

import asyncio

import pytest

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.registry import TestRegistry as Registry
from accessi_code.rgaa.runner import TestRunner as Runner
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import (
    Test171,
    Test172,
    Test173,
    Test174,
    Test175,
    Test176,
)
from tests.unit.rgaa.theme_01_images.image_fakes import description, services

ALL = [Test171, Test172, Test173, Test174, Test175, Test176]
WITH_DESCRIPTION = '<img src="g.png" alt="Ventes" aria-describedby="d">\n<p id="d">Les ventes ont doublé en 2025.</p>'


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


def test_171_relevant_description_passes(context_factory, run_rgaa):
    ai = services(description_analysis=description(relevant=True))
    assert run_rgaa(Test171(), context_factory(WITH_DESCRIPTION), ai).status == Status.PASS
    image_info, detailed = ai.image_analyzer.analyze.await_args.args
    assert detailed.content == "Les ventes ont doublé en 2025."
    assert image_info.src == "g.png"


def test_171_irrelevant_description_fails(context_factory, run_rgaa):
    ai = services(
        description_analysis=description(relevant=False, suggestion="Les ventes ont augmenté de 10 % en 2025.")
    )
    result = run_rgaa(Test171(), context_factory(WITH_DESCRIPTION), ai)

    assert result.status == Status.FAIL
    assert "Proposition : « Les ventes ont augmenté de 10 % en 2025. »." in result.findings[0].recommendation
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == '<p id="d">Les ventes ont doublé en 2025.</p>'


def test_171_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(description_analysis=description(relevant=False, confidence="low"))
    assert run_rgaa(Test171(), context_factory(WITH_DESCRIPTION), ai).status == Status.NEEDS_REVIEW


def test_171_not_a_detailed_description_is_not_applicable(context_factory, run_rgaa):
    ai = services(description_analysis=description(relevant=None, detailed=False))
    assert run_rgaa(Test171(), context_factory(WITH_DESCRIPTION), ai).status == Status.NOT_APPLICABLE


def test_171_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test171(), context_factory(WITH_DESCRIPTION)).status == Status.NEEDS_REVIEW


def test_171_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(description_analysis=RuntimeError("panne"))
    assert run_rgaa(Test171(), context_factory(WITH_DESCRIPTION), ai).status == Status.ERROR


def test_171_longdesc_is_loaded_from_local_file(context_factory, run_rgaa):
    ai = services()
    context = context_factory(
        '<img src="g.png" alt="Ventes" longdesc="desc.txt">',
        resources={"desc.txt": "Description complète des ventes."},
    )
    assert run_rgaa(Test171(), context, ai).status == Status.PASS
    assert ai.image_analyzer.analyze.await_args.args[1].content == "Description complète des ventes."


@pytest.mark.parametrize(
    ("relative", "fragment", "content", "snippet", "adjacent"),
    [
        (
            "pages/ventes.html",
            "#details",
            '<h1>Ventes</h1>\n<p>Introduction</p>\n<p id="details">Description des ventes.</p>',
            '<p id="details">Description des ventes.</p>',
            False,
        ),
        (
            "pages/ventes.html",
            "#details",
            '<h1>Ventes</h1>\n<p>Introduction</p>\n<p id="details">Description des ventes.</p>',
            '<p id="details">Description des ventes.</p>',
            True,
        ),
        ("pages/ventes.txt", "", "\n\nDescription des ventes.", None, False),
    ],
)
def test_171_external_description_keeps_its_own_file_and_line(tmp_path, relative, fragment, content, snippet, adjacent):
    site = tmp_path / "site"
    description_path = site / relative
    description_path.parent.mkdir(parents=True)
    description_path.write_text(content, encoding="utf-8")
    image_path = site / "g.png"
    image_path.write_bytes(b"image-test")
    page = site / "index.html"
    reference = relative + fragment
    image = '<img src="g.png" alt="Ventes"'
    if adjacent:
        image += f'><a href="{reference}">Description détaillée</a>'
    else:
        image += f' longdesc="{reference}">'
    page.write_text(f"<h1>Ventes</h1>\n{image}", encoding="utf-8")
    context = AuditContextBuilder(tmp_path / "workspace").build(
        [page, image_path, description_path],
        site_root=site,
    )
    runner = Runner(Registry([Test171()]), services=services(description_analysis=description(relevant=False)))

    [result] = asyncio.run(runner.run_all(context))

    assert result.status == Status.FAIL
    [finding] = result.findings
    assert (finding.file, finding.line, finding.snippet) == (relative, 3, snippet)


def test_171_external_html_without_dom_keeps_unknown_line(context_factory, run_rgaa):
    context = context_factory(
        '<img src="g.png" alt="Ventes" longdesc="ventes.html">',
        resources={"ventes.html": "<p>Description des ventes.</p>"},
    )

    result = run_rgaa(Test171(), context, services(description_analysis=description(relevant=False)))

    assert result.status == Status.FAIL
    [finding] = result.findings
    assert (finding.file, finding.line, finding.snippet) == ("ventes.html", None, None)


def test_171_unreadable_description_needs_review(context_factory, run_rgaa):
    ai = services()
    result = run_rgaa(Test171(), context_factory('<img src="g.png" alt="Ventes" longdesc="absent.txt">'), ai)
    assert result.status == Status.NEEDS_REVIEW
    ai.image_analyzer.analyze.assert_not_called()


def test_175_svg_without_image_file_needs_review(context_factory, run_rgaa):
    ai = services()
    html = '<svg role="img" aria-label="Ventes" aria-describedby="d"></svg><p id="d">Hausse.</p>'
    result = run_rgaa(Test175(), context_factory(html), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert "pas analysable" in result.findings[0].message
    ai.image_analyzer.analyze.assert_not_called()

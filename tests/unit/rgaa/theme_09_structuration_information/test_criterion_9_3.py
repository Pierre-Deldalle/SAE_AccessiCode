"""Critère RGAA 9.3 : listes."""

import pytest
from ai_fakes import structure, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_3 import Test931, Test932, Test933

BULLETS = "<p>- Audit<br>- Formation<br>- Conseil</p>"
NUMBERS = "<p>1. Importer<br>2. Analyser<br>3. Corriger</p>"


@pytest.mark.parametrize("cls", [Test931, Test932, Test933])
def test_no_list_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_931_well_formed_list_passes(context_factory, run_rgaa):
    assert run_rgaa(Test931(), context_factory("<ul><li>A</li><li>B</li></ul>"), text_services()).status == Status.PASS


@pytest.mark.parametrize("html", ["<ul></ul>", "<ul><div>A</div></ul>", '<div role="list"><span>A</span></div>'])
def test_931_badly_structured_list_fails(html, context_factory, run_rgaa):
    assert run_rgaa(Test931(), context_factory(html), text_services()).status == Status.FAIL


def test_931_aria_list_passes(context_factory, run_rgaa):
    html = '<div role="list"><div role="listitem">A</div><div role="listitem">B</div></div>'
    assert run_rgaa(Test931(), context_factory(html), text_services()).status == Status.PASS


def test_931_visual_list_confirmed_by_ai_fails(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(Test931(), context_factory(BULLETS), ai)
    assert result.status == Status.FAIL
    kind, items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "list"
    assert items[0].text.splitlines() == ["- Audit", "- Formation", "- Conseil"]


def test_931_dashes_that_are_not_a_list(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(False))
    assert run_rgaa(Test931(), context_factory(BULLETS), ai).status == Status.NOT_APPLICABLE


def test_931_consecutive_bullet_paragraphs(context_factory, run_rgaa):
    ai = text_services()
    html = "<p>• Audit</p><p>• Formation</p>"
    assert run_rgaa(Test931(), context_factory(html), ai).status == Status.FAIL
    assert len(ai.structure_analyzer.classify_candidates.call_args.args[1]) == 1


def test_931_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(structure_answer=structure(True, confidence="low"))
    assert run_rgaa(Test931(), context_factory(BULLETS), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test931(), context_factory(BULLETS)).status == Status.NEEDS_REVIEW
    broken = text_services(structure_answer=RuntimeError("panne"))
    assert run_rgaa(Test931(), context_factory(BULLETS), broken).status == Status.ERROR


def test_932_ordered_lists(context_factory, run_rgaa):
    assert run_rgaa(Test932(), context_factory("<ol><li>A</li></ol>"), text_services()).status == Status.PASS
    assert run_rgaa(Test932(), context_factory(NUMBERS), text_services()).status == Status.FAIL


def test_932_numbered_aria_list(context_factory, run_rgaa):
    html = '<div role="list"><div role="listitem">1. A</div><div role="listitem">2. B</div></div>'
    assert run_rgaa(Test932(), context_factory(html), text_services()).status == Status.PASS
    assert run_rgaa(Test931(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_933_description_lists(context_factory, run_rgaa):
    ok = "<dl><dt>RGAA</dt><dd>Référentiel</dd></dl>"
    grouped = "<dl><div><dt>RGAA</dt><dd>Référentiel</dd></div></dl>"
    only_terms = "<dl><dt>RGAA</dt></dl>"
    assert run_rgaa(Test933(), context_factory(ok), text_services()).status == Status.PASS
    assert run_rgaa(Test933(), context_factory(grouped), text_services()).status == Status.PASS
    assert run_rgaa(Test933(), context_factory(only_terms), text_services()).status == Status.FAIL


def test_hidden_list_is_ignored(context_factory, run_rgaa):
    assert run_rgaa(Test931(), context_factory("<ul hidden></ul>"), text_services()).status == Status.NOT_APPLICABLE


# ---- Emplacement des observations ------------------------------------


def test_931_badly_structured_list_is_located(context_factory, run_rgaa):
    html = '<p>Menu</p>\n<ul class="services"><div>A</div></ul>'
    finding = run_rgaa(Test931(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<ul class="services"><div>A</div></ul>')


def test_931_visual_list_is_located(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    finding = run_rgaa(Test931(), context_factory("<h1>Offres</h1>\n" + BULLETS), ai).findings[0]
    # BeautifulSoup sérialise les éléments vides sous la forme <br/>.
    assert (finding.line, finding.snippet) == (2, BULLETS.replace("<br>", "<br/>"))


def test_932_visual_ordered_list_is_located(context_factory, run_rgaa):
    finding = run_rgaa(Test932(), context_factory("<h1>Étapes</h1>\n" + NUMBERS), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, NUMBERS.replace("<br>", "<br/>"))


def test_933_description_list_is_located(context_factory, run_rgaa):
    html = "<p>Glossaire</p>\n<dl><dt>RGAA</dt></dl>"
    finding = run_rgaa(Test933(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, "<dl><dt>RGAA</dt></dl>")


# ---- Corrections proposées -------------------------------------------


@pytest.mark.parametrize(
    ("html", "example"),
    [
        ('<ul><div class="i">A</div></ul>', '<div class="i">A</div> → <li class="i">A</li>'),
        ('<ul><li>A</li><a href="/b">B</a></ul>', '<a href="/b">B</a> → <li><a href="/b">B</a></li>'),
        ('<div role="list"><span>A</span></div>', '<span>A</span> → <span role="listitem">A</span>'),
    ],
)
def test_931_badly_structured_list_example(html, example, context_factory, run_rgaa):
    finding = run_rgaa(Test931(), context_factory(html), text_services()).findings[0]
    assert finding.recommendation.endswith(f"Exemple : {example}")


@pytest.mark.parametrize("html", ["<ul></ul>", "<dl><dt>RGAA</dt></dl>"])
def test_no_example_when_the_fix_depends_on_content(html, context_factory, run_rgaa):
    cls = Test933 if html.startswith("<dl") else Test931
    finding = run_rgaa(cls(), context_factory(html), text_services()).findings[0]
    assert "Exemple" not in finding.recommendation


def test_931_visual_list_example_uses_its_items(context_factory, run_rgaa):
    html = "<p>- Audit<br>- Formation<br>- Conseil<br>- Suivi</p>"
    finding = run_rgaa(Test931(), context_factory(html), text_services(structure_answer=structure(True))).findings[0]
    assert finding.recommendation == (
        'Baliser la liste avec <ul> et <li> (ou role="list" et role="listitem"). '
        "Exemple : <p>- Audit<br/>- Formation<br/>- Conseil<br/>- Suivi</p> → "
        "<ul><li>Audit</li><li>Formation</li><li>Conseil</li><li>…</li></ul>"
    )


def test_931_paragraph_series_example(context_factory, run_rgaa):
    finding = run_rgaa(Test931(), context_factory("<p>• Audit</p><p>• Formation</p>"), text_services()).findings[0]
    assert finding.recommendation.endswith("Exemple : <p>• Audit</p> … → <ul><li>Audit</li><li>Formation</li></ul>")


def test_932_visual_ordered_list_example(context_factory, run_rgaa):
    finding = run_rgaa(Test932(), context_factory(NUMBERS), text_services()).findings[0]
    assert finding.recommendation.endswith("→ <ol><li>Importer</li><li>Analyser</li><li>Corriger</li></ol>")


def test_no_example_for_an_uncertain_visual_list(context_factory, run_rgaa):
    finding = run_rgaa(Test931(), context_factory(BULLETS)).findings[0]
    assert "Exemple" not in finding.recommendation

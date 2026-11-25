"""Critère RGAA 9.1 : titres."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_1 import Test911, Test912, Test913
from tests.ai_fakes import relevance, structure, text_services

GOOD = "<h1>Accueil</h1><h2>Services</h2><p>Texte</p><h3>Audit</h3><h2>Contact</h2>"
JUMP = "<h1>Accueil</h1><h2>Offres</h2><h4>Tarifs</h4><p>10 €</p>"


@pytest.mark.parametrize("cls", [Test911, Test912, Test913])
def test_no_heading_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


# ---- 9.1.1 -----------------------------------------------------------


def test_911_hierarchy_without_jump_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(Test911(), context_factory(GOOD), ai).status == Status.PASS
    ai.structure_analyzer.analyze_heading_hierarchy.assert_not_called()


def test_911_jump_judged_relevant_passes(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(True))
    assert run_rgaa(Test911(), context_factory(JUMP), ai).status == Status.PASS
    outline, remarks = ai.structure_analyzer.analyze_heading_hierarchy.call_args.args
    assert outline == [(1, "Accueil"), (2, "Offres"), (4, "Tarifs")]
    assert remarks == ["h2 → h4 : « Tarifs »"]


def test_911_jump_judged_irrelevant_fails(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(False, problems=["h4 – Tarifs : rattaché à aucun h3"]))
    result = run_rgaa(Test911(), context_factory(JUMP), ai)
    assert result.status == Status.FAIL
    assert "rattaché à aucun h3" in result.findings[0].message


def test_911_first_heading_not_level_one_is_a_remark(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(True))
    run_rgaa(Test911(), context_factory("<h2>Actualités</h2><h3>Brève</h3>"), ai)
    _, remarks = ai.structure_analyzer.analyze_heading_hierarchy.call_args.args
    assert "le premier titre est de niveau 2" in remarks[0]


def test_911_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test911(), context_factory(JUMP), ai).status == Status.NEEDS_REVIEW


def test_911_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test911(), context_factory(JUMP)).status == Status.NEEDS_REVIEW


def test_911_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=RuntimeError("panne"))
    assert run_rgaa(Test911(), context_factory(JUMP), ai).status == Status.ERROR


def test_911_hidden_and_aria_headings(context_factory, run_rgaa):
    html = '<h1>A</h1><h3 hidden>Masqué</h3><div role="heading" aria-level="2">B</div>'
    assert run_rgaa(Test911(), context_factory(html), text_services()).status == Status.PASS


# ---- 9.1.2 -----------------------------------------------------------


def test_912_relevant_headings_pass(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test912(), context_factory(GOOD), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "heading"
    assert [item.text for item in items] == ["Accueil", "Services", "Audit", "Contact"]
    assert "Texte" in items[1].context


def test_912_irrelevant_heading_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=[relevance(True), relevance(False)])
    result = run_rgaa(Test912(), context_factory("<h1>Accueil</h1><h2>Titre</h2><p>Nos horaires</p>"), ai)
    assert result.status == Status.FAIL
    assert "« Titre »" in result.findings[0].message


def test_912_empty_heading_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test912(), context_factory("<h1></h1>"), ai)
    assert result.status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_912_heading_with_only_an_image_uses_its_alt(context_factory, run_rgaa):
    ai = text_services()
    assert (
        run_rgaa(Test912(), context_factory('<h1><img src="l.png" alt="AccessiCode"></h1>'), ai).status == Status.PASS
    )


def test_912_low_confidence_and_no_ai(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test912(), context_factory(GOOD), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test912(), context_factory(GOOD)).status == Status.NEEDS_REVIEW


def test_912_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test912(), context_factory(GOOD), ai).status == Status.ERROR


# ---- 9.1.3 -----------------------------------------------------------


def test_913_marked_headings_pass(context_factory, run_rgaa):
    assert run_rgaa(Test913(), context_factory(GOOD), text_services()).status == Status.PASS


def test_913_aria_heading_without_level_fails(context_factory, run_rgaa):
    result = run_rgaa(Test913(), context_factory('<div role="heading">Contact</div>'), text_services())
    assert result.status == Status.FAIL
    assert "aria-level" in result.findings[0].message


def test_913_bold_paragraph_confirmed_as_heading_fails(context_factory, run_rgaa):
    html = "<h1>Accueil</h1><p><strong>Nos services</strong></p><p>Nous proposons des audits.</p>"
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(Test913(), context_factory(html), ai)
    assert result.status == Status.FAIL
    kind, items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "heading"
    assert items[0].text == "Nos services"
    assert "audits" in items[0].context


def test_913_candidate_that_is_not_a_heading(context_factory, run_rgaa):
    html = "<h1>Accueil</h1><p><strong>Important</strong></p>"
    ai = text_services(structure_answer=structure(False))
    assert run_rgaa(Test913(), context_factory(html), ai).status == Status.PASS


def test_913_candidates_without_ai_need_review(context_factory, run_rgaa):
    html = "<p><strong>Nos services</strong></p><p>Texte</p>"
    assert run_rgaa(Test913(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_913_ai_exception_gives_error(context_factory, run_rgaa):
    html = "<p><strong>Nos services</strong></p>"
    ai = text_services(structure_answer=RuntimeError("panne"))
    assert run_rgaa(Test913(), context_factory(html), ai).status == Status.ERROR


# ---- Emplacement des observations ------------------------------------


def test_911_finding_is_located_at_the_first_heading_concerned(context_factory, run_rgaa):
    html = "<h1>Accueil</h1>\n<h2>Offres</h2>\n<h4>Tarifs</h4>\n<p>10 €</p>\n<h2>Contact</h2>\n<h4>Plan</h4>"
    ai = text_services(hierarchy_answer=relevance(False, problems=["h4 rattaché à aucun h3"]))
    result = run_rgaa(Test911(), context_factory(html), ai)
    assert result.status == Status.FAIL
    finding = result.findings[0]
    assert (finding.line, finding.snippet) == (3, "<h4>Tarifs</h4>")
    assert finding.evidence["lines"] == [3, 6]


def test_911_without_ai_finding_is_located(context_factory, run_rgaa):
    finding = run_rgaa(Test911(), context_factory("<p>Intro</p>\n<h2>Actualités</h2>")).findings[0]
    assert (finding.line, finding.snippet) == (2, "<h2>Actualités</h2>")


def test_912_empty_heading_is_located(context_factory, run_rgaa):
    result = run_rgaa(Test912(), context_factory('<h1>Accueil</h1>\n<h2 id="vide"></h2>'), text_services())
    finding = next(item for item in result.findings if item.message == "Le titre est vide.")
    assert (finding.line, finding.snippet) == (2, '<h2 id="vide"></h2>')


def test_912_irrelevant_heading_is_located(context_factory, run_rgaa):
    ai = text_services(relevance_answer=[relevance(True), relevance(False)])
    html = "<h1>Accueil</h1>\n<h2>Titre</h2>\n<p>Nos horaires</p>"
    finding = run_rgaa(Test912(), context_factory(html), ai).findings[0]
    assert (finding.line, finding.snippet) == (2, "<h2>Titre</h2>")


def test_913_aria_heading_without_level_is_located(context_factory, run_rgaa):
    html = '<h1>Accueil</h1>\n<div role="heading">Contact</div>'
    finding = run_rgaa(Test913(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<div role="heading">Contact</div>')


def test_913_unmarked_heading_is_located(context_factory, run_rgaa):
    html = "<h1>Accueil</h1>\n<p><strong>Nos services</strong></p>\n<p>Nous proposons des audits.</p>"
    finding = run_rgaa(Test913(), context_factory(html), text_services(structure_answer=structure(True))).findings[0]
    assert (finding.line, finding.snippet) == (2, "<p><strong>Nos services</strong></p>")


# ---- Corrections proposées -------------------------------------------

HIERARCHY_RECOMMENDATION = "Organiser les niveaux de titres selon la structure réelle du contenu."
HEADING_RECOMMENDATION = "Rédiger un titre qui décrit le contenu de la section qu'il introduit."
IRRELEVANT = '<h1>Accueil</h1><h2 id="s">Titre</h2><p>Nos horaires</p>'


def test_911_fail_gives_the_level_that_removes_the_jump(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(False))
    result = run_rgaa(Test911(), context_factory('<h1>A</h1><h2>Offres</h2><h4 class="t">Tarifs</h4>'), ai)
    assert result.findings[0].recommendation == (
        f'{HIERARCHY_RECOMMENDATION} Exemple : <h4 class="t">Tarifs</h4> → <h3 class="t">Tarifs</h3>'
    )


def test_911_fail_on_first_heading_suggests_level_one(context_factory, run_rgaa):
    ai = text_services(hierarchy_answer=relevance(False))
    result = run_rgaa(Test911(), context_factory("<h2>Actualités</h2><h3>Brève</h3>"), ai)
    assert result.findings[0].recommendation.endswith("Exemple : <h2>Actualités</h2> → <h1>Actualités</h1>")


def test_911_no_example_when_unsure(context_factory, run_rgaa):
    low = text_services(hierarchy_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test911(), context_factory(JUMP), low).findings[0].recommendation == HIERARCHY_RECOMMENDATION
    assert run_rgaa(Test911(), context_factory(JUMP)).findings[0].recommendation == HIERARCHY_RECOMMENDATION


def test_912_fail_shows_the_ai_proposal(context_factory, run_rgaa):
    ai = text_services(relevance_answer=[relevance(True), relevance(False, suggestion="Horaires d'ouverture")])
    result = run_rgaa(Test912(), context_factory(IRRELEVANT), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation == (
        f"{HEADING_RECOMMENDATION} Proposition : « Horaires d'ouverture ». "
        'Exemple : <h2 id="s">Titre</h2> → <h2 id="s">Horaires d\'ouverture</h2>'
    )


def test_912_proposal_ignored_when_unsure_or_relevant(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(False, confidence="low", suggestion="Horaires"))
    result = run_rgaa(Test912(), context_factory(IRRELEVANT), low)
    assert result.status == Status.NEEDS_REVIEW
    assert all(finding.recommendation == HEADING_RECOMMENDATION for finding in result.findings)

    relevant = text_services(relevance_answer=relevance(True, suggestion="Horaires"))
    result = run_rgaa(Test912(), context_factory(IRRELEVANT), relevant)
    assert (result.status, result.findings) == (Status.PASS, [])


def test_912_fail_without_proposal_keeps_the_recommendation(context_factory, run_rgaa):
    ai = text_services(relevance_answer=[relevance(True), relevance(False)])
    result = run_rgaa(Test912(), context_factory(IRRELEVANT), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation == HEADING_RECOMMENDATION


def test_913_aria_heading_example_uses_level_below_previous_heading(context_factory, run_rgaa):
    html = '<h1>Accueil</h1><h2>Services</h2><div role="heading" class="t">Audit</div>'
    finding = run_rgaa(Test913(), context_factory(html), text_services()).findings[0]
    assert finding.recommendation.endswith(
        'Exemple : <div role="heading" class="t">Audit</div> → <div role="heading" class="t" aria-level="3">Audit</div>'
    )


def test_913_unmarked_heading_example(context_factory, run_rgaa):
    html = '<h1>Accueil</h1><p class="intro"><strong>Nos services</strong></p><p>Nous proposons des audits.</p>'
    ai = text_services(structure_answer=structure(True))
    finding = run_rgaa(Test913(), context_factory(html), ai).findings[0]
    assert finding.recommendation.endswith(
        'Exemple : <p class="intro"><strong>Nos services</strong></p> → <h2 class="intro">Nos services</h2>'
    )


def test_913_no_example_for_an_uncertain_candidate(context_factory, run_rgaa):
    html = "<p><strong>Nos services</strong></p><p>Texte</p>"
    finding = run_rgaa(Test913(), context_factory(html)).findings[0]
    assert "Exemple" not in finding.recommendation

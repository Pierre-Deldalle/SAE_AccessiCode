"""Critère RGAA 6.1 : liens explicites (6.1.1 à 6.1.4 jugés par l'IA, 6.1.5 déterministe)."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test611 as RGAA611,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test612 as RGAA612,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test613 as RGAA613,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test614 as RGAA614,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test615 as RGAA615,
)

TEXT_LINK = '<p>Nos tarifs 2024 : <a id="tarifs" href="/tarifs.pdf">télécharger la grille</a>.</p>'
IMAGE_LINK = '<a href="/"><img src="logo.png" alt="Accueil de la médiathèque"></a>'
COMPOSITE_LINK = '<a href="/panier"><img src="cart.svg" alt="Panier"> (3 articles)</a>'
SVG_LINK = '<svg><desc>Carte des agences</desc><a href="/lille"><text>Agence de Lille</text></a></svg>'

CASES = [
    (RGAA611, TEXT_LINK, "télécharger la grille"),
    (RGAA612, IMAGE_LINK, "Accueil de la médiathèque"),
    (RGAA613, COMPOSITE_LINK, "Panier (3 articles)"),
    (RGAA614, SVG_LINK, "Agence de Lille"),
]


def submitted(ai):
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "link"
    return items


# ---------------------------------------------------------------------------
# Répartition des liens entre les tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("test_class", [RGAA611, RGAA612, RGAA613, RGAA614])
def test_no_link_is_not_applicable(test_class, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory("<p>Aucun lien</p><a name='ancre'>x</a>"), text_services())
    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(("test_class", "html", "label"), CASES)
def test_each_link_type_goes_to_its_own_test(test_class, html, label, context_factory, run_rgaa):
    for other, other_html, _ in CASES:
        result = run_rgaa(other(), context_factory(html), text_services())
        expected = Status.PASS if other is test_class else Status.NOT_APPLICABLE
        assert result.status == expected, (other.test_id, html)


@pytest.mark.parametrize(("test_class", "html", "label"), CASES)
def test_label_is_submitted_to_ai(test_class, html, label, context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(test_class(), context_factory(html), ai)
    assert submitted(ai)[0].text == label


def test_hidden_links_are_ignored(context_factory, run_rgaa):
    html = '<div hidden><a href="/a">Lien caché</a></div><a href="/b" aria-hidden="true">Masqué</a>'
    assert run_rgaa(RGAA611(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_button_role_is_not_a_link(context_factory, run_rgaa):
    html = '<a href="#" role="button">Ouvrir</a>'
    assert run_rgaa(RGAA611(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Intitulé et contexte transmis à l'IA
# ---------------------------------------------------------------------------


def test_text_link_context_and_href(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(RGAA611(), context_factory("<h2>Tarifs</h2>" + TEXT_LINK), ai)
    item = submitted(ai)[0]
    assert item.details["href"] == "/tarifs.pdf"
    assert item.details["label_source"] == "content"
    assert "Paragraphe : Nos tarifs 2024" in item.context
    assert "Titre de la section : Tarifs" in item.context


def test_list_and_table_context(context_factory, run_rgaa):
    html = """
    <ul><li>Rapport annuel <a href="/r.pdf">PDF</a></li></ul>
    <table><tr><th>Document</th></tr><tr><td><a href="/c.pdf">Lire</a></td></tr></table>
    """
    ai = text_services()
    run_rgaa(RGAA611(), context_factory(html), ai)
    first, second = submitted(ai)
    assert "Élément de liste : Rapport annuel PDF" in first.context
    assert "Cellule : Lire (en-têtes : Document)" in second.context


def test_aria_labelledby_then_aria_label_then_content(context_factory, run_rgaa):
    html = """
    <span id="d">Programme du festival</span>
    <a href="/a" aria-labelledby="d" aria-label="ignoré">Lire</a>
    <a href="/b" aria-label="Programme complet">Lire</a>
    <a href="/c" aria-labelledby="absent">Programme jeunesse</a>
    """
    ai = text_services()
    run_rgaa(RGAA611(), context_factory(html), ai)
    assert [(item.text, item.details["label_source"]) for item in submitted(ai)] == [
        ("Programme du festival", "aria-labelledby"),
        ("Programme complet", "aria-label"),
        ("Programme jeunesse", "content"),
    ]


def test_same_label_to_different_destinations_is_reported(context_factory, run_rgaa):
    html = '<a href="/actu/1">Lire la suite</a><a href="/actu/2">Lire la suite</a>'
    ai = text_services()
    run_rgaa(RGAA611(), context_factory(html), ai)
    first, second = submitted(ai)
    assert first.details["same_label_other_destinations"] == "/actu/2"
    assert second.details["same_label_other_destinations"] == "/actu/1"


def test_image_link_alternatives_are_described(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(RGAA612(), context_factory(IMAGE_LINK), ai)
    assert submitted(ai)[0].details["images"] == "img : « Accueil de la médiathèque »"


def test_image_map_area_is_an_image_link(context_factory, run_rgaa):
    html = '<map name="m"><area href="/nord" alt="Région Nord" shape="rect" coords="0,0,1,1"></map>'
    ai = text_services()
    run_rgaa(RGAA612(), context_factory(html), ai)
    assert submitted(ai)[0].text == "Région Nord"


def test_link_aria_label_takes_priority_over_image_alt(context_factory, run_rgaa):
    html = '<a href="/" aria-label="Retour à l\'accueil"><img src="l.png" alt="Logo"></a>'
    ai = text_services()
    run_rgaa(RGAA612(), context_factory(html), ai)
    assert submitted(ai)[0].text == "Retour à l'accueil"


def test_composite_link_keeps_dom_order(context_factory, run_rgaa):
    html = '<a href="/p">Voir <img src="a.png" alt="le plan"> du site</a>'
    ai = text_services()
    run_rgaa(RGAA613(), context_factory(html), ai)
    assert submitted(ai)[0].text == "Voir le plan du site"


def test_svg_link_description_is_sent(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(RGAA614(), context_factory(SVG_LINK), ai)
    assert submitted(ai)[0].details["svg_description"] == "Carte des agences"


# ---------------------------------------------------------------------------
# Décision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (RGAA611, '<a href="/x"><span aria-hidden="true">→</span></a>'),
        (RGAA612, '<a href="/x"><img src="a.png" alt=""></a>'),
        (RGAA614, '<svg><a href="/x"><circle r="4"/></a></svg>'),
    ],
)
def test_link_without_label_fails_without_ai(test_class, html, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(test_class(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert "n'a pas d'intitulé" in result.findings[0].message
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_explicit_link_passes(context_factory, run_rgaa):
    result = run_rgaa(RGAA611(), context_factory(TEXT_LINK), text_services(relevance_answer=relevance(True)))
    assert result.status == Status.PASS
    assert result.findings == []


def test_non_explicit_link_fails(context_factory, run_rgaa):
    html = '<a id="ici" href="/x">cliquez ici</a>'
    result = run_rgaa(RGAA611(), context_factory(html), text_services(relevance_answer=relevance(False)))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "a#ici"
    assert "« cliquez ici » n'est pas explicite" in result.findings[0].message


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(RGAA611(), context_factory(TEXT_LINK), ai).status == Status.NEEDS_REVIEW


def test_unknown_answer_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    assert run_rgaa(RGAA611(), context_factory(TEXT_LINK), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(RGAA611(), context_factory(TEXT_LINK))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(RGAA611(), context_factory(TEXT_LINK), ai).status == Status.ERROR


def test_mixed_results_in_one_batch(context_factory, run_rgaa):
    html = TEXT_LINK + '<a href="/b">ici</a><a href="/c">Plan du site</a><a href="/d"></a>'
    ai = text_services(relevance_answer=[relevance(True), relevance(False), relevance(None)])
    result = run_rgaa(RGAA611(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert ai.text_relevance_analyzer.analyze_relevance.call_count == 1
    assert result.metadata["statuses"]["pass"] == 1
    assert result.metadata["statuses"]["fail"] == 2
    assert result.metadata["statuses"]["needs_review"] == 1


def test_item_limit(context_factory, run_rgaa, monkeypatch):
    monkeypatch.setenv("ACCESSICODE_AI_MAX_ITEMS", "1")
    html = '<a href="/a">Accueil</a><a href="/b">Contact</a>'
    result = run_rgaa(RGAA611(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert "Limite" in result.findings[0].message


# ---------------------------------------------------------------------------
# 6.1.5 — intitulé visible contenu dans le nom accessible (déterministe)
# ---------------------------------------------------------------------------


def test_615_no_links_not_applicable(context_factory, run_rgaa):
    context = context_factory("<p>Bonjour</p>")
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_615_simple_text_link_passes(context_factory, run_rgaa):
    context = context_factory('<a href="/contact">Contact</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_615_aria_label_contains_visible_text(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-label="Contacter notre équipe">Contact</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_aria_label_missing_visible_text_fails(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-label="Envoyer un message">Contact</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].evidence["visible_label"] == "Contact"


def test_615_words_must_remain_contiguous(context_factory, run_rgaa):
    context = context_factory('<a href="/achat" aria-label="Commander le produit maintenant">Commander maintenant</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL


def test_615_case_difference_allowed(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-label="CONTACTER">Contacter</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_punctuation_difference_allowed(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-label="Contact notre équipe">Contact : notre équipe</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_valid_aria_labelledby_passes(context_factory, run_rgaa):
    context = context_factory(
        '<span id="label">Contacter le service client</span><a href="/contact" aria-labelledby="label">Contacter</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_invalid_aria_labelledby_requires_review(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-labelledby="unknown">Contacter</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_symbol_requires_review(context_factory, run_rgaa):
    context = context_factory('<a href="/suite" aria-label="Suivant">&gt;</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_css_styled_link_requires_review(context_factory, run_rgaa):
    context = context_factory('<a class="link" href="/contact" aria-label="Envoyer un message">Contact</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_image_link_requires_review(context_factory, run_rgaa):
    context = context_factory('<a href="/accueil"><img src="home.png" alt="Accueil"></a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_svg_link_requires_review(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/contact"><text>Contact</text></a></svg>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_hidden_link_not_applicable(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" hidden>Contact</a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_615_missing_visible_text_not_applicable(context_factory, run_rgaa):
    context = context_factory('<a href="/contact" aria-label="Contact"></a>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_615_fail_takes_priority(context_factory, run_rgaa):
    context = context_factory(
        '<a href="/ok">Contact</a>'
        '<a href="/bad" aria-label="Envoyer un message">'
        "Contact</a>"
        '<a class="dynamic" href="/review">Aide</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert result.metadata["passed_links"] == 1
    assert result.metadata["failed_links"] == 1
    assert result.metadata["needs_review"] == 1


def test_615_role_link_is_checked(context_factory, run_rgaa):
    context = context_factory('<span role="link" aria-label="Contacter notre équipe">Contact</span>')
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# Régression : un lien interne au SVG relève de 6.1.4, pas de 6.1.1.
# ---------------------------------------------------------------------------


def test_611_svg_internal_link_is_not_counted(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/aide"><text>Consulter l’aide</text></a></svg>')

    text_result = run_rgaa(RGAA611(), context)
    svg_result = run_rgaa(RGAA614(), context)

    assert text_result.status == Status.NOT_APPLICABLE
    assert text_result.tested_elements == 0
    assert svg_result.status == Status.NEEDS_REVIEW
    assert svg_result.tested_elements == 1

"""Critère RGAA 3.1 : information donnée uniquement par la couleur (jugée par l'IA)."""

from pathlib import Path

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test311,
    Test312,
    Test313,
    Test314,
    Test315,
    Test316,
)
from tests.ai_fakes import sensory, text_services

COLORED_WORD = '<p>Statut : <span id="etat" style="color: red">indisponible</span></p>'
COLOR_TEXT = '<p id="aide">Les champs en rouge sont obligatoires.</p>'
IMAGE = '<img id="graphe" src="ventes.png" alt="Ventes par région">'


def submitted_texts(ai):
    kind, items = ai.sensory_analyzer.analyze_texts.call_args.args
    assert kind == "color"
    return items


# ---------------------------------------------------------------------------
# Aucun candidat → NOT_APPLICABLE (et pas d'appel IA)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("test_class", [Test311, Test312, Test313, Test314, Test315, Test316])
def test_no_candidate_is_not_applicable(test_class, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(test_class(), context_factory("<main><p>Bienvenue sur le site.</p></main>"), ai)
    assert result.status == Status.NOT_APPLICABLE
    ai.sensory_analyzer.analyze_texts.assert_not_called()
    ai.sensory_analyzer.analyze_image.assert_not_called()


# ---------------------------------------------------------------------------
# 3.1.1 — mots mis en couleur
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        COLORED_WORD,
        '<p>Statut : <font color="red">indisponible</font></p>',
        "<p>Statut : <mark>indisponible</mark></p>",
        '<style>.alerte { color: #c00 }</style><p>Statut : <span class="alerte">indisponible</span></p>',
    ],
)
def test_311_colored_words_are_candidates(html, context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test311(), context_factory(html), ai)
    item = submitted_texts(ai)[0]
    assert item.text == "indisponible"
    assert "Mise en couleur" in item.context


def test_311_external_stylesheet_is_read(context_factory, run_rgaa):
    context = context_factory('<p>Statut : <span class="alerte">indisponible</span></p>')
    context.css_sources = {Path("site.css"): "@media screen { .alerte { color: red } }"}
    ai = text_services()
    run_rgaa(Test311(), context, ai)
    assert submitted_texts(ai)[0].text == "indisponible"


@pytest.mark.parametrize(
    "html",
    [
        '<p>Texte <span style="color: inherit">normal</span></p>',
        "<style>* { color: #222 }</style><p>Texte <span>normal</span></p>",
        "<style>code { background: #eee }</style><p>Tapez <code>ls</code></p>",
        '<p>Texte <span hidden style="color: red">caché</span></p>',
        '<p>Texte <span style="font-weight: bold">gras</span></p>',
    ],
)
def test_311_neutral_or_hidden_colors_are_ignored(html, context_factory, run_rgaa):
    assert run_rgaa(Test311(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_311_color_only_fails(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=True))
    result = run_rgaa(Test311(), context_factory(COLORED_WORD), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "span#etat"
    assert "n'est donnée que par la couleur" in result.findings[0].message


def test_311_other_means_passes(context_factory, run_rgaa):
    result = run_rgaa(
        Test311(), context_factory(COLORED_WORD), text_services(sensory_answer=sensory(relies_only=False))
    )
    assert result.status == Status.PASS
    assert result.findings == []


def test_311_decorative_color_is_not_applicable(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(conveys=False))
    assert run_rgaa(Test311(), context_factory(COLORED_WORD), ai).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.1.2 — indication de couleur dans un texte
# ---------------------------------------------------------------------------


def test_312_color_indication_is_submitted(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test312(), context_factory("<h2>Inscription</h2>" + COLOR_TEXT), ai)
    item = submitted_texts(ai)[0]
    assert item.text == "Les champs en rouge sont obligatoires."
    assert "Titre de la section : Inscription" in item.context


def test_312_each_block_once(context_factory, run_rgaa):
    html = "<ul><li>Le vert indique un succès, le rouge une erreur.</li></ul><p>Rien à signaler ici.</p>"
    ai = text_services()
    result = run_rgaa(Test312(), context_factory(html), ai)
    assert len(submitted_texts(ai)) == 1
    assert result.tested_elements == 1


def test_312_script_and_style_are_ignored(context_factory, run_rgaa):
    html = "<script>var rouge = 1;</script><style>.vert{}</style><p>Bonjour</p>"
    assert run_rgaa(Test312(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.1.3 — images
# ---------------------------------------------------------------------------


def test_313_image_file_goes_to_vlm(context_factory, run_rgaa):
    ai = text_services(sensory_image_answer=sensory(relies_only=True))
    result = run_rgaa(Test313(), context_factory(IMAGE), ai)
    assert result.status == Status.FAIL
    kind, image = ai.sensory_analyzer.analyze_image.call_args.args
    assert kind == "color"
    assert image.src == "ventes.png"
    assert result.findings[0].evidence["source"] == "image"


def test_313_decorative_images_are_excluded(context_factory, run_rgaa):
    html = '<img src="deco.png" alt=""><img src="trait.png" aria-hidden="true" alt="trait">'
    ai = text_services()
    assert run_rgaa(Test313(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    ai.sensory_analyzer.analyze_image.assert_not_called()


def test_313_inline_svg_is_read_from_code(context_factory, run_rgaa):
    html = '<svg role="img" aria-label="Légende"><circle fill="red" r="4"/></svg>'
    ai = text_services()
    result = run_rgaa(Test313(), context_factory(html), ai)
    assert result.status == Status.PASS
    ai.sensory_analyzer.analyze_image.assert_not_called()
    kind, items = ai.sensory_analyzer.analyze_texts.call_args.args
    assert "circle" in items[0].element_html


def test_313_image_error_only_affects_that_image(context_factory, run_rgaa):
    ai = text_services(sensory_image_answer=RuntimeError("VLM indisponible"))
    result = run_rgaa(Test313(), context_factory(IMAGE), ai)
    assert result.status == Status.ERROR
    assert result.findings[0].message == "L'analyse IA a échoué."


# ---------------------------------------------------------------------------
# 3.1.4 — propriétés CSS de couleur
# ---------------------------------------------------------------------------


def test_314_link_without_underline_in_text(context_factory, run_rgaa):
    html = '<style>a { text-decoration: none }</style><p>Consultez <a href="/cgv">nos conditions</a> avant.</p>'
    ai = text_services()
    run_rgaa(Test314(), context_factory(html), ai)
    item = submitted_texts(ai)[0]
    assert item.text == "nos conditions"
    assert "sans soulignement" in item.context


def test_314_navigation_link_alone_is_not_a_candidate(context_factory, run_rgaa):
    html = '<style>a { text-decoration: none }</style><nav><a href="/">Accueil</a></nav>'
    assert run_rgaa(Test314(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_314_state_rule_and_inline_style(context_factory, run_rgaa):
    html = """
    <style>.error { border-color: red }</style>
    <input id="email" class="error">
    <td style="background-color: green">Livré</td>
    """
    ai = text_services()
    run_rgaa(Test314(), context_factory(html), ai)
    texts = [item.text for item in submitted_texts(ai)]
    assert texts[0] == "(élément input sans texte)"
    assert "Livré" in texts


def test_314_does_not_repeat_311(context_factory, run_rgaa):
    assert run_rgaa(Test314(), context_factory(COLORED_WORD), text_services()).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.1.5 / 3.1.6 — médias : vérification manuelle, sans IA
# ---------------------------------------------------------------------------


def test_315_video_needs_review_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test315(), context_factory('<video src="a.mp4"></video>'), ai)
    assert result.status == Status.NEEDS_REVIEW
    ai.sensory_analyzer.analyze_texts.assert_not_called()


def test_315_audio_is_not_concerned(context_factory, run_rgaa):
    assert run_rgaa(Test315(), context_factory('<audio src="a.mp3"></audio>'), text_services()).status == (
        Status.NOT_APPLICABLE
    )


def test_316_object_needs_review_but_image_object_is_an_image(context_factory, run_rgaa):
    html = '<object data="carte.swf" type="application/x-shockwave-flash"></object>'
    assert run_rgaa(Test316(), context_factory(html), text_services()).status == Status.NEEDS_REVIEW
    image = '<object data="plan.png" type="image/png"></object>'
    assert run_rgaa(Test316(), context_factory(image), text_services()).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Règles communes de décision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [sensory(relies_only=True, confidence="low"), sensory(conveys=None), sensory(relies_only=None)],
)
def test_uncertain_answer_needs_review(answer, context_factory, run_rgaa):
    result = run_rgaa(Test312(), context_factory(COLOR_TEXT), text_services(sensory_answer=answer))
    assert result.status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test312(), context_factory(COLOR_TEXT))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(sensory_answer=RuntimeError("panne"))
    assert run_rgaa(Test312(), context_factory(COLOR_TEXT), ai).status == Status.ERROR


def test_mixed_results_in_one_batch(context_factory, run_rgaa):
    html = COLOR_TEXT + "<p>Le bouton vert valide.</p><p>Un roman noir.</p>"
    ai = text_services(sensory_answer=[sensory(relies_only=True), sensory(relies_only=False), sensory(conveys=False)])
    result = run_rgaa(Test312(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert ai.sensory_analyzer.analyze_texts.call_count == 1
    assert result.metadata["statuses"]["fail"] == 1
    assert result.metadata["statuses"]["pass"] == 1
    assert result.metadata["statuses"]["not_applicable"] == 1
    assert result.tested_elements == 2


def test_item_limit(context_factory, run_rgaa, monkeypatch):
    monkeypatch.setenv("ACCESSICODE_AI_MAX_ITEMS", "1")
    html = COLOR_TEXT + "<p>Le bouton vert valide.</p>"
    result = run_rgaa(Test312(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert "Limite" in result.findings[0].message


# ---------------------------------------------------------------------------
# Emplacement des observations (ligne et extrait de l'élément)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("test_class", "html", "snippet"),
    [
        (Test311, COLORED_WORD, '<span id="etat" style="color: red">indisponible</span>'),
        (Test312, COLOR_TEXT, '<p id="aide">Les champs en rouge sont obligatoires.</p>'),
        (Test313, IMAGE, '<img id="graphe" src="ventes.png" alt="Ventes par région">'),
        (
            Test314,
            '<style>a { text-decoration: none }</style><p>Consultez <a href="/cgv">nos conditions</a> avant.</p>',
            '<a href="/cgv">nos conditions</a>',
        ),
    ],
    ids=["3.1.1", "3.1.2", "3.1.3", "3.1.4"],
)
def test_fail_gives_line_and_snippet(test_class, html, snippet, context_factory, run_rgaa):
    answer = sensory(relies_only=True)
    ai = text_services(sensory_answer=answer, sensory_image_answer=answer)
    result = run_rgaa(test_class(), context_factory(f"<p>Intro</p>\n{html}"), ai)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (2, snippet)


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test315, '<video src="a.mp4"></video>'),
        (Test316, '<object data="carte.swf" type="application/x-shockwave-flash"></object>'),
    ],
    ids=["3.1.5", "3.1.6"],
)
def test_media_review_gives_line_and_snippet(test_class, html, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory(f"<p>Intro</p>\n{html}"), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert (result.findings[0].line, result.findings[0].snippet) == (2, html)


# ---------------------------------------------------------------------------
# Correction : proposition de l'IA et exemple « avant / après »
# ---------------------------------------------------------------------------

BASE = (
    "Transmettre aussi l'information par un autre moyen que la couleur : texte explicite, "
    "symbole, motif, soulignement ou mise en forme."
)


def test_ai_suggestion_is_proposed_on_fail(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=True, suggestion="Statut : indisponible (en rupture)"))
    finding = run_rgaa(Test311(), context_factory(COLORED_WORD), ai).findings[0]
    assert finding.recommendation == f"{BASE} Proposition : « Statut : indisponible (en rupture) »."


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        (sensory(relies_only=True, confidence="low", suggestion="Texte"), Status.NEEDS_REVIEW),
        (sensory(relies_only=True), Status.FAIL),
    ],
    ids=["confiance faible", "sans suggestion"],
)
def test_no_proposition_without_a_certain_suggestion(answer, status, context_factory, run_rgaa):
    result = run_rgaa(Test311(), context_factory(COLORED_WORD), text_services(sensory_answer=answer))
    assert result.status == status
    assert result.findings[0].recommendation == BASE


def test_suggestion_on_pass_is_ignored(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=False, suggestion="Autre"))
    result = run_rgaa(Test311(), context_factory(COLORED_WORD), ai)
    assert (result.status, result.findings) == (Status.PASS, [])


@pytest.mark.parametrize(
    ("html", "example"),
    [
        (
            "<style>a.lien { color: red; text-decoration: none }</style>"
            '<p>Consultez <a class="lien" href="/cgv">nos conditions</a> avant.</p>',
            "a.lien { text-decoration: none } → a.lien { text-decoration: underline }",
        ),
        (
            '<p>Consultez <a href="/cgv" style="text-decoration: none">nos conditions</a> avant.</p>',
            '<a href="/cgv" style="text-decoration: none"> → <a href="/cgv" style="text-decoration: underline">',
        ),
    ],
    ids=["règle CSS", "style en ligne"],
)
def test_314_link_without_underline_shows_an_example(html, example, context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=True))
    finding = run_rgaa(Test314(), context_factory(html), ai).findings[0]
    assert finding.recommendation == f"{BASE} Exemple : {example}"


def test_314_example_only_on_fail(context_factory, run_rgaa):
    html = '<style>a { text-decoration: none }</style><p>Consultez <a href="/cgv">nos conditions</a> avant.</p>'
    result = run_rgaa(Test314(), context_factory(html), text_services(sensory_answer=sensory(conveys=None)))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].recommendation == BASE

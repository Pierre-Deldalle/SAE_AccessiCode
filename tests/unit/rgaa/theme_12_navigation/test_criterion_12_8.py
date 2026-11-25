from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_7 import Test1271, Test1272

HTML = '<html><body><a href="#contenu">Aller au contenu</a><nav>Menu</nav><main id="contenu">Texte</main></body></html>'


def test_1271_pass(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.navigation_evidence["12.7.1"] = {"visible_on_focus": True}
    assert run_rgaa(Test1271(), c).status == Status.PASS


def test_1271_review(context_factory, run_rgaa):
    assert run_rgaa(Test1271(), context_factory(HTML)).status == Status.NEEDS_REVIEW


def test_1271_fail(context_factory, run_rgaa):
    assert run_rgaa(Test1271(), context_factory('<main id="m">Texte</main>')).status == Status.FAIL


def test_1272_pass(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.page_doms["second.html"] = BeautifulSoup(HTML, "html.parser")
    c.navigation_evidence["12.7.2"] = {"same_visual_position": True, "visible_on_focus": True, "functional": True}
    assert run_rgaa(Test1272(), c).status == Status.PASS


def test_1272_review(context_factory, run_rgaa):
    assert run_rgaa(Test1272(), context_factory(HTML)).status == Status.NEEDS_REVIEW


def test_1272_fail(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.navigation_evidence["12.7.2"] = {"same_visual_position": False, "visible_on_focus": True, "functional": True}
    assert run_rgaa(Test1272(), c).status == Status.FAIL


def test_single_page_exception(context_factory, run_rgaa):
    c = context_factory("<main>Texte</main>")
    c.navigation_evidence["12.7.1"] = {"single_page_no_need": True}
    assert run_rgaa(Test1271(), c).status == Status.NOT_APPLICABLE


def test_1271_fail_is_located_on_main(context_factory, run_rgaa):
    [note] = run_rgaa(Test1271(), context_factory('<nav>Menu</nav>\n<main id="m">Texte</main>')).findings
    assert (note.element, note.line, note.snippet) == ("main#m", 2, '<main id="m">Texte</main>')


def test_1272_fail_is_located_in_the_page_without_link(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.page_doms["second.html"] = BeautifulSoup('<html lang="fr">\n<main>Texte</main>\n</html>', "html.parser")
    c.navigation_evidence["12.7.2"] = {"same_visual_position": True, "visible_on_focus": True, "functional": True}
    result = run_rgaa(Test1272(), c)
    assert result.status == Status.FAIL
    note = result.findings[0]
    assert (note.file, note.line, note.snippet) == ("second.html", 1, '<html lang="fr"> <main>Texte</main> </html>')


def test_1271_fail_shows_the_link_to_add(context_factory, run_rgaa):
    c = context_factory('<body>\n<nav>Menu</nav>\n<main id="m">Texte</main>\n</body>')
    [note] = run_rgaa(Test1271(), c).findings
    assert note.recommendation == (
        "Ajouter un lien href='#id-du-main' avant la navigation. "
        'Exemple : <body> → <body><a href="#m">Aller au contenu principal</a>'
    )


def test_1271_link_after_main_shows_where_to_move_it(context_factory, run_rgaa):
    c = context_factory('<body><main id="m">Texte</main><a href="#m">Aller au contenu</a></body>')
    [note] = run_rgaa(Test1271(), c).findings
    assert note.message == "Le lien est placé après la zone main."
    assert note.recommendation.endswith('Exemple : <body> → <body><a href="#m">Aller au contenu</a>')


def test_1272_missing_link_shows_the_link_for_that_page(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.page_doms["second.html"] = BeautifulSoup("<html><body><main>Texte</main></body></html>", "html.parser")
    note = run_rgaa(Test1272(), c).findings[0]
    assert note.recommendation == (
        'Ajouter un lien d\'évitement valide. Exemple : <main> → <main id="contenu"> ; '
        '<body> → <body><a href="#contenu">Aller au contenu principal</a>'
    )

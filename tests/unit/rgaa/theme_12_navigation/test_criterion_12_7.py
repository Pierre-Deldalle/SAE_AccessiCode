from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_6 import Test1261


def test_native_landmarks_pass(context_factory, run_rgaa):
    c = context_factory("<html><header>H</header><nav>N</nav><main>M</main><footer>F</footer></html>")
    assert run_rgaa(Test1261(), c).status == Status.PASS


def test_nested_header_review(context_factory, run_rgaa):
    c = context_factory("<main><section><header>H</header></section></main>")
    assert run_rgaa(Test1261(), c).status == Status.NEEDS_REVIEW


def test_no_zones_na(context_factory, run_rgaa):
    assert run_rgaa(Test1261(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_review_is_located_on_the_zone(context_factory, run_rgaa):
    # Aucun échec possible pour 12.6.1 : seule une vérification manuelle est produite.
    c = context_factory("<main>\n<section>\n<header>H</header>\n</section>\n</main>")
    result = run_rgaa(Test1261(), c)
    note = next(item for item in result.findings if item.element.startswith("header"))
    assert (note.line, note.snippet) == (3, "<header>H</header>")


def test_role_conflict_review_shows_the_role_to_remove(context_factory, run_rgaa):
    [note] = run_rgaa(Test1261(), context_factory('<nav role="main"><a href="/">Accueil</a></nav>')).findings
    assert note.recommendation == (
        "Vérifier la sémantique et le repérage de cette zone ; si l'élément joue bien son rôle habituel, "
        'retirer l\'attribut role. Exemple : <nav role="main"> → <nav>'
    )


def test_search_field_review_shows_the_search_zone(context_factory, run_rgaa):
    c = context_factory('<form action="/recherche"><input type="search" name="q"></form>')
    [note] = run_rgaa(Test1261(), c).findings
    assert note.recommendation == (
        "Ajouter un landmark adapté, un titre ou un lien d'accès rapide. "
        'Exemple : <form action="/recherche"> → <form action="/recherche" role="search">'
    )

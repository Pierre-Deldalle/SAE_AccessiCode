"""Exemples de correction « avant → après » du thème 12."""

from bs4 import BeautifulSoup

from accessi_code.analysis.navigation import (
    body_start_example,
    positive_tabindex_example,
    search_zone_example,
    skip_link_example,
)


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_skip_link_example_uses_the_id_of_main():
    page = soup('<body class="site"><nav>Menu</nav><main id="principal">Texte</main></body>')
    assert skip_link_example(page, page.main) == (
        '<body class="site"> → <body class="site"><a href="#principal">Aller au contenu principal</a>'
    )


def test_skip_link_example_gives_an_id_to_main_without_one():
    page = soup('<body><main class="page">Texte</main></body>')
    assert skip_link_example(page, page.main) == (
        '<main class="page"> → <main class="page" id="contenu"> ; '
        '<body> → <body><a href="#contenu">Aller au contenu principal</a>'
    )


def test_skip_link_example_avoids_an_id_already_used():
    page = soup('<body><p id="contenu">Intro</p><main>Texte</main></body>')
    assert skip_link_example(page, page.main).startswith('<main> → <main id="contenu-2">')


def test_skip_link_example_without_body():
    page = soup('<main id="m">Texte</main>')
    assert skip_link_example(page, page.main) == (
        'placer <a href="#m">Aller au contenu principal</a> au tout début de la page'
    )
    assert skip_link_example(page, None) is None


def test_body_start_example():
    page = soup('<body lang="fr"><p>Texte</p></body>')
    assert body_start_example(page, "<a>x</a>") == '<body lang="fr"> → <body lang="fr"><a>x</a>'


def test_search_zone_example_on_the_form():
    page = soup('<form action="/recherche"><input type="search" name="q"></form>')
    assert search_zone_example(page.input) == '<form action="/recherche"> → <form action="/recherche" role="search">'


def test_search_zone_example_without_form():
    page = soup('<input type="search" name="q">')
    assert search_zone_example(page.input) == (
        '<input type="search" name="q"> → <div role="search"><input type="search" name="q"></div>'
    )


def test_search_zone_example_ignores_submit_buttons():
    page = soup('<form action="/r"><input type="search" name="q"><input type="submit" value="OK"></form>')
    assert search_zone_example(page.find("input")) == '<form action="/r"> → <form action="/r" role="search">'


def test_no_search_zone_example_in_a_form_with_other_fields():
    page = soup('<form method="post"><input type="text" name="nom"><input type="search" name="q"></form>')
    assert search_zone_example(page.find("input", type="search")) is None


def test_no_search_zone_example_inside_a_search_zone():
    page = soup('<div role="search"><input type="search"></div>')
    assert search_zone_example(page.input) is None


def test_positive_tabindex_is_removed_from_a_natively_focusable_element():
    page = soup('<a href="/" tabindex="3">Accueil</a>')
    assert positive_tabindex_example(page.a) == '<a href="/" tabindex="3"> → <a href="/">'


def test_positive_tabindex_becomes_zero_on_another_element():
    page = soup('<div tabindex="2" role="button">Ouvrir</div>')
    assert positive_tabindex_example(page.div) == (
        '<div tabindex="2" role="button"> → <div tabindex="0" role="button">'
    )

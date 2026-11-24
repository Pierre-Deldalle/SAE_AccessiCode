"""Localisation des balises dans le HTML."""

from bs4 import BeautifulSoup

from accessi_code.analysis.location import locate


def test_locate_returns_line_and_short_html():
    soup = BeautifulSoup('<main>\n  <a href="/aide">Aide</a>\n</main>', "html.parser")

    assert locate(soup.a) == (2, '<a href="/aide">Aide</a>')


def test_locate_keeps_only_the_opening_tag_for_long_elements():
    soup = BeautifulSoup('<div title="5 > 3">' + "Texte " * 40 + "</div>", "html.parser")

    assert locate(soup.div) == (1, '<div title="5 &gt; 3">')


def test_locate_truncates_long_opening_tags():
    soup = BeautifulSoup(f'<img src="x.png" alt="{"é" * 250}">', "html.parser")

    line, snippet = locate(soup.img)

    assert line == 1
    assert len(snippet) == 200
    assert snippet.startswith('<img alt="')
    assert snippet.endswith("…")


def test_locate_keeps_html_when_source_line_is_unknown():
    tag = BeautifulSoup("", "html.parser").new_tag("img")

    assert locate(tag) == (None, "<img/>")
    assert locate(None) == (None, None)

from bs4 import BeautifulSoup

from accessi_code.analysis.location import (
    SNIPPET_MAX_LENGTH,
    html_snippet,
    locate,
    locate_in_text,
    location_fields,
    opening_tag,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_locate_none_returns_none():
    assert locate(None) == (None, None)


def test_locate_gives_source_line_and_full_short_element():
    soup = _soup('<html>\n<body>\n  <a href="/x">Lien</a>\n</body>\n</html>')

    line, snippet = locate(soup.find("a"))

    assert line == 3
    assert snippet == '<a href="/x">Lien</a>'


def test_locate_long_element_keeps_only_opening_tag():
    content = "texte " * 100
    soup = _soup(f'<p>intro</p>\n<div id="bloc" class="a b">{content}</div>')

    line, snippet = locate(soup.find("div"))

    assert line == 2
    assert snippet == '<div id="bloc" class="a b">'


def test_snippet_never_exceeds_max_length():
    soup = _soup(f'<img alt="{"x" * 500}" src="a.png">')

    snippet = html_snippet(soup.find("img"))

    assert len(snippet) == SNIPPET_MAX_LENGTH
    assert snippet.startswith('<img alt="xxx')
    assert snippet.endswith("…")


def test_snippet_is_compacted_on_one_line():
    soup = _soup("<button\n    type='button'>\n   Lire\n</button>")

    assert html_snippet(soup.find("button")) == '<button type="button"> Lire </button>'


def test_opening_tag_keeps_source_order_and_escapes_values():
    soup = _soup('<video controls title="Le &quot;film&quot;" src="v.mp4"></video>')

    assert opening_tag(soup.find("video")) == '<video controls title="Le &quot;film&quot;" src="v.mp4">'


def test_snippet_keeps_source_attribute_order_empty_alt_and_accents():
    soup = _soup('<p role="note" class="x">Été <img src="a.png" alt=""></p>')

    assert html_snippet(soup.find("p")) == '<p role="note" class="x">Été <img src="a.png" alt=""></p>'


def test_locate_without_source_line_returns_none_line():
    soup = _soup("<p></p>")
    created = soup.new_tag("span")

    line, snippet = locate(created)

    assert line is None
    assert snippet == "<span></span>"


def test_locate_in_text_gives_line_of_code_inside_script():
    html = "<p>a</p>\n<script>\nconst x = 1;\naudio.play();\n</script>"
    script = _soup(html).find("script")
    offset = script.get_text().index("audio.play")

    line, snippet = locate_in_text(script, offset)

    assert line == 4
    assert snippet == "audio.play();"


def test_locate_in_text_with_invalid_offset_falls_back_to_element():
    script = _soup("<script>a();</script>").find("script")

    assert locate_in_text(script, 999) == locate(script)
    assert locate_in_text(None, 0) == (None, None)


def test_location_fields_returns_finding_keywords():
    soup = _soup("<p>\n<audio src='a.mp3'></audio></p>")

    assert location_fields(soup.find("audio")) == {"line": 2, "snippet": '<audio src="a.mp3"></audio>'}
    assert location_fields(None) == {"line": None, "snippet": None}

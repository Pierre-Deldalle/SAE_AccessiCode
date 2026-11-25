from bs4 import BeautifulSoup

from accessi_code.analysis.fix_examples import (
    attribute_fix_example,
    first_keyboard_fix_example,
    keyboard_focus_example,
    rename_example,
    shorten,
    with_example,
    wrap_example,
)


def _tag(html: str):
    return BeautifulSoup(html, "html.parser").find(True)


def test_attribute_fix_example_uses_real_values_and_keeps_order():
    track = _tag('<track kind="subtitles" src="fr.vtt" srclang="fr">')

    example = attribute_fix_example(track, set_attributes={"kind": "captions"})

    assert example == (
        '<track kind="subtitles" src="fr.vtt" srclang="fr"> → <track kind="captions" src="fr.vtt" srclang="fr">'
    )


def test_attribute_fix_example_adds_boolean_attribute():
    video = _tag("<video autoplay src='film.mp4'></video>")

    assert attribute_fix_example(video, set_attributes={"controls": ""}) == (
        '<video autoplay="" src="film.mp4"> → <video autoplay="" src="film.mp4" controls="">'
    )


def test_attribute_fix_example_can_remove_attributes():
    audio = _tag("<audio autoplay src='a.mp3'></audio>")

    assert attribute_fix_example(audio, remove_attributes=["autoplay"]) == (
        '<audio autoplay="" src="a.mp3"> → <audio src="a.mp3">'
    )


def test_attribute_fix_example_without_change_or_tag_is_none():
    video = _tag("<video controls src='f.mp4'></video>")

    assert attribute_fix_example(video, set_attributes={"controls": ""}) is None
    assert attribute_fix_example(None, set_attributes={"controls": ""}) is None


def test_keyboard_focus_example_for_negative_or_missing_tabindex():
    assert keyboard_focus_example(_tag('<button tabindex="-1">Lire</button>')) == (
        '<button tabindex="-1"> → <button tabindex="0">'
    )
    assert keyboard_focus_example(_tag('<span role="button">Lire</span>')) == (
        '<span role="button"> → <span role="button" tabindex="0">'
    )


def test_keyboard_focus_example_when_tabindex_is_not_the_fix():
    assert keyboard_focus_example(_tag("<button>Lire</button>")) is None
    assert keyboard_focus_example(_tag('<span role="button" tabindex="0">Lire</span>')) is None
    assert keyboard_focus_example(_tag('<button disabled tabindex="-1">Lire</button>')) is None
    assert keyboard_focus_example(_tag('<span role="button" aria-disabled="true">Lire</span>')) is None
    assert keyboard_focus_example(_tag("<a>Lire</a>")) is None


def test_keyboard_focus_example_is_dropped_when_it_would_not_fix_the_rule():
    span = _tag("<span>Lire</span>")

    def has_button_role(tag):
        return tag.get("role") == "button"

    assert keyboard_focus_example(span, fixed_by=has_button_role) is None
    # La vérification se fait sur une copie : l'élément d'origine n'est pas modifié.
    assert "tabindex" not in span.attrs


def test_first_keyboard_fix_example_targets_first_failing_control():
    soup = BeautifulSoup('<button>Ok</button><span role="button" tabindex="-2">Pause</span>', "html.parser")
    controls = soup.find_all(True)

    def reachable(tag):
        return tag.name == "button" or int(str(tag.get("tabindex", "-1"))) >= 0

    assert first_keyboard_fix_example(controls, reachable) == (
        '<span role="button" tabindex="-2"> → <span role="button" tabindex="0">'
    )
    assert first_keyboard_fix_example(controls[:1], reachable) is None


def test_with_example():
    assert with_example("Ajouter les commandes.", "<a> → <b>") == "Ajouter les commandes. Exemple : <a> → <b>"
    assert with_example("Ajouter les commandes.", None) == "Ajouter les commandes."
    assert with_example(None, "<a> → <b>") is None


def test_shorten():
    assert shorten("  Plan   d'accès ") == "Plan d'accès"
    assert shorten("abcdefghij", 5) == "abcd…"


def test_rename_example_keeps_attributes_and_content():
    div = _tag('<div id="header" class="haut">Logo</div>')

    assert rename_example(div, "header") == (
        '<div id="header" class="haut">Logo</div> → <header id="header" class="haut">Logo</header>'
    )


def test_rename_example_changes_attributes_and_text():
    heading = _tag('<div role="heading">Contact</div>')

    assert rename_example(heading, "div", set_attributes={"aria-level": "2"}, text="Nous écrire") == (
        '<div role="heading">Contact</div> → <div role="heading" aria-level="2">Nous écrire</div>'
    )
    assert rename_example(_tag('<div role="banner">Logo</div>'), "header", remove_attributes=["role"]) == (
        '<div role="banner">Logo</div> → <header>Logo</header>'
    )


def test_rename_example_shortens_long_content():
    paragraph = _tag(f"<p>{'mot ' * 30}</p>")

    assert rename_example(paragraph, "h2") == "<p>…</p> → <h2>…</h2>"


def test_rename_example_without_change_or_tag():
    assert rename_example(_tag("<h2>Titre</h2>"), "h2") is None
    assert rename_example(None, "h2") is None


def test_wrap_example():
    menu = _tag('<ul class="menu"><li>A</li></ul>')

    assert wrap_example(menu, "nav") == '<ul class="menu"><li>A</li></ul> → <nav><ul class="menu"><li>A</li></ul></nav>'
    assert wrap_example(_tag("<p>« Une citation »</p>"), "blockquote", text="Une citation") == (
        "<p>Une citation</p> → <blockquote><p>Une citation</p></blockquote>"
    )
    assert wrap_example(None, "nav") is None

from bs4 import BeautifulSoup

from accessi_code.analysis.fix_examples import (
    attribute_fix_example,
    first_keyboard_fix_example,
    keyboard_focus_example,
    with_example,
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

from bs4 import BeautifulSoup

from accessi_code.analysis.media import (
    find_adjacent_media_alternatives,
    find_temporal_media,
)


def test_finds_native_audio_video_and_identifiable_objects():
    soup = BeautifulSoup(
        '<audio></audio><video></video><object type="audio/mpeg"></object>'
        '<object data="/movie.mp4?download=1"></object><object data="image.svg"></object>',
        "html.parser",
    )

    media = find_temporal_media(soup)

    assert [(item.kind, item.tag.name) for item in media] == [
        ("audio", "audio"),
        ("video", "video"),
        ("audio", "object"),
        ("video", "object"),
    ]


def test_detects_immediate_link_button_and_text_candidates():
    soup = BeautifulSoup(
        "<p>Transcription proposée.</p><audio></audio>"
        "<button>Lire la transcription</button><span>Informations complémentaires</span>",
        "html.parser",
    )
    audio = soup.audio

    assert audio is not None
    alternatives = find_adjacent_media_alternatives(audio)

    assert [tag.name for tag in alternatives.links_or_buttons] == ["button"]
    assert alternatives.text_candidates == ("Transcription proposée.",)


def test_ignores_non_adjacent_link_and_whitespace_siblings():
    soup = BeautifulSoup(
        '<a href="transcript.html">Transcription</a><div><audio></audio></div>',
        "html.parser",
    )
    audio = soup.audio

    assert audio is not None
    alternatives = find_adjacent_media_alternatives(audio)

    assert alternatives.links_or_buttons == ()
    assert alternatives.text_candidates == ()
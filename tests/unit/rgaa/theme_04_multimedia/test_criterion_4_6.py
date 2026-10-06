import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_6 import (
    Test461,
    Test462,
)


@pytest.mark.parametrize("test_class", [Test461, Test462])
def test_criterion_46_without_video_is_not_applicable(
    test_class,
    context_factory,
    run_rgaa,
):
    html = '<audio src="speech.mp3"></audio>'

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.parametrize("test_class", [Test461, Test462])
def test_criterion_46_video_without_audio_description_requires_review(
    test_class,
    context_factory,
    run_rgaa,
):
    html = '<video id="lecture" src="lecture.mp4"></video>'

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert result.findings[0].element == "video#lecture"

    assert (
        result.findings[0].evidence["description_tracks_count"]
        == 0
    )

    assert (
        result.findings[0].evidence["track_sources"]
        == []
    )

    assert (
        result.findings[0].evidence[
            "adjacent_audio_description_alternatives"
        ]
        == 0
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is False
    )

    assert (
        result.findings[0].evidence[
            "audio_description_requires_review"
        ]
        is True
    )


@pytest.mark.parametrize("test_class", [Test461, Test462])
def test_criterion_46_detects_description_track(
    test_class,
    context_factory,
    run_rgaa,
):
    html = (
        '<video id="lecture" src="lecture.mp4">'
        '<track '
        'kind="descriptions" '
        'src="lecture-description.vtt">'
        '</video>'
    )

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert result.findings[0].element == "video#lecture"

    assert (
        result.findings[0].evidence["description_tracks_count"]
        == 1
    )

    assert (
        result.findings[0].evidence["track_sources"]
        == ["lecture-description.vtt"]
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is True
    )

    assert (
        result.findings[0].evidence[
            "audio_description_requires_review"
        ]
        is True
    )


def test_criterion_46_detects_adjacent_audio_description_alternative(
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<video src="lecture.mp4"></video>'
        '<a href="lecture-audiodescription.mp4">'
        'Version avec audiodescription'
        '</a>'
        '</div>'
    )

    result = run_rgaa(
        Test462(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence[
            "adjacent_audio_description_alternatives"
        ]
        == 1
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is True
    )


@pytest.mark.parametrize(
    "alternative",
    [
        '<a href="description.mp4">Audiodescription</a>',
        (
            '<a href="description.mp4" '
            'aria-label="Audiodescription">'
            'Version'
            '</a>'
        ),
        (
            '<button title="Audio description">'
            'Version'
            '</button>'
        ),
        '<a href="description.mp4">Version audio</a>',
        '<a href="description.mp4">Description audio</a>',
    ],
)
def test_criterion_46_detects_audio_description_variants(
    alternative,
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<video src="lecture.mp4"></video>'
        f'{alternative}'
        '</div>'
    )

    result = run_rgaa(
        Test461(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence[
            "adjacent_audio_description_alternatives"
        ]
        == 1
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is True
    )


@pytest.mark.parametrize(
    "link_text",
    [
        "Transcription",
        "Sous-titres",
        "Version texte",
        "Télécharger la vidéo",
        "Vidéo alternative",
    ],
)
def test_criterion_46_ignores_unrelated_adjacent_links(
    link_text,
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<video src="lecture.mp4"></video>'
        f'<a href="alternative.html">{link_text}</a>'
        '</div>'
    )

    result = run_rgaa(
        Test461(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence[
            "adjacent_audio_description_alternatives"
        ]
        == 0
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is False
    )


@pytest.mark.parametrize("test_class", [Test461, Test462])
def test_criterion_46_ignores_decorative_video(
    test_class,
    context_factory,
    run_rgaa,
):
    html = (
        '<video '
        'aria-hidden="true" '
        'src="decorative.mp4">'
        '</video>'
    )

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.parametrize("test_class", [Test461, Test462])
def test_criterion_46_ignores_presentation_video(
    test_class,
    context_factory,
    run_rgaa,
):
    html = (
        '<video '
        'role="presentation" '
        'src="decorative.mp4">'
        '</video>'
    )

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_criterion_46_multiple_videos_are_all_tested(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <video id="video-1" src="video-1.mp4">
                <track
                    kind="descriptions"
                    src="video-1-description.vtt"
                >
            </video>

            <video id="video-2" src="video-2.mp4"></video>

            <video
                id="video-3"
                aria-hidden="true"
                src="decorative.mp4"
            ></video>
        </div>
    """

    result = run_rgaa(
        Test461(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2

    assert result.findings[0].element == "video#video-1"
    assert result.findings[1].element == "video#video-2"

    assert (
        result.findings[0].evidence[
            "description_tracks_count"
        ]
        == 1
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is True
    )

    assert (
        result.findings[1].evidence[
            "description_tracks_count"
        ]
        == 0
    )

    assert (
        result.findings[1].evidence[
            "has_audio_description_candidate"
        ]
        is False
    )


def test_criterion_46_track_without_src_is_not_counted(
    context_factory,
    run_rgaa,
):
    html = """
        <video id="lecture" src="lecture.mp4">
            <track kind="descriptions">
        </video>
    """

    result = run_rgaa(
        Test461(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence[
            "description_tracks_count"
        ]
        == 0
    )

    assert (
        result.findings[0].evidence["track_sources"]
        == []
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is False
    )


def test_criterion_46_other_track_kind_is_not_counted(
    context_factory,
    run_rgaa,
):
    html = """
        <video id="lecture" src="lecture.mp4">
            <track
                kind="subtitles"
                src="lecture-subtitles.vtt"
            >
        </video>
    """

    result = run_rgaa(
        Test461(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence[
            "description_tracks_count"
        ]
        == 0
    )

    assert (
        result.findings[0].evidence["track_sources"]
        == []
    )

    assert (
        result.findings[0].evidence[
            "has_audio_description_candidate"
        ]
        is False
    )
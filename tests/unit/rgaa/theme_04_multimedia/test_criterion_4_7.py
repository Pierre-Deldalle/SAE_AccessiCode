import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_7 import (
    Test471,
)


def test_criterion_471_without_temporal_media_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <p>Un contenu classique.</p>
            <img src="image.jpg" alt="Une image">
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.parametrize(
    "media",
    [
        '<video id="video" src="video.mp4"></video>',
        '<audio id="audio" src="audio.mp3"></audio>',
    ],
)
def test_criterion_471_media_without_adjacent_text_is_non_compliant(
    media,
    context_factory,
    run_rgaa,
):
    html = f"""
        <div>
            {media}
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NON_CONFORME
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    assert (
        result.findings[0].evidence["media_identified"]
        is False
    )

    assert (
        result.findings[0].evidence["has_preceding_text"]
        is False
    )

    assert (
        result.findings[0].evidence["has_following_text"]
        is False
    )


@pytest.mark.parametrize(
    "media",
    [
        '<video id="video" src="video.mp4"></video>',
        '<audio id="audio" src="audio.mp3"></audio>',
    ],
)
def test_criterion_471_text_before_media_is_detected(
    media,
    context_factory,
    run_rgaa,
):
    html = f"""
        <div>
            <h2>Présentation du projet</h2>
            {media}
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["media_identified"] is True
    assert finding.evidence["has_preceding_text"] is True
    assert finding.evidence["has_following_text"] is False

    assert (
        finding.evidence["preceding_text"]
        == "Présentation du projet"
    )


@pytest.mark.parametrize(
    "media",
    [
        '<video id="video" src="video.mp4"></video>',
        '<audio id="audio" src="audio.mp3"></audio>',
    ],
)
def test_criterion_471_text_after_media_is_detected(
    media,
    context_factory,
    run_rgaa,
):
    html = f"""
        <div>
            {media}
            <p>Description de la vidéo.</p>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["media_identified"] is True
    assert finding.evidence["has_preceding_text"] is False
    assert finding.evidence["has_following_text"] is True

    assert (
        finding.evidence["following_text"]
        == "Description de la vidéo."
    )


def test_criterion_471_ignores_whitespace_before_media(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <h2>Titre du média</h2>

            <video
                id="lecture"
                src="lecture.mp4"
            ></video>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_preceding_text"] is True
    assert (
        finding.evidence["preceding_text"]
        == "Titre du média"
    )


def test_criterion_471_ignores_whitespace_after_media(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <video
                id="lecture"
                src="lecture.mp4"
            ></video>

            <p>
                Description du média.
            </p>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_following_text"] is True
    assert (
        finding.evidence["following_text"]
        == "Description du média."
    )


def test_criterion_471_title_before_video_is_detected(
    context_factory,
    run_rgaa,
):
    html = """
        <section>
            <h1>Interview de présentation</h1>

            <video
                id="interview"
                src="interview.mp4"
            ></video>
        </section>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence["preceding_text"]
        == "Interview de présentation"
    )


def test_criterion_471_paragraph_before_audio_is_detected(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <p>Écoutez le témoignage du directeur.</p>

            <audio
                id="temoignage"
                src="temoignage.mp3"
            ></audio>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1

    assert (
        result.findings[0].evidence["preceding_text"]
        == "Écoutez le témoignage du directeur."
    )


def test_criterion_471_only_immediate_text_is_used(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <h2>Présentation de la vidéo</h2>

            <div class="container"></div>

            <video
                id="lecture"
                src="lecture.mp4"
            ></video>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NON_CONFORME
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["media_identified"] is False
    assert finding.evidence["preceding_text"] == ""


def test_criterion_471_text_inside_media_container_is_not_used(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <div>
                <p>Titre de la vidéo</p>

                <video
                    id="lecture"
                    src="lecture.mp4"
                ></video>
            </div>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["media_identified"] is True
    assert (
        finding.evidence["preceding_text"]
        == "Titre de la vidéo"
    )


def test_criterion_471_decorative_video_is_ignored(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <video
                id="background"
                aria-hidden="true"
                src="background.mp4"
            ></video>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_criterion_471_presentation_audio_is_ignored(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <audio
                id="background"
                role="presentation"
                src="background.mp3"
            ></audio>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_criterion_471_multiple_media_all_identified(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <h2>Vidéo de présentation</h2>
            <video
                id="video-1"
                src="video-1.mp4"
            ></video>

            <audio
                id="audio-1"
                src="audio-1.mp3"
            ></audio>
            <p>Podcast de présentation.</p>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.CONFORME
    assert result.tested_elements == 2
    assert len(result.findings) == 2

    assert (
        result.findings[0].element
        == "video#video-1"
    )

    assert (
        result.findings[1].element
        == "audio#audio-1"
    )

    assert (
        result.findings[0].evidence["media_identified"]
        is True
    )

    assert (
        result.findings[1].evidence["media_identified"]
        is True
    )


def test_criterion_471_mixed_media_returns_non_compliant(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <h2>Vidéo identifiée</h2>
            <video
                id="video-1"
                src="video-1.mp4"
            ></video>

            <audio
                id="audio-1"
                src="audio-1.mp3"
            ></audio>
        </div>
    """

    result = run_rgaa(
        Test471(),
        context_factory(html),
    )

    assert result.status == Status.NON_CONFORME
    assert result.tested_elements == 2
    assert len(result.findings) == 2

    assert (
        result.findings[0].evidence["media_identified"]
        is True
    )

    assert (
        result.findings[1].evidence["media_identified"]
        is False
    )
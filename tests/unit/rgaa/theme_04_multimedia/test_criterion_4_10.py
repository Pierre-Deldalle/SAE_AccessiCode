import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_10 import (
    Test4101,
)


def test_criterion_410_without_automatic_sound_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <audio controls src="audio.mp3"></audio>
            <video controls src="video.mp4"></video>

            <audio src="audio-2.mp3"></audio>
            <video src="video-2.mp4"></video>
        </div>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


@pytest.mark.parametrize(
    "media",
    [
        '<audio autoplay src="audio.mp3"></audio>',
        '<video autoplay src="video.mp4"></video>',
        '<object autoplay data="audio.mp3"></object>',
        '<embed autoplay src="audio.mp3">',
        '<bgsound autostart="true" src="audio.mp3">',
    ],
)
def test_criterion_410_detects_automatic_sound(
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        Test4101(),
        context_factory(media),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["automatic_sound"] is True
    assert finding.evidence["manual_review_required"] is True


@pytest.mark.parametrize(
    "media",
    [
        '<audio autoplay controls src="audio.mp3"></audio>',
        '<video autoplay controls src="video.mp4"></video>',
    ],
)
def test_criterion_410_autoplay_with_native_controls(
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        Test4101(),
        context_factory(media),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["automatic_sound"] is True
    assert finding.evidence["controls"] is True
    assert finding.evidence["stop_control_detected"] is True
    assert finding.evidence["independent_volume_control_detected"] is True

    assert finding.evidence["manual_review_required"] is True


@pytest.mark.parametrize(
    "media",
    [
        '<audio autoplay muted src="audio.mp3"></audio>',
        '<video autoplay muted src="video.mp4"></video>',
    ],
)
def test_criterion_410_muted_media_is_not_considered_as_automatic_sound(
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        Test4101(),
        context_factory(media),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["automatic_sound"] is False
    assert finding.evidence["muted"] is True


def test_criterion_410_detects_explicit_stop_button(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <audio autoplay src="audio.mp3"></audio>

            <button id="stop-audio">
                Arrêter le son
            </button>
        </div>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["stop_control_detected"] is True
    assert finding.evidence["manual_review_required"] is True


def test_criterion_410_detects_explicit_volume_control(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <audio autoplay src="audio.mp3"></audio>

            <label for="volume">
                Volume
            </label>
            <input
                id="volume"
                type="range"
                min="0"
                max="100">
        </div>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["independent_volume_control_detected"] is True
    assert finding.evidence["manual_review_required"] is True


def test_criterion_410_detects_javascript_audio_playback(
    context_factory,
    run_rgaa,
):
    html = """
        <script>
            const audio = new Audio("notification.mp3");
            audio.play();
        </script>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.element == "script[index=0]"
    assert finding.evidence["source_type"] == "javascript"
    assert finding.evidence["automatic_sound"] is True
    assert finding.evidence["manual_review_required"] is True


def test_criterion_410_detects_web_audio_api(
    context_factory,
    run_rgaa,
):
    html = """
        <script>
            const context = new AudioContext();
            const source = context.createBufferSource();
            source.start();
        </script>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["source_type"] == "javascript"
    assert finding.evidence["automatic_sound"] is True


def test_criterion_410_multiple_automatic_sounds(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <audio autoplay src="audio-1.mp3"></audio>

            <video autoplay src="video.mp4"></video>

            <audio autoplay muted src="audio-2.mp3"></audio>
        </div>
    """

    result = run_rgaa(
        Test4101(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 3
    assert len(result.findings) == 3

    assert result.metadata["candidate_sequences"] == 3
    assert result.metadata["audible_sequences"] == 2
    assert result.metadata["muted_sequences"] == 1
    assert result.metadata["manual_review_required"] is True


@pytest.mark.parametrize(
    "media",
    [
        (
            '<audio autoplay src="audio.mp3" '
            'aria-hidden="true"></audio>'
        ),
        (
            '<video autoplay src="video.mp4" '
            'role="presentation"></video>'
        ),
    ],
)
def test_criterion_410_ignores_decorative_media(
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        Test4101(),
        context_factory(media),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []
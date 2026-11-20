import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_11 import (
    Test4111,
    Test4112,
    Test4113,
)


@pytest.mark.parametrize("test_class", [Test4111, Test4112, Test4113])
def test_no_temporal_media_is_not_applicable(test_class, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory("<main><p>Texte.</p></main>"))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_criterion_4111_native_audio_controls_pass(context_factory, run_rgaa):
    result = run_rgaa(
        Test4111(),
        context_factory('<audio id="episode" controls src="episode.mp3"></audio>'),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings[0].evidence["required_actions"] == ["playback", "sound"]


def test_criterion_4111_detects_missing_playback_controls(context_factory, run_rgaa):
    result = run_rgaa(
        Test4111(),
        context_factory('<audio id="episode" src="episode.mp3"></audio>'),
    )

    assert result.status == Status.FAIL
    assert result.findings[0].evidence["missing_actions"] == ["playback", "sound"]


def test_criterion_4111_reviews_custom_controls(context_factory, run_rgaa):
    html = """
        <video id="movie" src="movie.mp4"></video>
        <button aria-controls="movie">Lecture</button>
    """

    result = run_rgaa(Test4111(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["recognized_custom_actions"] == ["playback"]


@pytest.mark.parametrize("test_class", [Test4112, Test4113])
def test_native_controls_are_accessible_and_activatable(
    test_class,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        test_class(),
        context_factory('<video id="movie" controls src="movie.mp4"></video>'),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_criterion_4112_custom_non_focusable_control_fails(context_factory, run_rgaa):
    html = """
        <video id="movie" src="movie.mp4"></video>
        <div aria-controls="movie" role="button" tabindex="-1">Lecture</div>
    """

    result = run_rgaa(Test4112(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.findings[0].evidence["keyboard_reachable"] is False


def test_criterion_4113_custom_button_needs_runtime_review(context_factory, run_rgaa):
    html = """
        <video id="movie" src="movie.mp4"></video>
        <button aria-controls="movie">Lecture</button>
    """

    result = run_rgaa(Test4113(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["keyboard_activatable"] is True


def test_criterion_411_mixed_results_prioritize_failure(context_factory, run_rgaa):
    html = """
        <audio id="episode" src="episode.mp3"></audio>
        <video id="movie" src="movie.mp4"></video>
        <button aria-controls="movie">Lecture</button>
    """

    result = run_rgaa(Test4111(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 2


def test_criterion_411_tests_are_registered_in_official_order():
    test_ids = [test.test_id for test in build_default_registry().get_all() if test.criterion_id == "4.11"]

    assert test_ids == ["4.11.1", "4.11.2", "4.11.3"]

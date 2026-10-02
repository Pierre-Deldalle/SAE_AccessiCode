import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_2 import (
    Test421,
    Test422,
    Test423,
)


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test421, '<a href="transcript.html">Transcription</a><audio src="episode.mp3"></audio>'),
        (Test422, '<video src="silent.mp4"></video><a href="transcript.html">Transcription</a>'),
        (Test423, '<video src="interview.mp4"><track kind="descriptions" src="description.vtt"></video>'),
    ],
)
def test_alternative_candidates_need_human_review(test_class, html, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.findings[0].recommendation


@pytest.mark.parametrize("test_class", [Test421, Test422, Test423])
def test_no_alternative_candidate_is_not_applicable(test_class, context_factory, run_rgaa):
    html = "<audio src='episode.mp3'></audio><video src='clip.mp4'></video>"

    result = run_rgaa(test_class(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_audio_test_does_not_include_video(context_factory, run_rgaa):
    html = '<video src="clip.mp4"></video><a href="transcript.html">Transcription</a>'

    result = run_rgaa(Test421(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE


def test_video_tests_do_not_include_audio(context_factory, run_rgaa):
    html = '<audio src="episode.mp3"></audio><a href="transcript.html">Transcription</a>'

    assert run_rgaa(Test422(), context_factory(html)).status == Status.NOT_APPLICABLE
    assert run_rgaa(Test423(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_criterion_42_tests_are_registered_in_official_order():
    test_ids = [test.test_id for test in build_default_registry().get_all() if test.criterion_id == "4.2"]

    assert test_ids == ["4.2.1", "4.2.2", "4.2.3"]

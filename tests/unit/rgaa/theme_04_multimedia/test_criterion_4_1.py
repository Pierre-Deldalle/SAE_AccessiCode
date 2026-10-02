import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_1 import (
    Test411 as RGAA411,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_1 import (
    Test412 as RGAA412,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_1 import (
    Test413 as RGAA413,
)


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (RGAA411, "<audio src='episode.mp3'></audio>"),
        (RGAA412, "<video src='silent.mp4'></video>"),
        (RGAA413, "<video src='interview.mp4'></video>"),
    ],
)
def test_media_candidates_need_human_review(test_class, html, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


@pytest.mark.parametrize("test_class", [RGAA411, RGAA412, RGAA413])
def test_no_media_is_not_applicable(test_class, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory("<main><p>Contenu textuel.</p></main>"))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_audio_finding_reports_adjacent_alternative_candidates(context_factory, run_rgaa):
    html = '<a href="transcript.html">Transcription</a><audio src="episode.mp3"></audio>'

    result = run_rgaa(RGAA411(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["adjacent_link_or_button_candidates"] == 1
    assert result.findings[0].evidence["adjacent_link_or_button_candidates"] == 1


def test_audio_test_does_not_include_video(context_factory, run_rgaa):
    result = run_rgaa(RGAA411(), context_factory("<video src='video.mp4'></video>"))

    assert result.status == Status.NOT_APPLICABLE


def test_video_tests_do_not_include_audio(context_factory, run_rgaa):
    html = "<audio src='episode.mp3'></audio>"

    assert run_rgaa(RGAA412(), context_factory(html)).status == Status.NOT_APPLICABLE
    assert run_rgaa(RGAA413(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_criterion_41_tests_are_registered_in_official_order():
    test_ids = [test.test_id for test in build_default_registry().get_all() if test.criterion_id == "4.1"]

    assert test_ids == ["4.1.1", "4.1.2", "4.1.3"]
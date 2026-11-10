import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_4 import Test441


def test_441_video_without_subtitles_is_not_applicable(context_factory, run_rgaa):
    html = '<video src="movie.mp4"></video>'
    result = run_rgaa(Test441(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_441_video_with_caption_track_requires_review(context_factory, run_rgaa):
    html = (
        '<video id="interview" src="interview.mp4">'
        '<track kind="captions" src="subtitles_fr.vtt">'
        '</video>'
    )
    result = run_rgaa(Test441(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].element == "video#interview"
    assert result.findings[0].evidence["captions_tracks_count"] == 1
    assert result.findings[0].evidence["track_sources"] == ["subtitles_fr.vtt"]


def test_441_video_with_adjacent_alternative_requires_review(context_factory, run_rgaa):
    html = (
        '<div>'
        '<video src="presentation.mp4"></video>'
        '<a href="subtitles.html">Version sous-titrée</a>'
        '</div>'
    )
    result = run_rgaa(Test441(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].evidence["adjacent_links_or_buttons"] == 1


def test_criterion_44_tests_are_registered_in_official_order():
    test_ids = [test.test_id for test in build_default_registry().get_all() if test.criterion_id == "4.4"]

    assert test_ids == ["4.4.1"]
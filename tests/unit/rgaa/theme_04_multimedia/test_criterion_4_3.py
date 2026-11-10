import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_3 import Test431, Test432


def test_431_video_without_subtitle_candidates_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test431(), context_factory('<video src="interview.mp4"></video>'))

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].recommendation


def test_431_caption_track_and_adjacent_alternative_need_content_review(context_factory, run_rgaa):
    html = (
        '<video id="interview" src="interview.mp4">'
        '<track kind="captions" src="captions.vtt">'
        '</video><a href="version.html">Version sous-titrée</a>'
    )

    result = run_rgaa(Test431(), context_factory(html))

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].element == "video#interview"
    assert result.findings[0].evidence == {
        "captions_track_candidates": 1,
        "adjacent_link_or_button_candidates": 1,
    }


@pytest.mark.parametrize(
    ("html", "expected_status"),
    [
        ('<video><track kind="captions" src="captions.vtt"></video>', Status.PASS),
        ('<video><track kind="caption" src="captions.vtt"></video>', Status.FAIL),
        ('<video><track kind="subtitles" src="subtitles.vtt"></video>', Status.NOT_APPLICABLE),
        ('<video><track kind="captions"></video>', Status.NOT_APPLICABLE),
        ("<video></video>", Status.NOT_APPLICABLE),
    ],
)
def test_432_checks_caption_track_kind(context_factory, run_rgaa, html, expected_status):
    result = run_rgaa(Test432(), context_factory(html))

    assert result.status == expected_status
    assert result.tested_elements == (1 if expected_status in {Status.PASS, Status.FAIL} else 0)


def test_432_mixed_caption_track_kinds_fail(context_factory, run_rgaa):
    html = '<video><track kind="captions" src="captions-en.vtt"><track kind="caption" src="captions-fr.vtt"></video>'

    result = run_rgaa(Test432(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.metadata["passed_count"] == 0
    assert result.metadata["failed_count"] == 1


def test_criterion_43_tests_are_registered_in_official_order():
    test_ids = [test.test_id for test in build_default_registry().get_all() if test.criterion_id == "4.3"]

    assert test_ids == ["4.3.1", "4.3.2"]

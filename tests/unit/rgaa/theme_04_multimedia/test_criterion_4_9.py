import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_9 import (
    Test491,
)


def test_criterion_49_without_non_temporal_media_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <p>Un contenu classique.</p>
            <video src="video.mp4"></video>
            <audio src="audio.mp3"></audio>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


def test_criterion_49_without_alternative_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document"
                data="document.pdf">
            </object>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 1
    assert result.findings == []

    assert result.metadata["candidate_media"] == 1
    assert result.metadata["media_with_alternative"] == 0
    assert result.metadata["media_without_alternative"] == 1


@pytest.mark.parametrize(
    "media",
    [
        '<object id="document" data="document.pdf"></object>',
        '<embed id="document" src="document.pdf">',
    ],
)
def test_criterion_49_with_alternative_needs_review(
    media,
    context_factory,
    run_rgaa,
):
    html = (
        "<div>"
        f"{media}"
        '<a href="alternative.html">Lire l’alternative</a>'
        "</div>"
    )

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["alternative_detected"] is True
    assert finding.evidence["relevance_requires_manual_review"] is True


@pytest.mark.parametrize(
    "control",
    [
        '<a href="alternative.html">Lire l’alternative</a>',
        (
            '<button aria-controls="alternative">'
            "Afficher l’alternative"
            "</button>"
        ),
        (
            '<button data-href="alternative.html">'
            "Afficher l’alternative"
            "</button>"
        ),
    ],
)
def test_criterion_49_detects_alternative(
    control,
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<object id="document" data="document.pdf"></object>'
        f"{control}"
        "</div>"
    )

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.evidence["alternative_detected"] is True


def test_criterion_49_ignores_invalid_link(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document"
                data="document.pdf">
            </object>

            <a href="#">Lire l'alternative</a>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 1
    assert result.findings == []


def test_criterion_49_ignores_non_identifiable_control(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document"
                data="document.pdf">
            </object>

            <button aria-controls="alternative">
                <span aria-hidden="true"></span>
            </button>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 1
    assert result.findings == []


def test_criterion_49_multiple_media_with_alternatives(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document-1"
                data="document-1.pdf">
            </object>

            <a href="alternative-1.html">
                Alternative 1
            </a>

            <object
                id="document-2"
                data="document-2.pdf">
            </object>

            <button aria-controls="alternative-2">
                Alternative 2
            </button>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2

    assert result.metadata["candidate_media"] == 2
    assert result.metadata["media_with_alternative"] == 2
    assert result.metadata["media_without_alternative"] == 0


def test_criterion_49_multiple_media_one_with_alternative(
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document-1"
                data="document-1.pdf">
            </object>

            <a href="alternative-1.html">
                Alternative 1
            </a>

            <object
                id="document-2"
                data="document-2.pdf">
            </object>
        </div>
    """

    result = run_rgaa(
        Test491(),
        context_factory(html),
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    assert result.metadata["candidate_media"] == 2
    assert result.metadata["media_with_alternative"] == 1
    assert result.metadata["media_without_alternative"] == 1


@pytest.mark.parametrize(
    "media",
    [
        (
            '<object id="decorative" '
            'data="icon.svg" '
            'aria-hidden="true"></object>'
        ),
        (
            '<embed id="decorative" '
            'src="icon.svg" '
            'role="presentation">'
        ),
        (
            '<object id="decorative" '
            'data="icon.svg" '
            'data-decorative="true"></object>'
        ),
    ],
)
def test_criterion_49_ignores_decorative_media(
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        Test491(),
        context_factory(media),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []
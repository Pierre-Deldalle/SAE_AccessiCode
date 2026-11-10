import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_8 import (
    Test481,
    Test482,
)


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_without_non_temporal_media_is_not_applicable(
    test_class,
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
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


@pytest.mark.parametrize("test_class", [Test481, Test482])
@pytest.mark.parametrize(
    "media",
    [
        '<object id="document" data="document.pdf"></object>',
        '<embed id="document" src="document.pdf">',
    ],
)
def test_criterion_48_media_without_adjacent_control_fails(
    test_class,
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        test_class(),
        context_factory(f"<div>{media}</div>"),
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1

    assert result.findings[0].element in {
        "object#document",
        "embed#document",
    }

    assert result.findings[0].evidence["has_alternative"] is False


@pytest.mark.parametrize("test_class", [Test481, Test482])
@pytest.mark.parametrize(
    "control",
    [
        '<a href="#">Alternative</a>',
        '<button aria-label="Afficher l’alternative">Alternative</button>',
    ],
)
def test_criterion_48_identifiable_control_without_destination_fails(
    test_class,
    control,
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<object id="document" data="document.pdf"></object>'
        f"{control}"
        '</div>'
    )

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_alternative"] is False
    assert finding.evidence["has_alternative_destination"] is False


@pytest.mark.parametrize("test_class", [Test481, Test482])
@pytest.mark.parametrize(
    "control",
    [
        '<a href="document.html">Lire l’alternative</a>',
        '<button aria-controls="document-alternative">'
        'Lire l’alternative'
        '</button>',
        '<button data-href="document.html">'
        'Lire l’alternative'
        '</button>',
    ],
)
def test_criterion_48_adjacent_control_with_destination_passes(
    test_class,
    control,
    context_factory,
    run_rgaa,
):
    html = (
        '<div>'
        '<object id="document" data="document.pdf"></object>'
        f"{control}"
        '</div>'
    )

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_alternative"] is True
    assert finding.evidence["has_alternative_destination"] is True


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_ignores_whitespace_between_media_and_control(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <a href="document.html">Lire l'alternative</a>

            <object
                id="document"
                data="document.pdf">
            </object>
        </div>
    """

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_alternative"] is True
    assert finding.evidence["has_alternative_destination"] is True


@pytest.mark.parametrize("test_class", [Test481, Test482])
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
def test_criterion_48_ignores_decorative_media(
    test_class,
    media,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(
        test_class(),
        context_factory(media),
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_control_before_media_passes(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <a href="alternative.html">
                Voir l'alternative
            </a>

            <object
                id="document"
                data="document.pdf">
            </object>
        </div>
    """

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_control_after_media_passes(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document"
                data="document.pdf">
            </object>

            <a href="alternative.html">
                Voir l'alternative
            </a>
        </div>
    """

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 1


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_non_identifiable_control_fails(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <object
                id="document"
                data="document.pdf">
            </object>

            <button>
                <span aria-hidden="true"></span>
            </button>
        </div>
    """

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 1

    finding = result.findings[0]

    assert finding.evidence["has_alternative"] is False


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_multiple_media_all_valid_passes(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <a href="alternative-1.html">
                Alternative 1
            </a>
            <object
                id="document-1"
                data="document-1.pdf">
            </object>

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
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.PASS
    assert result.tested_elements == 2
    assert len(result.findings) == 2


@pytest.mark.parametrize("test_class", [Test481, Test482])
def test_criterion_48_multiple_media_one_invalid_fails(
    test_class,
    context_factory,
    run_rgaa,
):
    html = """
        <div>
            <a href="alternative-1.html">
                Alternative 1
            </a>
            <object
                id="document-1"
                data="document-1.pdf">
            </object>

            <object
                id="document-2"
                data="document-2.pdf">
            </object>
        </div>
    """

    result = run_rgaa(
        test_class(),
        context_factory(html),
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 2
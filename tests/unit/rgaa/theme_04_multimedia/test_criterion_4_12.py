from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_12 import (
    Test4121,
    Test4122,
)


def test_4121_no_non_temporal_media(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <p>Page sans média non temporel.</p>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4121(), context)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_4122_no_non_temporal_media(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <p>Page sans média non temporel.</p>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4122(), context)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_4121_svg_with_button(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <svg id="carte" aria-label="Carte interactive">
                    <button type="button">Zoom +</button>
                </svg>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4121(), context)

    assert result.status == TestStatus.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_4122_svg_with_button(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <svg id="carte" aria-label="Carte interactive">
                    <button type="button">Zoom +</button>
                </svg>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4122(), context)

    assert result.status == TestStatus.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_4121_svg_with_non_keyboard_control(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <svg id="carte" aria-label="Carte interactive">
                    <div
                        role="button"
                        onclick="zoom()"
                    >
                        Zoom
                    </div>
                </svg>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4121(), context)

    assert result.status == TestStatus.FAIL


def test_4122_svg_with_non_keyboard_control(context_factory, run_rgaa):
    context = context_factory(
        """
        <html>
            <body>
                <svg id="carte" aria-label="Carte interactive">
                    <div
                        role="button"
                        onclick="zoom()"
                    >
                        Zoom
                    </div>
                </svg>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4122(), context)

    assert result.status == TestStatus.FAIL


def test_4121_external_control_with_aria_controls(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        """
        <html>
            <body>
                <button
                    type="button"
                    aria-controls="carte"
                >
                    Zoom
                </button>

                <canvas
                    id="carte"
                    width="400"
                    height="300"
                ></canvas>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4121(), context)

    assert result.status == TestStatus.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_4122_external_control_with_aria_controls(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        """
        <html>
            <body>
                <button
                    type="button"
                    aria-controls="carte"
                >
                    Zoom
                </button>

                <canvas
                    id="carte"
                    width="400"
                    height="300"
                ></canvas>
            </body>
        </html>
        """
    )

    result = run_rgaa(Test4122(), context)

    assert result.status == TestStatus.NEEDS_REVIEW


def test_4121_failure_points_to_unreachable_control(context_factory, run_rgaa):
    html = '<svg id="carte" aria-label="Carte">\n<div role="button" onclick="zoom()">Zoom</div>\n</svg>'

    result = run_rgaa(Test4121(), context_factory(html))

    assert result.status == TestStatus.FAIL
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == '<div role="button" onclick="zoom()">Zoom</div>'


def test_4121_failure_recommendation_shows_tabindex_example(context_factory, run_rgaa):
    html = '<svg id="carte" aria-label="Carte"><div role="button" onclick="zoom()">Zoom</div></svg>'

    result = run_rgaa(Test4121(), context_factory(html))

    assert result.status == TestStatus.FAIL
    assert result.findings[0].recommendation.endswith(
        'Exemple : <div role="button" onclick="zoom()"> → <div role="button" onclick="zoom()" tabindex="0">'
    )


def test_4122_no_example_when_tabindex_would_not_be_enough(context_factory, run_rgaa):
    # Un lien sans href n'est pas activable : sa destination dépend du site, pas d'exemple.
    html = '<svg id="carte" aria-label="Carte"><a onclick="zoom()">Zoom</a></svg>'

    result = run_rgaa(Test4122(), context_factory(html))

    assert result.status == TestStatus.FAIL
    assert "Exemple" not in result.findings[0].recommendation

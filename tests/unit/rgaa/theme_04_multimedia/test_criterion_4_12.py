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
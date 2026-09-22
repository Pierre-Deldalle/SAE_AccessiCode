from pathlib import Path

import pytest

from accessi_code.input.file_classifier import (
    could_be_screenshot,
    is_html_file,
    is_image_file,
)


@pytest.mark.parametrize(
    "filename",
    [
        "index.html",
        "page.htm",
        "INDEX.HTML",
        "PAGE.HTM",
    ],
)
def test_html_files_are_detected(filename: str):
    assert is_html_file(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "style.css",
        "script.js",
        "logo.png",
        "document.txt",
    ],
)
def test_non_html_files_are_not_detected_as_html(filename: str):
    assert not is_html_file(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "image.png",
        "photo.jpg",
        "photo.jpeg",
        "banner.webp",
        "animation.gif",
        "logo.svg",
        "IMAGE.PNG",
        "PHOTO.JPG",
    ],
)
def test_image_files_are_detected(filename: str):
    assert is_image_file(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "index.html",
        "style.css",
        "script.js",
        "document.txt",
    ],
)
def test_non_image_files_are_not_detected_as_images(filename: str):
    assert not is_image_file(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "screenshot.png",
        "capture.jpg",
        "page.jpeg",
        "website.webp",
        "SCREENSHOT.PNG",
    ],
)
def test_screenshot_compatible_files_are_detected(filename: str):
    assert could_be_screenshot(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "logo.svg",
        "animation.gif",
        "index.html",
        "style.css",
    ],
)
def test_non_screenshot_compatible_files_are_rejected(filename: str):
    assert not could_be_screenshot(Path(filename))

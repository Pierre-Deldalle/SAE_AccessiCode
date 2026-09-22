from pathlib import Path


HTML_EXTENSIONS = {".html", ".htm"}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
}

SCREENSHOT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


def is_html_file(path: Path) -> bool:
    return path.suffix.lower() in HTML_EXTENSIONS


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def could_be_screenshot(path: Path) -> bool:
    return path.suffix.lower() in SCREENSHOT_EXTENSIONS
"""Règles simples de classification des fichiers importés."""

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
    """Retourne ``True`` si le chemin possède une extension HTML connue."""

    return path.suffix.lower() in HTML_EXTENSIONS


def is_image_file(path: Path) -> bool:
    """Retourne ``True`` si le chemin possède une extension d'image connue."""

    return path.suffix.lower() in IMAGE_EXTENSIONS


def could_be_screenshot(path: Path) -> bool:
    """Indique si l'extension est compatible avec une capture d'écran.

    Les SVG et GIF sont des images, mais sont volontairement exclus car cette
    fonction cible les formats habituellement produits par une capture.
    """

    return path.suffix.lower() in SCREENSHOT_EXTENSIONS

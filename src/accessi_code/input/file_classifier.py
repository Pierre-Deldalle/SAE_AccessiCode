"""Règles simples de classification des fichiers importés."""

from pathlib import Path

HTML_EXTENSIONS = {".html", ".htm"}

CSS_EXTENSIONS = {".css"}

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


def is_css_file(path: Path) -> bool:
    """Retourne ``True`` si le chemin possède une extension CSS connue."""

    return path.suffix.lower() in CSS_EXTENSIONS


def is_image_file(path: Path) -> bool:
    """Retourne ``True`` si le chemin possède une extension d'image connue."""

    return path.suffix.lower() in IMAGE_EXTENSIONS


def could_be_screenshot(path: Path) -> bool:
    """Indique si l'extension est compatible avec une capture d'écran.

    Les SVG et GIF sont des images, mais sont volontairement exclus car cette
    fonction cible les formats habituellement produits par une capture.
    """

    return path.suffix.lower() in SCREENSHOT_EXTENSIONS


# Noms reconnus comme page d'accueil d'un site.
MAIN_HTML_NAMES = ("index.html", "index.htm")


def pick_main_html(paths: list[Path]) -> int | None:
    """
    Indice de la page principale parmi des chemins de fichiers.

    La page d'accueil (index.html ou index.htm, la moins profonde en cas
    de doublons) est prioritaire ; sinon, le premier fichier HTML.
    Retourne None si aucun fichier HTML n'est présent.
    """
    html_indexes = [index for index, path in enumerate(paths) if is_html_file(path)]
    if not html_indexes:
        return None
    homepages = [index for index in html_indexes if paths[index].name.lower() in MAIN_HTML_NAMES]
    if homepages:
        return min(homepages, key=lambda index: len(paths[index].parts))
    return html_indexes[0]

from enum import Enum


class Capability(str, Enum):
    """
    Représente une information ou une capacité disponible
    pour l'exécution des tests RGAA.
    """

    SOURCE_FILES = "source_files"
    HTML_SOURCE = "html_source"
    DOM = "dom"
    IMAGES = "images"
    SCREENSHOT = "screenshot"

    # Futures capacités
    COMPUTED_STYLES = "computed_styles"
    BROWSER_INTERACTION = "browser_interaction"
    ACCESSIBILITY_TREE = "accessibility_tree"
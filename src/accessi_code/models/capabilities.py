"""Capacités nécessaires à l'exécution des contrôles d'accessibilité."""

from enum import Enum


class Capability(str, Enum):
    """
    Représente une information ou une capacité disponible pour un test RGAA.

    Les valeurs futures permettent de réserver les noms des ressources qui
    seront produites par les prochaines étapes d'analyse.
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

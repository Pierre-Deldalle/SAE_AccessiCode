"""Capacités nécessaires à l'exécution des contrôles d'accessibilité."""

from enum import Enum


class Capability(str, Enum):
    """
    Représente une information ou une capacité disponible pour un test RGAA.

    Les capacités permettent au TestRunner de vérifier que les ressources
    nécessaires sont disponibles avant d'exécuter un contrôle.

    Une capacité indique la présence de données exploitables, mais ne
    garantit pas à elle seule une couverture exhaustive de la page.
    """

    SOURCE_FILES = "source_files"
    HTML_SOURCE = "html_source"
    DOM = "dom"
    CSS_SOURCE = "css_source"
    IMAGES = "images"
    SCREENSHOT = "screenshot"

    # Capacité générale conservée pour compatibilité.
    COMPUTED_STYLES = "computed_styles"

    # Contrastes textuels : critères RGAA 3.2.
    TEXT_CONTRAST = "text_contrast"

    # Contrastes des composants et graphiques : critères RGAA 3.3.
    NON_TEXT_CONTRAST = "non_text_contrast"

    # Autres capacités prévues pour les futures analyses.
    BROWSER_INTERACTION = "browser_interaction"
    ACCESSIBILITY_TREE = "accessibility_tree"

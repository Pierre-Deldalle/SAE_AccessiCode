"""Modèles utilisés pour les contrôles de contraste."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class TextContrastSample:
    """
    Représente le style calculé d'un texte à contrôler.

    Les valeurs doivent provenir du rendu réel du navigateur et non
    uniquement du HTML ou des styles inline.
    """

    element: str
    text: str

    color: str
    background_color: str

    font_size_px: float
    font_weight: int

    is_image_text: bool = False
    exempt: bool = False

    # Utilisé pour le test 3.2.5 lorsqu'un mécanisme permet
    # d'afficher une version suffisamment contrastée.
    is_contrast_mechanism: bool = False


@dataclass
class NonTextContrastSample:
    """
    Représente une comparaison de couleurs pour le critère 3.3.
    """

    element: str

    kind: Literal[
        "component",
        "graphic",
        "mechanism",
    ]

    comparison: Literal[
        "background",
        "adjacent",
    ]

    foreground_color: str
    background_color: str

    state: str | None = None
    exempt: bool = False

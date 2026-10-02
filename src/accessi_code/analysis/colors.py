"""Fonctions communes aux contrôles de contraste."""

from __future__ import annotations

import re

RGB = tuple[int, int, int]

_HEX_PATTERN = re.compile(
    r"^#([0-9a-f]{3}|[0-9a-f]{6})$",
    re.IGNORECASE,
)

_RGB_PATTERN = re.compile(
    r"^rgba?\(\s*"
    r"(\d{1,3})\s*,\s*"
    r"(\d{1,3})\s*,\s*"
    r"(\d{1,3})"
    r"(?:\s*,\s*([01](?:\.\d+)?))?"
    r"\s*\)$",
    re.IGNORECASE,
)


def parse_color(value: str) -> RGB | None:
    """
    Convertit une couleur CSS simple en tuple RGB.

    Les couleurs transparentes ou les syntaxes CSS complexes ne sont
    volontairement pas interprétées ici.
    """
    normalized = value.strip().lower()

    match = _HEX_PATTERN.fullmatch(normalized)

    if match is not None:
        hexadecimal = match.group(1)

        if len(hexadecimal) == 3:
            hexadecimal = "".join(character * 2 for character in hexadecimal)

        return (
            int(hexadecimal[0:2], 16),
            int(hexadecimal[2:4], 16),
            int(hexadecimal[4:6], 16),
        )

    match = _RGB_PATTERN.fullmatch(normalized)

    if match is None:
        return None

    red = int(match.group(1))
    green = int(match.group(2))
    blue = int(match.group(3))

    if any(
        channel > 255
        for channel in (
            red,
            green,
            blue,
        )
    ):
        return None

    alpha = match.group(4)

    if alpha is not None and float(alpha) < 1:
        return None

    return (
        red,
        green,
        blue,
    )


def _linear_channel(channel: int) -> float:
    """
    Convertit une composante sRGB en valeur linéaire.
    """
    value = channel / 255

    if value <= 0.04045:
        return value / 12.92

    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: RGB) -> float:
    """
    Calcule la luminance relative d'une couleur RGB.
    """
    red, green, blue = color

    return 0.2126 * _linear_channel(red) + 0.7152 * _linear_channel(green) + 0.0722 * _linear_channel(blue)


def contrast_ratio(
    foreground: str,
    background: str,
) -> float | None:
    """
    Calcule le rapport de contraste entre deux couleurs CSS.

    Retourne ``None`` lorsqu'une des deux couleurs ne peut pas être
    interprétée de manière suffisamment fiable.
    """
    foreground_rgb = parse_color(foreground)
    background_rgb = parse_color(background)

    if foreground_rgb is None or background_rgb is None:
        return None

    foreground_luminance = relative_luminance(foreground_rgb)
    background_luminance = relative_luminance(background_rgb)

    lightest = max(
        foreground_luminance,
        background_luminance,
    )
    darkest = min(
        foreground_luminance,
        background_luminance,
    )

    return (lightest + 0.05) / (darkest + 0.05)


def is_bold(font_weight: int) -> bool:
    """
    Indique si une graisse correspond à un texte gras.
    """
    return font_weight >= 700

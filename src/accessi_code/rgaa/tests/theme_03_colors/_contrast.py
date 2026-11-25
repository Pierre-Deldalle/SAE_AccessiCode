"""
Correction d'un contraste insuffisant (critères 3.2 et 3.3) : couleur la plus proche de
la couleur mesurée, de même teinte, qui atteint le rapport de contraste requis sur le
même arrière-plan.
"""

from __future__ import annotations

import colorsys

from accessi_code.analysis.colors import RGB, parse_color, relative_luminance

_STEPS = 40


def _ratio(first: RGB, second: RGB) -> float:
    light, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _rgb(hue: float, lightness: float, saturation: float) -> RGB:
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return round(red * 255), round(green * 255), round(blue * 255)


def hex_color(color: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def corrected_color(color: str, background: str, threshold: float) -> RGB | None:
    """
    Couleur de même teinte et de même saturation, assombrie ou éclaircie le moins possible,
    dont le contraste avec ``background`` atteint ``threshold`` ; None si les couleurs ne
    sont pas lisibles ou si aucune luminosité ne suffit.
    """
    foreground, back = parse_color(color), parse_color(background)
    if foreground is None or back is None:
        return None
    hue, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in foreground))
    best: tuple[float, RGB] | None = None
    for target in (0.0, 1.0):
        if _ratio(_rgb(hue, target, saturation), back) < threshold:
            continue
        # Recherche par dichotomie de la plus petite variation de luminosité suffisante.
        near, far = lightness, target
        for _ in range(_STEPS):
            middle = (near + far) / 2
            if _ratio(_rgb(hue, middle, saturation), back) >= threshold:
                far = middle
            else:
                near = middle
        if best is None or abs(far - lightness) < best[0]:
            best = (abs(far - lightness), _rgb(hue, far, saturation))
    return best[1] if best else None


def contrast_example(color: str, background: str, threshold: float, prop: str | None = None) -> str:
    """« Exemple : color: #999999 → color: #767676 (contraste 4.54:1 sur #ffffff). » ; vide sans correction."""
    foreground, back = parse_color(color), parse_color(background)
    fixed = corrected_color(color, background, threshold)
    if foreground is None or back is None or fixed is None:
        return ""
    before, after = hex_color(foreground), hex_color(fixed)
    if prop:
        before, after = f"{prop}: {before}", f"{prop}: {after}"
    return f" Exemple : {before} → {after} (contraste {_ratio(fixed, back):.2f}:1 sur {hex_color(back)})."

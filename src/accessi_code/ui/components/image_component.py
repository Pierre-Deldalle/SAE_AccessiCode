"""
Crée un composant image réutilisable pour l'interface Gradio.
"""

from pathlib import Path

import gradio as gr


def create_image(
    image_path: str | Path,
    *,
    height: int | None = None,
    width: int | None = None,
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
) -> gr.Image:
    """Retourne une image Gradio configurée pour l'affichage."""

    return gr.Image(
        value=str(image_path),
        height=height,
        width=width,
        show_label=False,
        interactive=False,
        container=False,

        # Masque les boutons d'action affichés par défaut sur l'image.
        buttons=[],

        # Permet de cibler facilement le composant dans le CSS.
        elem_id=elem_id,
        elem_classes=elem_classes,
    )
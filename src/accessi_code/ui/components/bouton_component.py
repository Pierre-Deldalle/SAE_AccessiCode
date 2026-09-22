"""
Crée un composant bouton réutilisable pour l'interface Gradio.
"""

import gradio as gr


def create_button(
    text: str,
    *,
    variant: str = "secondary",
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
) -> gr.Button:
    """Retourne un bouton Gradio configurable."""

    return gr.Button(
        value=text,

        # Définit le style général du bouton dans Gradio.
        variant=variant,

        # Permet de cibler le bouton dans le CSS.
        elem_id=elem_id,
        elem_classes=elem_classes,
    )
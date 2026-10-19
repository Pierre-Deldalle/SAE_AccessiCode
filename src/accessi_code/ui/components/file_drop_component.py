
"""Composant de dépôt de fichiers pour AccessiCode."""

import gradio as gr


def create_file_drop(
    *,
    file_count: str = "multiple",
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
) -> gr.File:
    """
    Crée une zone de dépôt de fichiers.

    Conserve les fonctionnalités natives de Gradio :
    - glisser-déposer ;
    - sélection de fichiers ;
    - sélection multiple si demandée.

    Affiche également les formats acceptés sous la zone.
    """

    file_input = gr.File(
        file_count=file_count,
        show_label=False,
        container=True,
        elem_id=elem_id,
        elem_classes=elem_classes,
        interactive=True,
        height=245,
    )

    gr.Markdown(
        "**Formats pris en charge :** HTML (.html, .htm), "
        "CSS (.css), images (.png, .jpg, .jpeg, .webp).",
        elem_id="file-formats-hint",
    )

    return file_input

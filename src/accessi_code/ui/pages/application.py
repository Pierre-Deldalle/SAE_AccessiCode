"""
Construit la page principale de l'application AccessiCode.
"""

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.file_drop_component import create_file_drop


def build_application_page():
    """Crée l'interface principale de l'application."""

    with gr.Column(
        visible=False,
        elem_id="application-page",
        elem_classes=["page-container"],
    ) as application_page:

        # =========================
        # TITRE
        # =========================

        gr.Markdown(
            "# AccessiCode",
            elem_id="application-title",
        )

        # =========================
        # CONTENU PRINCIPAL
        # =========================

        with gr.Column(elem_id="application-content"):

            # Lien du site web
            gr.Markdown(
                "### Lien du site web",
                elem_id="website-title",
            )

            website_input = gr.Textbox(
                placeholder="https://www.exemple.com",
                show_label=False,
                container=False,
                elem_id="website-input",
            )

            # Documents
            gr.Markdown(
                "### Insérer vos documents",
                elem_id="documents-title",
            )

            files_input = create_file_drop(
                file_count="multiple",
                elem_id="file-drop-zone",
            )

        # =========================
        # AIDE
        # =========================

        help_button = create_button(
            "?",
            elem_id="help-button",
        )

    return (
        application_page,
        website_input,
        files_input,
        help_button,
    )
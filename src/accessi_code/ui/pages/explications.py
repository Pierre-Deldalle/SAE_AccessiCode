"""
Construit la page d'explications de l'application AccessiCode.
"""

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


def build_explications_page():
    """Crée la page d'explications d'AccessiCode."""

    with gr.Column(
        visible=False,
        elem_id="explications-page",
        elem_classes=["page-container"],
    ) as explications_page:

        # Bouton retour
        back_button = create_button(
            "←",
            elem_id="back-button",
        )

        # Titre
        gr.Markdown(
            "# AccessiCode c’est quoi ?",
            elem_id="explications-title",
        )

        # Partie supérieure : texte + logo
        with gr.Row(elem_id="explications-top"):

            gr.Markdown(
                """
-
-
-
-
-
-
-
                """,
                elem_id="explications-text-top",
            )

            create_image(
                "assets/logo_complet.png",
                elem_id="explications-logo",
            )

        # Partie inférieure
        gr.Markdown(
            """
-
-
-
-
-
-
-
-
-
-
                """,
            elem_id="explications-text-bottom",
        )

    return (
        explications_page,
        back_button,
    )
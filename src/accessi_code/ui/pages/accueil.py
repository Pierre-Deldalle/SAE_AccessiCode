from pathlib import Path

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_accueil_page():
    with gr.Column(
        elem_id="accueil-page",
        elem_classes=["page-container"],
    ) as accueil_page:

        create_image(
            ASSETS_DIR / "logo_complet.png",
            width=260,
            elem_id="accueil-logo",
            elem_classes=["accueil-logo"],
        )

        start_button = create_button(
            "Accéder à\nl'application",
            variant="primary",
            elem_id="accueil-button",
            elem_classes=["accueil-button"],
        )

    return accueil_page, start_button
"""
Construit la page d'accueil de l'application AccessiCode.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


# Chemin vers les ressources graphiques utilisées sur la page.
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_accueil_page():
    """Crée les éléments visuels de la page d'accueil."""
    with gr.Column(
        elem_id="accueil-page",
        elem_classes=["page-container"],
    ) as accueil_page:

        # Titre affiché au-dessus du logo.
        gr.Markdown(
            "## Bienvenue sur",
            elem_id="welcome-title",
        )

        # Logo principal de l'application.
        create_image(
            ASSETS_DIR / "logo_complet.png",
            width=350,
            elem_id="accueil-logo",
        )

        # Bouton permettant d'accéder à la suite de l'application.
        start_button = create_button(
            "Accéder à l'application",
            variant="primary",
            elem_id="accueil-button",
        )

    # Le bouton est retourné pour pouvoir lui associer une action ailleurs.
    return accueil_page, start_button
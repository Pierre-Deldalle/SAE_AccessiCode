"""
Construit la page de chargement de l'application AccessiCode.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image
from accessi_code.ui.loading_view import render_progress

# Chemin vers les ressources graphiques.
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_chargement_page():
    """
    Crée la page de chargement de l'audit.

    Les étapes et la barre reflètent l'avancement réel du moteur
    (voir ui/loading_view.py). Retourne la page, le bloc de progression
    et le bouton d'annulation.
    """

    with gr.Column(
        visible=False,
        elem_id="chargement-page",
        elem_classes=["page-container"],
    ) as chargement_page:
        with gr.Column(elem_id="chargement-content"):
            # Titre principal.
            gr.Markdown(
                "# Analyse en cours",
                elem_id="chargement-title",
            )

            # Logo animé avec notre composant réutilisable.
            create_image(
                ASSETS_DIR / "logo_couleur.png",
                width=90,
                height=90,
                elem_id="chargement-logo",
            )

            # Message principal.
            gr.Markdown(
                "Préparation du rapport d'accessibilité…",
                elem_id="chargement-message",
            )

            # Progression réelle, mise à jour par app.run_audit().
            progress_html = gr.HTML(
                render_progress(None),
                elem_id="chargement-progress",
            )

            # Message secondaire.
            gr.Markdown(
                "La durée dépend du nombre de tests et des analyses par IA.",
                elem_id="chargement-subtitle",
            )

            # Interrompt l'audit en cours et ramène à la préparation.
            cancel_button = create_button(
                "Annuler l'audit",
                variant="secondary",
                elem_id="chargement-cancel-button",
            )

    return chargement_page, progress_html, cancel_button

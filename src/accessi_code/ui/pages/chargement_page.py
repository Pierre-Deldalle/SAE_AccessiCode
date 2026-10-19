
"""
Construit la page de chargement de l'application AccessiCode.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.components.image_component import create_image


# Chemin vers les ressources graphiques.
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_chargement_page():
    """
    Crée la page de chargement de l'audit.

    Pour le moment, le chargement est simulé.
    La barre verte ne représente pas encore
    la progression réelle du moteur d'audit.
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

            # Barre de progression verte simulée.
            gr.HTML(
                """
                <div class="accessicode-progress-section">
                    <div class="accessicode-progress-track"
                         aria-hidden="true">
                        <div class="accessicode-progress-fill"></div>
                    </div>

                    <p class="accessicode-progress-description">
                        Simulation de progression
                    </p>
                </div>
                """,
                elem_id="chargement-progress",
            )

            # Message secondaire.
            gr.Markdown(
                "Veuillez patienter quelques instants.",
                elem_id="chargement-subtitle",
            )

    return chargement_page

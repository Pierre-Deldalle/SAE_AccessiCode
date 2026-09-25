"""
Construit la page d'explications de l'application AccessiCode.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


# Chemin vers les ressources graphiques utilisées sur la page.
ASSETS_DIR = Path(__file__).parent.parent / "assets"


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
            "# AccessiCode c'est quoi ?",
            elem_id="explications-title",
        )

        # Partie supérieure : texte + logo
        with gr.Row(elem_id="explications-top"):

            gr.Markdown(
                """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed sit amet faucibus ante. Etiam condimentum diam non neque euismod, id tristique elit viverra. Vivamus mollis facilisis sapien, pretium elementum mauris accumsan ut. Vivamus ultricies lacus eget eros semper, pellentesque mattis risus laoreet. Quisque odio velit, commodo ullamcorper gravida sed, dapibus ut diam. Sed in rhoncus massa. Ut gravida, diam sed feugiat mattis, mauris dolor congue lorem, non auctor nulla libero quis dolor.
                """,
                elem_id="explications-text-top",
            )

            # Logo principal de l'application
            create_image(
                ASSETS_DIR / "logo_complet.png",
                width=150,
                elem_id="explications-logo",
            )

        # Partie inférieure
        gr.Markdown(
            """
Etiam at facilisis ipsum. Vivamus mollis purus in mi venenatis, dapibus congue sapien faucibus. Cras justo libero, consequat quis felis quis, pretium ornare elit. In id sagittis felis, bibendum ultrices nisi. Cras mattis est et massa ultricies egestas. Maecenas vitae libero eu diam tincidunt semper. Donec eleifend tortor ac enim congue sollicitudin.

Ut arcu orci, pretium at laoreet nec, sollicitudin non nisl. Mauris fringilla gravida purus sed imperdiet. In mi neque, ultricies sed enim non, semper sagittis ex. Integer non ultricies purus, in dictum augue. Cras tortor sapien, ornare vel faucibus et, cursus sit amet sem. Pellentesque nec aliquet dolor. Mauris sed mi rhoncus, volutpat arcu ac, sodales nulla. Etiam molestie molestie ligula, eu hendrerit justo dignissim vitae. Nulla ultricies pharetra consectetur.
            """,
            elem_id="explications-text-bottom",
        )

    return (
        explications_page,
        back_button,
    )
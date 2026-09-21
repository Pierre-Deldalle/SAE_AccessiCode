import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


def create_test_page():
    with gr.Blocks() as app:
        create_image(
            "src/accessi_code/ui/assets/logo_complet.png",
            width=300,
        )

        create_button(
            "Accéder à l'application",
            variant="primary",
        )

    return app


if __name__ == "__main__":
    create_test_page().launch()
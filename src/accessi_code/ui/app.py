"""
Construit l'application Gradio et charge les styles de l'interface.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.pages.accueil import build_accueil_page
from accessi_code.ui.pages.preparation_audit import build_preparation_audit_page
from accessi_code.ui.pages.explications import build_explications_page


# Répertoires utilisés pour retrouver les fichiers CSS de l'interface.
UI_DIR = Path(__file__).parent
STYLES_DIR = UI_DIR / "styles"


def load_css(*filenames: str) -> str:
    """Charge et fusionne plusieurs fichiers CSS."""
    css_parts = []

    for filename in filenames:
        css_path = STYLES_DIR / filename
        css_parts.append(css_path.read_text(encoding="utf-8"))

    return "\n".join(css_parts)


# Styles globaux et spécifiques aux pages.
CSS = load_css(
    "global.css",
    "accueil.css",
    "preparation_audit.css",
    "explications.css",
)


def open_application():
    """Cache l'accueil et affiche la préparation de l'audit."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def open_explications():
    """Cache la préparation de l'audit et affiche les explications."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def close_explications():
    """Cache les explications et retourne à la préparation de l'audit."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def create_app():
    """Crée l'application Gradio principale."""
    with gr.Blocks(
        title="AccessiCode",
        css=CSS,
        theme=gr.themes.Base(),
    ) as app:

        # Page d'accueil.
        accueil_page, start_button = build_accueil_page()

        # Page de préparation de l'audit.
        (
            preparation_audit_page,
            website_input,
            files_input,
            validate_button,
            help_button,
        ) = build_preparation_audit_page()

        # Page d'explications.
        explications_page, back_button = build_explications_page()

        # Navigation accueil -> préparation de l'audit.
        start_button.click(
            fn=open_application,
            inputs=[],
            outputs=[
                accueil_page,
                preparation_audit_page,
            ],
        )

        # Navigation préparation de l'audit -> explications.
        help_button.click(
            fn=open_explications,
            inputs=[],
            outputs=[
                preparation_audit_page,
                explications_page,
            ],
        )

        # Navigation explications -> préparation de l'audit.
        back_button.click(
            fn=close_explications,
            inputs=[],
            outputs=[
                explications_page,
                preparation_audit_page,
            ],
        )

    return app


if __name__ == "__main__":
    create_app().launch()

    
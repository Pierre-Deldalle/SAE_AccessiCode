"""
Construit l'application Gradio et charge les styles de l'interface.
"""

from pathlib import Path

import gradio as gr

from accessi_code.ui.pages.accueil import build_accueil_page


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


# Styles globaux et spécifiques à la page d'accueil.
CSS = load_css(
    "global.css",
    "accueil.css",
)


def create_app():
    """Crée l'application Gradio principale."""
    with gr.Blocks(
        title="AccessiCode",
        css=CSS,
        theme=gr.themes.Base(),
    ) as app:
        # Ajoute la page d'accueil à l'application.
        build_accueil_page()

    return app


if __name__ == "__main__":
    create_app().launch()
from pathlib import Path

import gradio as gr

from accessi_code.ui.pages.accueil import build_accueil_page


UI_DIR = Path(__file__).parent
STYLES_DIR = UI_DIR / "styles"


def load_css(*filenames: str) -> str:
    css_parts = []

    for filename in filenames:
        css_path = STYLES_DIR / filename
        css_parts.append(css_path.read_text(encoding="utf-8"))

    return "\n".join(css_parts)


CSS = load_css(
    "global.css",
    "accueil.css",
)


def create_app():
    with gr.Blocks(
        title="AccessiCode",
        css=CSS,
        theme=gr.themes.Base(),
    ) as app:
        build_accueil_page()

    return app


if __name__ == "__main__":
    create_app().launch()
import gradio as gr

from accessi_code.ui.pages.accueil import build_accueil_page

CUSTOM_CSS = """
html,
body,
.gradio-container {
    background: white !important;
}

.gradio-container {
    min-height: 100vh !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
}

#accueil-page {
    min-height: 100vh;
    display: flex !important;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 36px;
    background: white;
}

#accueil-logo {
    width: min(32vw, 420px) !important;
    max-width: 420px !important;
}

#accueil-logo img {
    width: 100% !important;
    height: auto !important;
    object-fit: contain !important;
}

#accueil-button {
    width: min(22vw, 260px) !important;
    min-width: 210px !important;
    min-height: 64px !important;

    background: #1aa3b8 !important;
    border: 1px solid #777 !important;
    border-radius: 3px !important;

    color: black !important;
    font-size: 20px !important;
    font-weight: 400 !important;
}

#accueil-button:hover {
    background: #1593a6 !important;
}

footer {
    display: none !important;
}
"""


def create_app():
    with gr.Blocks(
        title="AccessiCode",
        css=CUSTOM_CSS,
        theme=gr.themes.Base(),
    ) as app:
        build_accueil_page()

    return app


if __name__ == "__main__":
    create_app().launch()
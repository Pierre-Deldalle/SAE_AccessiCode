"""
Construit l'application Gradio et charge les styles de l'interface.

Parcours :
Accueil -> Préparation -> Chargement -> Résultats
                  |
                  -> Explications -> Préparation

La sortie de l'accueil utilise un fondu de 350 ms.
Le chargement et les résultats sont encore simulés.
"""

import asyncio
from pathlib import Path

import gradio as gr

from accessi_code.ui.pages.accueil import build_accueil_page
from accessi_code.ui.pages.chargement_page import build_chargement_page
from accessi_code.ui.pages.explications import build_explications_page
from accessi_code.ui.pages.preparation_audit import (
    build_preparation_audit_page,
)
from accessi_code.ui.pages.resultats_page import (
    DEFAULT_THEME_DETAIL,
    build_resultats_page,
)

UI_DIR = Path(__file__).parent
STYLES_DIR = UI_DIR / "styles"

ACCUEIL_CLASSES = ["page-container"]
ACCUEIL_FADE_CLASSES = ["page-container", "accueil-fade-out"]


def load_css(*filenames: str) -> str:
    """Charge et fusionne les feuilles CSS."""
    css_parts = []

    for filename in filenames:
        css_path = STYLES_DIR / filename
        css_parts.append(css_path.read_text(encoding="utf-8"))

    return "\n".join(css_parts)


CSS = load_css(
    "global.css",
    "accueil.css",
    "preparation_audit.css",
    "explications.css",
    "chargement.css",
    "resultats.css",
)


def start_accueil_transition():
    """Déclenche le fondu avant de quitter l'accueil."""
    return gr.update(elem_classes=ACCUEIL_FADE_CLASSES)


async def finish_accueil_transition():
    """
    Laisse le fondu se terminer avant de changer de page.

    Le délai est limité à 350 millisecondes.
    """
    await asyncio.sleep(0.35)

    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def open_explications():
    """Affiche les explications depuis la préparation."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def close_explications():
    """Revient de l'aide à la préparation."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def show_loading():
    """Affiche le chargement simulé."""
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
    )


async def finish_demo_loading():
    """Simule deux secondes de chargement."""
    await asyncio.sleep(2)

    return (
        gr.update(visible=False),
        gr.update(visible=True),
    )


def show_return_confirmation():
    """Demande confirmation avant de quitter les résultats."""
    return gr.update(visible=True)


def hide_return_confirmation():
    """Ferme la confirmation sans perdre les résultats."""
    return gr.update(visible=False)


def confirm_return_home():
    """Réinitialise l'interface et retourne à l'accueil."""
    return (
        gr.update(visible=False),  # Résultats
        gr.update(
            visible=True,
            elem_classes=ACCUEIL_CLASSES,
        ),  # Accueil : visible et sans l'ancienne classe de fondu
        gr.update(visible=False),  # Confirmation
        gr.update(value=""),  # URL
        gr.update(value=None),  # Fichiers
        gr.update(value=DEFAULT_THEME_DETAIL),  # Détail
    )


def create_app():
    """Crée l'application Gradio principale."""

    with gr.Blocks(
        title="AccessiCode",
        css=CSS,
        theme=gr.themes.Base(),
    ) as app:
        # Construction des pages.
        accueil_page, start_button = build_accueil_page()

        (
            preparation_audit_page,
            website_input,
            files_input,
            validate_button,
            help_button,
        ) = build_preparation_audit_page()

        explications_page, back_button = build_explications_page()
        chargement_page = build_chargement_page()

        (
            resultats_page,
            theme_buttons,
            theme_detail,
            home_button,
            confirmation_panel,
            cancel_button,
            confirm_button,
        ) = build_resultats_page()

        # Accueil : lancement du fondu, puis navigation.
        start_button.click(
            fn=start_accueil_transition,
            inputs=[],
            outputs=[accueil_page],
            show_progress="hidden",
        ).then(
            fn=finish_accueil_transition,
            inputs=[],
            outputs=[
                accueil_page,
                preparation_audit_page,
            ],
            show_progress="hidden",
        )

        # Préparation -> Explications.
        help_button.click(
            fn=open_explications,
            inputs=[],
            outputs=[
                preparation_audit_page,
                explications_page,
            ],
            show_progress="hidden",
        )

        # Explications -> Préparation.
        back_button.click(
            fn=close_explications,
            inputs=[],
            outputs=[
                explications_page,
                preparation_audit_page,
            ],
            show_progress="hidden",
        )

        # Préparation -> Chargement -> Résultats.
        validate_button.click(
            fn=show_loading,
            inputs=[],
            outputs=[
                preparation_audit_page,
                chargement_page,
                resultats_page,
            ],
            show_progress="hidden",
        ).then(
            fn=finish_demo_loading,
            inputs=[],
            outputs=[
                chargement_page,
                resultats_page,
            ],
            show_progress="hidden",
        )

        # Demande de confirmation du nouvel audit.
        home_button.click(
            fn=show_return_confirmation,
            inputs=[],
            outputs=[confirmation_panel],
            show_progress="hidden",
        )

        # Annulation du retour à l'accueil.
        cancel_button.click(
            fn=hide_return_confirmation,
            inputs=[],
            outputs=[confirmation_panel],
            show_progress="hidden",
        )

        # Retour confirmé à l'accueil.
        confirm_button.click(
            fn=confirm_return_home,
            inputs=[],
            outputs=[
                resultats_page,
                accueil_page,
                confirmation_panel,
                website_input,
                files_input,
                theme_detail,
            ],
            show_progress="hidden",
        )

    return app


if __name__ == "__main__":
    create_app().launch()

"""Construit l'application Gradio et charge les styles de l'interface.

Parcours :
Accueil -> Préparation -> Chargement -> Résultats
                  |
                  -> Explications -> Préparation

L'accueil laisse automatiquement place à la préparation après un fondu.
« Lancer l'audit » exécute le moteur RGAA via ui/audit_bridge.py, avec
une progression réelle sur la page de chargement ;
la page de résultats affiche les synthèses par thématique.
"""

from pathlib import Path

import gradio as gr

from accessi_code.service.audit_progress import AuditProgress
from accessi_code.ui.audit_bridge import stream_audit
from accessi_code.ui.loading_view import render_progress
from accessi_code.ui.pages.accueil import build_accueil_page
from accessi_code.ui.pages.chargement_page import build_chargement_page
from accessi_code.ui.pages.explications import build_explications_page
from accessi_code.ui.pages.preparation_audit import (
    RGAA_THEMES,
    build_preparation_audit_page,
)
from accessi_code.ui.pages.resultats_page import (
    SCORE_CSS,
    build_resultats_page,
    reset_updates,
    results_updates,
)
from accessi_code.ui.results_view import audit_stats

UI_DIR = Path(__file__).parent
STYLES_DIR = UI_DIR / "styles"

ACCUEIL_TRANSITION_JS = """async () => {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        // Attend le rendu initial de l'accueil ou son remontage après les résultats.
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        const app = document.querySelector("gradio-app");
        const accueil = (app?.shadowRoot ?? document).querySelector("#accueil-page");
        const progress = accueil?.querySelector(".accueil-progress-fill");

        await progress?.animate(
            [{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }],
            { duration: 3500, easing: "ease-out", fill: "forwards" }
        ).finished;
        await accueil?.animate(
            [{ opacity: 1 }, { opacity: 0 }],
            { duration: 350, easing: "ease-in-out", fill: "forwards" }
        ).finished;
    }

    return [
        { __type__: "update", visible: false },
        { __type__: "update", visible: true },
    ];
}"""


# Appelé après chaque changement de page, une fois les composants mis à jour.
# Double requestAnimationFrame : attend que le navigateur ait appliqué le rendu.
SCROLL_TO_TOP_JS = """() => {
    const resetScroll = () => {
        window.scrollTo({ top: 0, left: 0, behavior: "instant" });
        if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;

        // Certaines versions de Gradio utilisent un conteneur défilant.
        const app = document.querySelector("gradio-app");
        for (const root of [document, app?.shadowRoot].filter(Boolean)) {
            for (const container of root.querySelectorAll(".gradio-container, main")) {
                if (container.scrollHeight > container.clientHeight) {
                    container.scrollTop = 0;
                }
            }
        }
    };
    requestAnimationFrame(() => requestAnimationFrame(resetScroll));
}"""


def load_css(*filenames: str) -> str:
    """Charge et fusionne les feuilles CSS."""
    css_parts = []

    for filename in filenames:
        css_path = STYLES_DIR / filename
        css_parts.append(css_path.read_text(encoding="utf-8"))

    return "\n".join(css_parts)


CSS = (
    load_css(
        "global.css",
        "accueil.css",
        "preparation_audit.css",
        "explications.css",
        "chargement.css",
        "resultats.css",
    )
    + "\n"
    + SCORE_CSS
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
    """Affiche la page de chargement pendant l'audit."""
    return (
        gr.update(visible=False),  # Préparation
        gr.update(visible=True),  # Chargement
        gr.update(visible=False),  # Résultats
        gr.update(value="", visible=False),  # Erreur de préparation
        gr.update(value=render_progress(None)),  # Progression remise à zéro
    )


async def run_audit(url, files, themes):
    """
    Exécute l'audit en affichant sa progression réelle, puis les résultats.

    En cas d'erreur, revient à la préparation avec un message explicite.
    Ordre des sorties : chargement, progression, résultats, préparation,
    erreur, puis celles de results_updates().
    """
    skip_results = [gr.skip() for _ in reset_updates()]

    async for item in stream_audit(url, files, themes):
        if isinstance(item, AuditProgress):
            yield [
                gr.skip(),
                gr.update(value=render_progress(item)),
                gr.skip(),
                gr.skip(),
                gr.skip(),
                *skip_results,
            ]
            continue

        if item.error is not None:
            yield [
                gr.update(visible=False),
                gr.skip(),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(value=f"**L'audit n'a pas pu être lancé.** {item.error}", visible=True),
                *skip_results,
            ]
            return

        yield [
            gr.update(visible=False),
            gr.skip(),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            *results_updates(item.summaries, item.notices, audit_stats(item.duration_seconds, item.tokens_used)),
        ]


def cancel_audit():
    """Revient à la préparation après l'annulation ; les saisies sont conservées."""
    return (
        gr.update(visible=False),  # Chargement
        gr.update(visible=True),  # Préparation
        gr.update(
            value="**Audit annulé.** Vos documents et thématiques sont conservés : vous pouvez relancer l'audit.",
            visible=True,
        ),
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
        gr.update(visible=True),  # Accueil
        gr.update(visible=False),  # Confirmation
        gr.update(value=""),  # URL
        gr.update(value=None),  # Fichiers
        gr.update(value=list(RGAA_THEMES)),  # Sélection RGAA
        *reset_updates(),  # État, avertissements, détail, cartes
    )


# L'interface est conçue en clair. Gradio passe en mode sombre quand le système l'est
# (classe « dark ») : les composants natifs (liste des fichiers déposés, cases…)
# deviendraient noirs avec un texte foncé illisible. On garde donc le thème clair.
FORCE_LIGHT_THEME_JS = """() => {
    const keepLight = () => {
        for (const element of document.querySelectorAll(".dark")) {
            element.classList.remove("dark");
        }
    };
    keepLight();
    new MutationObserver(keepLight).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["class"],
        subtree: true,
    });
}"""


def launch_options() -> dict:
    """Styles, thème et script de l'application, à passer à app.launch() (Gradio 6)."""
    return {"css": CSS, "theme": gr.themes.Base(), "js": FORCE_LIGHT_THEME_JS}


def create_app():
    """Crée l'application Gradio principale (à lancer avec launch_options())."""

    with gr.Blocks(title="AccessiCode") as app:
        accueil_page = build_accueil_page()

        (
            preparation_audit_page,
            website_input,
            files_input,
            validate_button,
            help_button,
            selected_themes,
            audit_error,
        ) = build_preparation_audit_page()

        explications_page, back_button = build_explications_page()
        chargement_page, progress_html, cancel_audit_button = build_chargement_page()

        (
            resultats_page,
            theme_buttons,
            theme_detail,
            home_button,
            confirmation_panel,
            cancel_button,
            confirm_button,
            results_state,
            audit_notices,
        ) = build_resultats_page()

        # Sorties communes à l'affichage et à la remise à zéro des résultats.
        results_outputs = [results_state, audit_notices, theme_detail, *theme_buttons]

        accueil_transition = {
            "fn": None,
            "js": ACCUEIL_TRANSITION_JS,
            "outputs": [accueil_page, preparation_audit_page],
            "queue": False,
        }
        app.load(**accueil_transition)

        help_button.click(
            fn=open_explications,
            inputs=[],
            outputs=[preparation_audit_page, explications_page],
            show_progress="hidden",
        ).then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)

        back_button.click(
            fn=close_explications,
            inputs=[],
            outputs=[explications_page, preparation_audit_page],
            show_progress="hidden",
        ).then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)

        # Audit réel : seules les thématiques cochées sont exécutées.
        # L'événement d'audit est conservé pour pouvoir l'annuler.
        audit_event = (
            validate_button.click(
                fn=show_loading,
                inputs=[],
                outputs=[preparation_audit_page, chargement_page, resultats_page, audit_error, progress_html],
                show_progress="hidden",
            )
            .then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)
            .then(
                fn=run_audit,
                inputs=[website_input, files_input, selected_themes],
                outputs=[
                    chargement_page,
                    progress_html,
                    resultats_page,
                    preparation_audit_page,
                    audit_error,
                    *results_outputs,
                ],
                show_progress="hidden",
            )
        )
        audit_event.then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)

        # « Annuler l'audit » : Gradio interrompt run_audit, ce qui annule
        # la tâche d'audit (voir audit_bridge.stream_audit).
        cancel_audit_button.click(
            fn=cancel_audit,
            inputs=[],
            outputs=[chargement_page, preparation_audit_page, audit_error],
            cancels=[audit_event],
            show_progress="hidden",
        ).then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)

        home_button.click(
            fn=show_return_confirmation,
            inputs=[],
            outputs=[confirmation_panel],
            show_progress="hidden",
        )

        cancel_button.click(
            fn=hide_return_confirmation,
            inputs=[],
            outputs=[confirmation_panel],
            show_progress="hidden",
        )

        confirm_button.click(
            fn=confirm_return_home,
            inputs=[],
            outputs=[
                resultats_page,
                accueil_page,
                confirmation_panel,
                website_input,
                files_input,
                selected_themes,
                *results_outputs,
            ],
            show_progress="hidden",
        ).then(**accueil_transition).then(fn=None, js=SCROLL_TO_TOP_JS, inputs=[], outputs=[], queue=False)

    return app


if __name__ == "__main__":
    create_app().launch(**launch_options())

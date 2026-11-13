"""Construit la page de préparation d'un audit AccessiCode."""

import gradio as gr

from accessi_code.rgaa.themes import RGAA_THEMES as RGAA_THEME_CATALOG
from accessi_code.service.audit_timing import format_duration
from accessi_code.ui.audit_bridge import estimate_audit
from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.file_drop_component import create_file_drop
from accessi_code.ui.components.texte_box_component import create_textbox

# Libellés « N. Nom » issus du catalogue officiel des 13 thématiques.
RGAA_THEMES = tuple(theme.label for theme in RGAA_THEME_CATALOG)


def estimated_audit_time(selected_themes: list[str] | None, files: object = None) -> str:
    """
    Durée estimée pour les thématiques cochées.

    L'estimation additionne la durée mesurée de chaque test RGAA lors des
    audits précédents (valeur de départ pour un test jamais mesuré).
    Seule la page principale est analysée : le nombre de fichiers importés
    ne change pas la durée.
    """
    if not selected_themes:
        return "*Sélectionnez au moins une thématique pour estimer la durée.*"

    estimate = estimate_audit(selected_themes)
    if estimate is None:
        return "*Aucun test automatisé n'existe encore pour les thématiques sélectionnées.*"

    if estimate.fully_measured:
        basis = f"D'après la durée mesurée lors des audits précédents ({estimate.total_tests} tests)."
    elif estimate.measured_tests:
        basis = (
            f"D'après les audits précédents pour {estimate.measured_tests} test(s) sur "
            f"{estimate.total_tests} ; l'estimation s'affine après chaque audit."
        )
    else:
        basis = "Première estimation : elle sera affinée après le premier audit."

    return (
        f"⏱️ **Temps estimé : environ {format_duration(estimate.seconds)}** "
        f"({estimate.total_tests} tests)  \n"
        f"*{basis} La durée réelle dépend de la rapidité du serveur d'IA.*"
    )


def select_all_themes() -> list[str]:
    """Coche toutes les thématiques."""
    return list(RGAA_THEMES)


def deselect_all_themes() -> list[str]:
    """Décoche toutes les thématiques."""
    return []


def update_audit_button(selected_themes: list[str] | None):
    """Empêche de lancer un audit avec une sélection vide."""
    return gr.update(interactive=bool(selected_themes))


def build_preparation_audit_page():
    """Crée la page de saisie et la sélection des thématiques RGAA."""

    with gr.Column(
        visible=False,
        elem_id="application-page",
        elem_classes=["page-container"],
    ) as application_page:
        gr.Markdown("# AccessiCode", elem_id="application-title")

        with gr.Column(elem_id="application-content"):
            gr.Markdown("### Lien du site web :", elem_id="website-title")
            website_input = create_textbox(
                placeholder="https://www.exemple.com",
                elem_id="website-input",
            )

            gr.Markdown("### Insérer vos documents :", elem_id="documents-title")
            files_input = create_file_drop(
                file_count="multiple",
                elem_id="file-drop-zone",
            )

            gr.Markdown(
                "### Thématiques RGAA à auditer :",
                elem_id="rgaa-themes-title",
            )
            gr.Markdown(
                "Sélectionnez les thématiques à inclure dans l'audit. Toutes sont cochées par défaut.",
                elem_id="rgaa-themes-description",
            )

            with gr.Row(elem_id="rgaa-themes-actions"):
                select_all_button = create_button(
                    "Tout sélectionner",
                    elem_id="select-all-themes-button",
                )
                deselect_all_button = create_button(
                    "Tout désélectionner",
                    elem_id="deselect-all-themes-button",
                )

            selected_themes = gr.CheckboxGroup(
                choices=list(RGAA_THEMES),
                value=list(RGAA_THEMES),
                label="Thématiques sélectionnées",
                elem_id="rgaa-themes-selection",
            )

            validate_button = create_button(
                "Lancer l'audit",
                variant="primary",
                elem_id="validate-files-button",
            )
            estimated_time = gr.Markdown(
                estimated_audit_time(list(RGAA_THEMES)),
                elem_id="audit-estimated-time",
            )
            # Message affiché si l'audit ne peut pas être lancé.
            audit_error = gr.Markdown("", visible=False, elem_id="audit-error-message")

        help_button = create_button("?", elem_id="help-button")

    select_all_button.click(
        fn=select_all_themes,
        outputs=[selected_themes],
        show_progress="hidden",
    )
    deselect_all_button.click(
        fn=deselect_all_themes,
        outputs=[selected_themes],
        show_progress="hidden",
    )
    selected_themes.change(
        fn=estimated_audit_time,
        inputs=[selected_themes, files_input],
        outputs=[estimated_time],
        show_progress="hidden",
    )
    files_input.change(
        fn=estimated_audit_time,
        inputs=[selected_themes, files_input],
        outputs=[estimated_time],
        show_progress="hidden",
    )
    selected_themes.change(
        fn=update_audit_button,
        inputs=[selected_themes],
        outputs=[validate_button],
        show_progress="hidden",
    )

    return (
        application_page,
        website_input,
        files_input,
        validate_button,
        help_button,
        selected_themes,
        audit_error,
    )

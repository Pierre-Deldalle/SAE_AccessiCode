"""Construit la page de préparation d'un audit AccessiCode."""

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.file_drop_component import create_file_drop
from accessi_code.ui.components.texte_box_component import create_textbox

# Les noms et l'ordre suivent les 13 thématiques RGAA.
RGAA_THEMES = (
    "1. Images",
    "2. Cadres",
    "3. Couleurs",
    "4. Multimédia",
    "5. Tableaux",
    "6. Liens",
    "7. Scripts",
    "8. Éléments obligatoires",
    "9. Structuration de l'information",
    "10. Présentation de l'information",
    "11. Formulaires",
    "12. Navigation",
    "13. Consultation",
)

# Ordres de grandeur provisoires, en secondes, à recalibrer avec des audits réels.
# Il ne s'agit PAS de temps mesurés ou garantis par le moteur RGAA.
ESTIMATED_SECONDS_BY_THEME = {
    "1. Images": 40,
    "2. Cadres": 5,
    "3. Couleurs": 20,
    "4. Multimédia": 30,
    "5. Tableaux": 10,
    "6. Liens": 15,
    "7. Scripts": 30,
    "8. Éléments obligatoires": 15,
    "9. Structuration de l'information": 10,
    "10. Présentation de l'information": 20,
    "11. Formulaires": 20,
    "12. Navigation": 15,
    "13. Consultation": 15,
}


def _format_duration(seconds: int) -> str:
    """Formate une durée en secondes, minutes ou heures."""
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        minutes, rest = divmod(seconds, 60)
        return f"{minutes} min" + (f" {rest} s" if rest else "")
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours} h" + (f" {minutes} min" if minutes else "")


def estimated_audit_time(selected_themes: list[str] | None, files: object = None) -> str:
    """Affiche une estimation indicative pour la sélection courante.

    Cette version UI ne déclenche pas encore les tests RGAA : les coefficients
    sont des hypothèses à remplacer par des mesures du moteur d'audit.
    """
    selected = set(selected_themes or [])
    if not selected:
        return "*Sélectionnez au moins une thématique pour estimer la durée.*"

    # Les fichiers peuvent être une liste (upload multiple) ou une valeur unique.
    if isinstance(files, (list, tuple)):
        count = len([file for file in files if file is not None])
    elif files is None:
        count = 0
    else:
        count = 1

    # Une page est comptée même si le contenu provient d'une URL.
    page_count = max(1, count)
    duration = page_count * sum(
        ESTIMATED_SECONDS_BY_THEME[theme]
        for theme in RGAA_THEMES
        if theme in selected
    )
    return (
        f"⏱️ **Temps estimé : environ {_format_duration(duration)}**  "
        "\n*Estimation indicative, non mesurée. "
        "Elle sera affinée lors du branchement au moteur d'audit.*"
    )


def select_all_themes() -> list[str]:
    """Coche toutes les thématiques."""
    return list(RGAA_THEMES)


def deselect_all_themes() -> list[str]:
    """Décoche toutes les thématiques."""
    return []


def update_audit_button(selected_themes: list[str] | None):
    """Empêche de lancer une simulation avec une sélection vide."""
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
                "Sélectionnez les thématiques à inclure dans le futur audit. "
                "Toutes sont cochées par défaut.",
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
    )

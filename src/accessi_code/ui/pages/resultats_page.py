"""Construit la page de résultats de l'audit AccessiCode.

Les cartes sont alimentées par des ThemeSummary (service/theme_summary.py),
calculés à partir de l'AuditResult du moteur. Cette page ne dépend ni du
moteur RGAA ni d'Ollama.
"""

import gradio as gr

from accessi_code.rgaa.themes import RGAA_THEMES
from accessi_code.service.theme_summary import ThemeSummary
from accessi_code.ui.results_view import (
    DEFAULT_THEME_DETAIL,
    LEGEND_TEXT,
    SCORE_CSS,
    build_notices,
    build_theme_detail,
    card_classes,
    initial_card_classes,
    priority_label,
    score_category,
    show_detail,
)

__all__ = [
    "DEFAULT_THEME_DETAIL",
    "SCORE_CSS",
    "build_resultats_page",
    "build_theme_detail",
    "priority_label",
    "reset_updates",
    "results_updates",
    "score_category",
]


def results_updates(summaries: tuple[ThemeSummary, ...], notices: list[str]) -> list:
    """
    Mises à jour Gradio, dans l'ordre :
    état des résultats, avertissements, détail, puis les 13 cartes.
    """
    notices_md = build_notices(notices)
    return [
        summaries,
        gr.update(value=notices_md, visible=bool(notices_md)),
        gr.update(value=DEFAULT_THEME_DETAIL),
        *[gr.update(value=s.theme.label, elem_classes=card_classes(s)) for s in summaries],
    ]


def reset_updates() -> list:
    """Mises à jour remettant la page dans son état initial (même ordre)."""
    return [
        (),
        gr.update(value="", visible=False),
        gr.update(value=DEFAULT_THEME_DETAIL),
        *[gr.update(elem_classes=initial_card_classes()) for _ in RGAA_THEMES],
    ]


def build_resultats_page():
    """Construit la page des résultats et sa confirmation de retour."""
    results_state = gr.State(())

    with gr.Column(
        visible=False,
        elem_id="resultats-page",
        elem_classes=["page-container"],
    ) as resultats_page:
        with gr.Row(elem_id="resultats-header", equal_height=False):
            home_button = gr.Button(
                "← Nouvel audit",
                variant="secondary",
                elem_id="resultats-home-button",
            )

        gr.Markdown(
            "# Votre audit d'accessibilité",
            elem_id="resultats-title",
        )

        gr.Markdown(LEGEND_TEXT, elem_id="resultats-demo-notice")

        audit_notices = gr.Markdown("", visible=False, elem_id="resultats-audit-notices")

        theme_buttons = []
        with gr.Column(elem_id="resultats-themes"):
            for start, end in ((0, 5), (5, 10), (10, 13)):
                with gr.Row(
                    elem_classes=["resultats-theme-row"],
                    equal_height=True,
                ):
                    for theme in RGAA_THEMES[start:end]:
                        with gr.Column(
                            scale=1,
                            min_width=145,
                            elem_classes=["resultats-theme-column"],
                        ):
                            # Le contenu du cercle est fourni par les classes
                            # theme-score-* (voir SCORE_CSS).
                            button = gr.Button(
                                value=theme.label,
                                variant="secondary",
                                elem_id=f"theme-card-{theme.number}",
                                elem_classes=initial_card_classes(),
                            )
                            theme_buttons.append(button)

        with gr.Column(elem_id="resultats-detail-section"):
            gr.Markdown(
                "## Détail du thème",
                elem_id="resultats-detail-title",
            )
            theme_detail = gr.Markdown(
                DEFAULT_THEME_DETAIL,
                elem_id="resultats-detail-content",
            )

        with gr.Column(
            visible=False,
            elem_id="resultats-confirmation-overlay",
        ) as confirmation_panel:
            with gr.Column(elem_id="resultats-confirmation-dialog"):
                gr.Markdown(
                    "## Retourner à l'accueil ?",
                    elem_id="resultats-confirmation-title",
                )
                gr.Markdown(
                    "Voulez-vous vraiment retourner à l'accueil ? **Les résultats de l'audit en cours seront perdus.**",
                    elem_id="resultats-confirmation-message",
                )
                with gr.Row(elem_id="resultats-confirmation-actions"):
                    cancel_button = gr.Button(
                        "Annuler",
                        variant="secondary",
                        elem_id="resultats-cancel-button",
                    )
                    confirm_button = gr.Button(
                        "Confirmer le retour",
                        variant="primary",
                        elem_id="resultats-confirm-button",
                    )

    for index, button in enumerate(theme_buttons):
        button.click(
            fn=lambda summaries, i=index: show_detail(summaries, i),
            inputs=[results_state],
            outputs=[theme_detail],
            show_progress="hidden",
        )

    return (
        resultats_page,
        theme_buttons,
        theme_detail,
        home_button,
        confirmation_panel,
        cancel_button,
        confirm_button,
        results_state,
        audit_notices,
    )


"""Construit la page de résultats de l'audit AccessiCode."""

from dataclasses import dataclass

import gradio as gr


@dataclass(frozen=True)
class ThemeDemo:
    """Données fictives pour une carte de thème RGAA."""

    numero: int
    nom: str
    score: int


# Résultats fictifs pour tester l'interface.
# Ces scores ne représentent pas un véritable audit RGAA.
THEMES_DEMO = (
    ThemeDemo(1, "Images", 11),
    ThemeDemo(2, "Cadres", 64),
    ThemeDemo(3, "Couleurs", 100),
    ThemeDemo(4, "Multimédia", 28),
    ThemeDemo(5, "Tableaux", 69),
    ThemeDemo(6, "Liens", 81),
    ThemeDemo(7, "Scripts", 100),
    ThemeDemo(8, "Éléments obligatoires", 100),
    ThemeDemo(9, "Structuration de l'information", 100),
    ThemeDemo(10, "Présentation de l'information", 52),
    ThemeDemo(11, "Formulaires", 42),
    ThemeDemo(12, "Navigation", 100),
    ThemeDemo(13, "Consultation", 78),
)


DEFAULT_THEME_DETAIL = (
    "Sélectionnez une carte ci-dessus pour afficher "
    "les informations du thème."
)


def score_category(score: int) -> str:
    """Détermine la couleur associée au score fictif."""

    if not 0 <= score <= 100:
        raise ValueError("Le score doit être compris entre 0 et 100.")

    if score <= 35:
        return "danger"

    if score <= 65:
        return "warning"

    return "success"


def priority_label(score: int) -> str:
    """Retourne une indication compréhensible sans la couleur."""

    category = score_category(score)

    if category == "danger":
        return "Priorité élevée"

    if category == "warning":
        return "À surveiller"

    return "Satisfaisant"


def build_theme_detail(theme: ThemeDemo) -> str:
    """Construit le détail fictif du thème sélectionné."""

    return (
        f"## {theme.numero}. {theme.nom}\n\n"
        "**Mode démonstration — aucun audit réel n'a encore été chargé.**\n\n"
        f"**Score fictif :** {theme.score} %  \n"
        f"**Indication visuelle :** {priority_label(theme.score)}\n\n"
        "### Détail de l'analyse\n\n"
        "Les résultats des critères RGAA de ce thème apparaîtront ici "
        "après le raccordement du moteur d'audit.\n\n"
        "Cette section présentera les éléments concernés, les tests "
        "effectués, les problèmes détectés et les recommandations.\n\n"
        "**Attention :** le score affiché ici sert uniquement à "
        "tester l'interface. Il ne constitue pas une mesure de "
        "conformité RGAA."
    )


def build_resultats_page():
    """
    Construit la page des résultats et sa confirmation de retour.

    Retourne les composants nécessaires à la navigation Gradio.
    """

    with gr.Column(
        visible=False,
        elem_id="resultats-page",
        elem_classes=["page-container"],
    ) as resultats_page:

        # En-tête et bouton de retour.
        with gr.Row(
            elem_id="resultats-header",
            equal_height=False,
        ):
            home_button = gr.Button(
                "← Nouvel audit",
                variant="secondary",
                elem_id="resultats-home-button",
            )

        gr.Markdown(
            "# Votre audit d'accessibilité",
            elem_id="resultats-title",
        )

        gr.Markdown(
            "Démonstration de l'interface — scores fictifs, "
            "en attente du raccordement aux résultats d'audit.",
            elem_id="resultats-demo-notice",
        )

        # Cartes des 13 thèmes RGAA.
        theme_buttons = []

        with gr.Column(elem_id="resultats-themes"):
            for start, end in ((0, 5), (5, 10), (10, 13)):
                with gr.Row(
                    elem_classes=["resultats-theme-row"],
                    equal_height=True,
                ):
                    for theme in THEMES_DEMO[start:end]:
                        with gr.Column(
                            scale=1,
                            min_width=145,
                            elem_classes=["resultats-theme-column"],
                        ):
                            button = gr.Button(
                                value=(
                                    f"{theme.numero}. {theme.nom}\n"
                                    f"{theme.score} %"
                                ),
                                variant="secondary",
                                elem_id=f"theme-card-{theme.numero}",
                                elem_classes=[
                                    "resultats-theme-card",
                                    f"theme-score-{theme.score}",
                                    f"theme-status-{score_category(theme.score)}",
                                ],
                            )
                            theme_buttons.append(button)

        # Détail du thème sélectionné.
        with gr.Column(elem_id="resultats-detail-section"):
            gr.Markdown(
                "## Détail du thème",
                elem_id="resultats-detail-title",
            )

            theme_detail = gr.Markdown(
                DEFAULT_THEME_DETAIL,
                elem_id="resultats-detail-content",
            )

        gr.Markdown(
            "Codes de couleur : **rouge (0–35)** · "
            "**jaune (36–65)** · **vert (66–100)**. "
            "Ces seuils sont des indicateurs visuels du projet, "
            "pas une échelle officielle du RGAA.",
            elem_id="resultats-legend",
        )

        # Confirmation de retour.
        # Invisible tant que l'utilisateur n'a pas cliqué
        # sur « Nouvel audit ».
        with gr.Column(
            visible=False,
            elem_id="resultats-confirmation-overlay",
        ) as confirmation_panel:

            with gr.Column(
                elem_id="resultats-confirmation-dialog",
            ):
                gr.Markdown(
                    "## Retourner à l'accueil ?",
                    elem_id="resultats-confirmation-title",
                )

                gr.Markdown(
                    "Voulez-vous vraiment retourner à l'accueil ? "
                    "**Les résultats de l'audit en cours seront perdus.**",
                    elem_id="resultats-confirmation-message",
                )

                with gr.Row(
                    elem_id="resultats-confirmation-actions",
                ):
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

    # Affichage des détails lors du clic sur une carte.
    for theme, button in zip(
        THEMES_DEMO,
        theme_buttons,
        strict=True,
    ):
        button.click(
            fn=lambda selected=theme: build_theme_detail(selected),
            inputs=[],
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
    )


"""Construit la page d'explications de l'application AccessiCode."""

from pathlib import Path

import gradio as gr

from accessi_code.ui.components.bouton_component import create_button
from accessi_code.ui.components.image_component import create_image


# Chemin vers les ressources graphiques de l'application.
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_explications_page():
    """Crée la page d'aide et de présentation d'AccessiCode."""

    with gr.Column(
        visible=False,
        elem_id="explications-page",
        elem_classes=["page-container"],
    ) as explications_page:

        # Navigation vers la page précédente.
        back_button = create_button(
            "← Retour",
            elem_id="back-button",
        )

        # Titre principal.
        gr.Markdown(
            "# AccessiCode, c'est quoi ?",
            elem_id="explications-title",
        )

        # Présentation : texte à gauche, logo à droite.
        with gr.Row(elem_id="explications-top"):

            gr.Markdown(
                """
**AccessiCode** est une application d'aide à l'audit
d'accessibilité des pages web.

Elle permet d'analyser des fichiers HTML et leurs ressources
associées afin de repérer certains problèmes d'accessibilité
au regard du **Référentiel général d'amélioration de
l'accessibilité (RGAA)**.

L'objectif est de faciliter les premières vérifications
techniques et d'identifier les éléments qui nécessitent
une correction ou un examen plus approfondi.
                """,
                elem_id="explications-text-top",
            )

            create_image(
                ASSETS_DIR / "logo_complet.png",
                width=150,
                elem_id="explications-logo",
            )

        # Explications pratiques.
        gr.Markdown(
            """
## Comment utiliser AccessiCode ?

**1. Préparer les documents**

Depuis la page principale, importez les fichiers de votre
page web à analyser. Vous pouvez notamment fournir un
document HTML et les feuilles CSS qui lui sont associées.

Pour une analyse fidèle des couleurs, veillez à conserver
les ressources nécessaires à l'affichage de la page.

**2. Lancer l'audit**

Cliquez sur **« Lancer les audits »**. AccessiCode prépare
les fichiers, extrait les informations nécessaires et exécute
les contrôles RGAA disponibles.

Certains contrôles, notamment ceux liés aux couleurs,
utilisent les styles calculés par un navigateur.

**3. Consulter les résultats**

Le rapport permet d'identifier les tests effectués
et les éventuels problèmes détectés.

Les statuts utilisés indiquent notamment :

- **PASS** : le test a réussi sur les éléments contrôlés ;
- **FAIL** : une non-conformité a été détectée ;
- **NEEDS_REVIEW** : une vérification humaine est nécessaire ;
- **NOT_TESTED** : le test n'a pas pu être exécuté ;
- **NOT_APPLICABLE** : le test ne concerne pas les éléments évalués.

## Une aide à l'audit, pas une certification

AccessiCode automatise une partie des vérifications, mais
ne remplace pas un audit d'accessibilité complet.

Certaines situations demandent une interprétation humaine :
par exemple, déterminer si une bordure est essentielle
pour identifier un champ, ou vérifier le rendu réel
d'un composant interactif.

Un résultat positif sur les contrôles réalisés
ne garantit donc pas, à lui seul, la conformité RGAA
de l'ensemble du site.
            """,
            elem_id="explications-text-bottom",
        )

    return (
        explications_page,
        back_button,
    )

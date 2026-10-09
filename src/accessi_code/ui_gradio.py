from __future__ import annotations

import html
import json
import threading
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import gradio as gr
import webview

from accessi_code.config import settings
from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import Test111
from accessi_code.service.audit_service import AuditService
from accessi_code.service.default_services import build_default_audit_services

# ---------------------------------------------------------------------------
# Configuration générale
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]

WORKSPACE_DIR = ROOT_DIR / "workspace"


# ---------------------------------------------------------------------------
# Construction du nouveau pipeline AccessiCode
# ---------------------------------------------------------------------------

context_builder = AuditContextBuilder(
    workspace_root=WORKSPACE_DIR,
)

audit_services = build_default_audit_services(
    ollama_host=settings.OLLAMA_HOST,
    llm_model=settings.LLM_MODEL,
    vlm_model=settings.VLM_MODEL,
)

audit_registry = build_default_registry()

audit_service = AuditService(
    registry=audit_registry,
    services=audit_services,
)


# Le deuxième onglet de l'interface permet toujours de tester directement
# une image isolée.
#
# On utilise le même moteur que pour l'audit HTML, mais avec un registre
# limité au test RGAA 1.1.1, qui est le contrôle actuellement pertinent
# pour une image HTML isolée.
image_registry = TestRegistry(
    [
        Test111(),
    ]
)

image_audit_service = AuditService(
    registry=image_registry,
    services=audit_services,
)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _uploaded_file_path(file: Any) -> Path:
    """
    Retourne le chemin local d'un fichier fourni par Gradio.
    """
    if isinstance(
        file,
        (str, Path),
    ):
        return Path(file)

    path = getattr(
        file,
        "name",
        file,
    )

    return Path(str(path))


def _expand_uploaded_paths(uploaded_files: list[Any]) -> list[Path]:
    """
    Développe les fichiers reçus par Gradio, y compris un dossier importé.

    Le navigateur ne peut pas déduire les ressources voisines d'un fichier
    HTML envoyé seul. Le mode d'import dossier fournit donc explicitement
    tous les fichiers à conserver dans le contexte d'audit.
    """
    paths: list[Path] = []
    seen: set[Path] = set()

    for file in uploaded_files:
        if file is None:
            continue

        path = _uploaded_file_path(file)

        candidates = path.rglob("*") if path.is_dir() else [path]

        for candidate in candidates:
            if not candidate.is_file():
                continue

            resolved = candidate.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)
            paths.append(candidate)

    return paths


def _json_default(value: Any) -> Any:
    """
    Conversion des objets AccessiCode en valeurs sérialisables en JSON.
    """
    if isinstance(
        value,
        Enum,
    ):
        return value.value

    if isinstance(
        value,
        Path,
    ):
        return str(value)

    if is_dataclass(value):
        return asdict(value)

    raise TypeError(f"Objet non sérialisable en JSON : {type(value).__name__}")


def _format_json(value: Any) -> str:
    """
    Produit le rapport JSON lisible affiché dans l'interface.
    """
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=_json_default,
    )


def _result_table(audit_result: Any) -> list[list[Any]]:
    """
    Transforme un AuditResult en lignes compatibles avec le tableau Gradio.
    """
    rows: list[list[Any]] = []

    for criterion in audit_result.criteria:
        for test_result in criterion.tests:
            rows.append(
                [
                    test_result.test_id,
                    test_result.status.value,
                    test_result.tested_elements,
                    test_result.summary,
                    len(test_result.findings),
                ]
            )

    return rows


def _build_context_from_html_text(
    html_text: str,
):
    """
    Construit un AuditContext lorsqu'un utilisateur colle directement
    du HTML dans la zone de texte.
    """
    with TemporaryDirectory(
        prefix="accessicode_ui_",
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)

        html_path = temporary_path / "index.html"

        html_path.write_text(
            html_text,
            encoding="utf-8",
        )

        return context_builder.build(
            [
                html_path,
            ]
        )


def _build_context_from_uploaded_files(
    uploaded_files: list[Any],
):
    """
    Construit un AuditContext à partir des fichiers reçus par Gradio.
    """
    paths = _expand_uploaded_paths(uploaded_files)

    return context_builder.build(paths)


# ---------------------------------------------------------------------------
# Audit HTML
# ---------------------------------------------------------------------------


async def run_audit(
    html_text: str,
    file_obj,
):
    """
    Fonction d'audit déclenchée par l'onglet HTML.

    Le pipeline utilisé est désormais exactement le même que celui validé
    dans debug_rgaa.py :

        fichiers
        -> AuditContext
        -> TestRegistry
        -> AuditService
        -> TestRunner
        -> AuditResult
    """
    uploaded_files = (
        file_obj
        if isinstance(
            file_obj,
            list,
        )
        else [
            file_obj,
        ]
    )

    uploaded_files = [file for file in uploaded_files if file is not None]

    html_file = next(
        (file for file in uploaded_files if str(_uploaded_file_path(file)).lower().endswith(".html")),
        None,
    )

    try:
        if html_file is not None:
            context = _build_context_from_uploaded_files(uploaded_files)

        elif html_text and html_text.strip():
            context = _build_context_from_html_text(html_text)

        else:
            return (
                "Veuillez coller du HTML ou charger un fichier .html.",
                [],
            )

        audit_result = await audit_service.audit(context)

    except Exception as error:
        return (
            (f"Erreur lors de l'exécution de l'audit : {error}"),
            [],
        )

    table_data = _result_table(audit_result)

    json_formatted = _format_json(audit_result)

    return (
        json_formatted,
        table_data,
    )


# ---------------------------------------------------------------------------
# Audit VLM d'une image isolée
# ---------------------------------------------------------------------------


async def test_vlm(
    image_file,
):
    """
    Lance le test RGAA 1.1.1 sur une image isolée en utilisant le moteur
    AccessiCode actuel et les mêmes services IA que l'audit HTML.

    Une petite page HTML temporaire est créée afin que l'image puisse entrer
    dans le pipeline normal AuditContext -> RGAATest.
    """
    if image_file is None:
        return (
            "Veuillez charger une image.",
            [],
        )

    try:
        image_path = _uploaded_file_path(image_file)

        if not image_path.is_file():
            return (
                (f"Le fichier image fourni est introuvable : {image_path}"),
                [],
            )

        with TemporaryDirectory(
            prefix="accessicode_vlm_",
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)

            html_path = temporary_path / "index.html"

            image_name = html.escape(
                image_path.name,
                quote=True,
            )

            html_source = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Audit d'image AccessiCode</title>
</head>
<body>
    <img src="{image_name}">
</body>
</html>
"""

            html_path.write_text(
                html_source,
                encoding="utf-8",
            )

            context = context_builder.build(
                [
                    html_path,
                    image_path,
                ]
            )

        audit_result = await image_audit_service.audit(context)

        table_data = _result_table(audit_result)

        return (
            _format_json(audit_result),
            table_data,
        )

    except Exception as error:
        return (
            (f"Erreur lors de l'exécution du test VLM : {error}"),
            [],
        )


# ---------------------------------------------------------------------------
# Interface Gradio
# ---------------------------------------------------------------------------


def build_ui():
    """
    Construction de l'interface Gradio Blocks.
    """
    with gr.Blocks(
        title="AccessiCode - Audit Accessibilité A11y",
    ) as demo:
        gr.Markdown("# ♿ AccessiCode - Audit d'accessibilité Web")

        gr.Markdown("Application de bureau pour l'audit d'accessibilité des images HTML.")

        with gr.Tabs():
            with gr.Tab(
                "LLM - Audit HTML",
            ):
                with gr.Row():
                    with gr.Column(
                        scale=1,
                    ):
                        html_input = gr.Textbox(
                            lines=12,
                            placeholder=("Collez votre code HTML ici..."),
                            label="Code HTML à analyser",
                        )

                        file_input = gr.File(
                            label=(
                                "Ou chargez le dossier du site "
                                "(ex: test_files/perfect_site)"
                            ),
                            file_count="directory",
                            type="filepath",
                        )

                        btn_audit = gr.Button(
                            "🔍 Lancer l'audit LLM",
                            variant="primary",
                        )

                    with gr.Column(
                        scale=1,
                    ):
                        dataframe_output = gr.Dataframe(
                            headers=[
                                "Critère",
                                "Statut",
                                "Éléments testés",
                                "Résumé",
                                "Anomalies",
                            ],
                            label="Résultats des critères DOM",
                        )

                        json_output = gr.Code(
                            language="json",
                            label=("Rapport JSON Détaillé (DOM + LLM)"),
                        )

            with gr.Tab(
                "VLM - Audit d'image",
            ):
                with gr.Row():
                    with gr.Column(
                        scale=1,
                    ):
                        vlm_image_input = gr.File(
                            label="Image à analyser",
                            file_types=[
                                "image",
                            ],
                            type="filepath",
                        )

                        btn_vlm = gr.Button(
                            "🔍 Lancer l'audit VLM",
                            variant="primary",
                        )

                    with gr.Column(
                        scale=1,
                    ):
                        vlm_dataframe_output = gr.Dataframe(
                            headers=[
                                "Critère",
                                "Statut",
                                "Éléments testés",
                                "Résumé",
                                "Anomalies",
                            ],
                            label="Résultats de l'audit VLM",
                        )

                        vlm_output = gr.Textbox(
                            label="Réponse du VLM",
                            lines=12,
                        )

        btn_audit.click(
            fn=run_audit,
            inputs=[
                html_input,
                file_input,
            ],
            outputs=[
                json_output,
                dataframe_output,
            ],
        )

        btn_vlm.click(
            fn=test_vlm,
            inputs=[
                vlm_image_input,
            ],
            outputs=[
                vlm_output,
                vlm_dataframe_output,
            ],
        )

    return demo


# ---------------------------------------------------------------------------
# Application bureau
# ---------------------------------------------------------------------------


def launch_desktop():
    """
    Lancement du serveur Gradio en arrière-plan puis ouverture de la
    fenêtre native pywebview.
    """
    demo = build_ui()

    thread = threading.Thread(
        target=lambda: demo.launch(
            server_name="127.0.0.1",
            server_port=7860,
            prevent_thread_lock=True,
            show_error=False,
        ),
        daemon=True,
    )

    thread.start()

    time.sleep(1.2)

    webview.create_window(
        title="AccessiCode - Desktop App",
        url="http://127.0.0.1:7860",
        width=1280,
        height=850,
        resizable=True,
    )

    webview.start()


if __name__ == "__main__":
    launch_desktop()

"""Interface Gradio et application de bureau AccessiCode."""

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
from accessi_code.input.context_enricher import ContextEnricher
from accessi_code.input.file_classifier import is_html_file
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import Test111
from accessi_code.service.audit_service import AuditService
from accessi_code.service.default_services import build_default_audit_services

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT_DIR / "workspace"

context_builder = AuditContextBuilder(
    workspace_root=WORKSPACE_DIR,
)

audit_services = build_default_audit_services(
    ollama_host=settings.OLLAMA_HOST,
    llm_model=settings.LLM_MODEL,
    vlm_model=settings.VLM_MODEL,
)

audit_registry = build_default_registry()

# L'enrichisseur Playwright est activé pour les audits HTML/CSS.
audit_service = AuditService(
    registry=audit_registry,
    services=audit_services,
    context_enricher=ContextEnricher(),
)

# L'audit VLM reste indépendant de l'enrichissement Playwright.
image_registry = TestRegistry([Test111()])

image_audit_service = AuditService(
    registry=image_registry,
    services=audit_services,
)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _uploaded_file_path(file: Any) -> Path:
    """Retourne le chemin local d'un fichier reçu par Gradio."""

    path = getattr(file, "name", file)
    return Path(str(path))


def _json_default(value: Any) -> Any:
    """Convertit les objets AccessiCode en valeurs JSON."""

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return asdict(value)

    raise TypeError(f"Objet non sérialisable en JSON : {type(value).__name__}")


def _format_json(value: Any) -> str:
    """Produit une représentation JSON lisible."""

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=_json_default,
    )


def _result_table(audit_result: Any) -> list[list[Any]]:
    """Transforme les résultats RGAA en lignes Gradio."""

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


# ---------------------------------------------------------------------------
# Construction des contextes
# ---------------------------------------------------------------------------


def _build_context_from_html_text(html_text: str):
    """Construit un contexte depuis du HTML collé."""

    with TemporaryDirectory(
        prefix="accessicode_ui_",
    ) as temporary_directory:
        html_path = Path(temporary_directory) / "index.html"

        html_path.write_text(
            html_text,
            encoding="utf-8",
        )

        return context_builder.build([html_path])


def _build_context_from_uploaded_files(
    uploaded_files: list[Any],
):
    """Construit un contexte depuis des fichiers individuels."""

    paths = [_uploaded_file_path(file) for file in uploaded_files if file is not None]

    return context_builder.build(paths)


def _build_context_from_site_directory(
    directory_path: str,
):
    """
    Construit un contexte depuis un dossier local.

    L'arborescence est conservée grâce au paramètre site_root.
    Ce mode est destiné à l'application exécutée localement.
    """

    site_root = Path(directory_path.strip().strip('"')).expanduser().resolve()

    if not site_root.is_dir():
        raise NotADirectoryError(f"Le dossier du site est introuvable : {site_root}")

    # Ne pas importer les dossiers de développement ni les liens symboliques.
    excluded_directories = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
    }

    input_files = sorted(
        (
            path
            for path in site_root.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not any(part in excluded_directories for part in path.relative_to(site_root).parts)
        ),
        key=lambda path: str(path),
    )

    if not input_files:
        raise ValueError("Le dossier sélectionné ne contient aucun fichier.")

    html_files = [path for path in input_files if is_html_file(path)]

    if not html_files:
        raise ValueError("Le dossier ne contient aucun fichier HTML.")

    # Choisir index.html à la racine s'il existe.
    # Sinon, prendre le premier HTML trouvé.
    main_html = next(
        (path for path in html_files if path.parent == site_root and path.name.lower() in {"index.html", "index.htm"}),
        html_files[0],
    )

    ordered_files = [
        main_html,
        *(path for path in input_files if path != main_html),
    ]

    return context_builder.build(
        ordered_files,
        site_root=site_root,
    )


# ---------------------------------------------------------------------------
# Audit HTML / CSS
# ---------------------------------------------------------------------------


async def run_audit(
    html_text: str,
    file_obj: Any,
    site_directory: str,
):
    """
    Lance un audit RGAA.

    Priorité des entrées :
    1. dossier local ;
    2. fichiers importés ;
    3. HTML collé.

    Si ContextEnricher est configuré, AuditService exécute
    Playwright avant les tests RGAA.
    """

    uploaded_files = file_obj if isinstance(file_obj, list) else [file_obj]

    uploaded_files = [file for file in uploaded_files if file is not None]

    try:
        if site_directory and site_directory.strip():
            context = _build_context_from_site_directory(site_directory)

        elif uploaded_files:
            paths = [_uploaded_file_path(file) for file in uploaded_files]

            if not any(is_html_file(path) for path in paths):
                raise ValueError("Veuillez importer au moins un fichier HTML.")

            context = _build_context_from_uploaded_files(uploaded_files)

        elif html_text and html_text.strip():
            context = _build_context_from_html_text(html_text)

        else:
            return (
                "Veuillez fournir du HTML, des fichiers ou un dossier.",
                [],
            )

        # L'enrichissement Playwright est appelé avant les tests RGAA.
        audit_result = await audit_service.audit(context)

        # Diagnostic temporaire de l'extraction Playwright.
        report = audit_service.last_enrichment_report

        if report is None:
            print("[Playwright] Aucun rapport d'enrichissement.", flush=True)

        elif report.error is not None:
            print(f"[Playwright] ERREUR : {report.error}", flush=True)

        else:
            print(
                "[Playwright] Extraction réussie : "
                f"{report.total} fragments observés, "
                f"{report.usable_count} candidats, "
                f"{report.review_count} à vérifier.",
                flush=True,
            )

    except Exception as error:
        return (
            f"Erreur lors de l'exécution de l'audit : {error}",
            [],
        )

    return (
        _format_json(audit_result),
        _result_table(audit_result),
    )


# ---------------------------------------------------------------------------
# Audit VLM d'une image isolée
# ---------------------------------------------------------------------------


async def test_vlm(image_file: Any):
    """Lance le test RGAA 1.1.1 sur une image isolée."""

    if image_file is None:
        return (
            "Veuillez charger une image.",
            [],
        )

    try:
        image_path = _uploaded_file_path(image_file)

        if not image_path.is_file():
            return (
                f"Le fichier image est introuvable : {image_path}",
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

            context = context_builder.build([html_path, image_path])

        audit_result = await image_audit_service.audit(context)

        return (
            _format_json(audit_result),
            _result_table(audit_result),
        )

    except Exception as error:
        return (
            f"Erreur lors de l'exécution du test VLM : {error}",
            [],
        )


# ---------------------------------------------------------------------------
# Interface Gradio
# ---------------------------------------------------------------------------


def build_ui():
    """Construit l'interface AccessiCode."""

    with gr.Blocks(
        title="AccessiCode - Audit d'accessibilité Web",
    ) as demo:
        gr.Markdown("# ♿ AccessiCode — Audit d'accessibilité Web")

        gr.Markdown("Analyse de pages HTML et de leurs ressources, selon les contrôles RGAA implémentés.")

        with gr.Tabs():
            # -----------------------------------------------------------
            # Audit d'un site HTML / CSS
            # -----------------------------------------------------------

            with gr.Tab("Audit HTML / CSS"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Source à analyser")

                        html_input = gr.Textbox(
                            lines=9,
                            placeholder="Collez votre HTML ici...",
                            label="Code HTML",
                        )

                        file_input = gr.File(
                            label=("Ou importer des fichiers HTML, CSS et images"),
                            file_count="multiple",
                            file_types=[
                                ".html",
                                ".htm",
                                ".css",
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".webp",
                                ".gif",
                                ".svg",
                            ],
                            type="filepath",
                        )

                        gr.Markdown("### Importer un site complet")

                        site_directory = gr.Textbox(
                            label="Chemin local du dossier du site",
                            placeholder=(
                                r"C:\Users\etudiant\Documents"
                                r"\SAE\SAE_AccessiCode\test_files\color_site"
                            ),
                            info=(
                                "Mode application de bureau : "
                                "le dossier doit exister sur "
                                "l'ordinateur exécutant AccessiCode."
                            ),
                        )

                        gr.Markdown(
                            "Si plusieurs sources sont renseignées, "
                            "le dossier local est prioritaire, puis "
                            "les fichiers importés, puis le HTML collé."
                        )

                        btn_audit = gr.Button(
                            "🔍 Lancer l'audit RGAA",
                            variant="primary",
                        )

                    with gr.Column(scale=1):
                        dataframe_output = gr.Dataframe(
                            headers=[
                                "Test RGAA",
                                "Statut",
                                "Éléments testés",
                                "Résumé",
                                "Anomalies",
                            ],
                            label="Résultats des contrôles",
                        )

                        json_output = gr.Code(
                            language="json",
                            label="Rapport JSON détaillé",
                        )

            # -----------------------------------------------------------
            # Audit d'une image isolée
            # -----------------------------------------------------------

            with gr.Tab("VLM - Audit d'image"):
                with gr.Row():
                    with gr.Column(scale=1):
                        vlm_image_input = gr.File(
                            label="Image à analyser",
                            file_types=["image"],
                            type="filepath",
                        )

                        btn_vlm = gr.Button(
                            "🔍 Lancer l'audit VLM",
                            variant="primary",
                        )

                    with gr.Column(scale=1):
                        vlm_dataframe_output = gr.Dataframe(
                            headers=[
                                "Test RGAA",
                                "Statut",
                                "Éléments testés",
                                "Résumé",
                                "Anomalies",
                            ],
                            label="Résultats de l'audit VLM",
                        )

                        vlm_output = gr.Textbox(
                            label="Rapport VLM",
                            lines=12,
                        )

        btn_audit.click(
            fn=run_audit,
            inputs=[
                html_input,
                file_input,
                site_directory,
            ],
            outputs=[
                json_output,
                dataframe_output,
            ],
        )

        btn_vlm.click(
            fn=test_vlm,
            inputs=[vlm_image_input],
            outputs=[
                vlm_output,
                vlm_dataframe_output,
            ],
        )

    return demo


# ---------------------------------------------------------------------------
# Application de bureau
# ---------------------------------------------------------------------------


def launch_desktop():
    """Démarre Gradio et ouvre la fenêtre native pywebview."""

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

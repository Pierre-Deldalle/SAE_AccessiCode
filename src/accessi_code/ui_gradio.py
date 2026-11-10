"""Interface Gradio historique d'AccessiCode (conservée pendant l'intégration).

Cette interface peut être retirée après validation de l'interface principale
et du pont d'audit ``accessi_code.ui.audit_bridge``.
"""

from __future__ import annotations

import html
import json
import logging
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

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT_DIR / "workspace"

context_builder = AuditContextBuilder(workspace_root=WORKSPACE_DIR)

audit_services = build_default_audit_services(
    ollama_host=settings.OLLAMA_HOST,
    llm_model=settings.LLM_MODEL,
    vlm_model=settings.VLM_MODEL,
)

audit_registry = build_default_registry()

audit_service = AuditService(
    registry=audit_registry,
    services=audit_services,
    context_enricher=ContextEnricher(),
)

# Audit de l'image isolée : seulement le test 1.1.1, sans enrichisseur.
image_registry = TestRegistry([Test111()])
image_audit_service = AuditService(
    registry=image_registry,
    services=audit_services,
)


def _uploaded_file_path(file: Any) -> Path:
    """Retrouve le chemin d'un fichier retourné par Gradio."""
    if isinstance(file, (str, Path)):
        return Path(file)
    return Path(str(getattr(file, "name", file)))


def _expand_uploaded_paths(uploaded_files: list[Any]) -> list[Path]:
    """Déplie les dossiers téléchargés et évite les chemins en double."""
    paths: list[Path] = []
    seen: set[Path] = set()

    for file in uploaded_files:
        if file is None:
            continue

        path = _uploaded_file_path(file)
        candidates = path.rglob("*") if path.is_dir() else [path]

        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(candidate)

    return paths


def _json_default(value: Any) -> Any:
    """Convertit les valeurs propres au moteur en valeurs JSON."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Objet non sérialisable en JSON : {type(value).__name__}")


def _format_json(value: Any) -> str:
    """Formate un rapport d'audit en JSON lisible."""
    return json.dumps(value, indent=2, ensure_ascii=False, default=_json_default)


def _result_table(audit_result: Any) -> list[list[Any]]:
    """Transforme les résultats des tests en lignes Gradio."""
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


def _build_context_from_html_text(html_text: str):
    """Construit un contexte depuis une source HTML saisie."""
    with TemporaryDirectory(prefix="accessicode_ui_") as temporary_directory:
        html_path = Path(temporary_directory) / "index.html"
        html_path.write_text(html_text, encoding="utf-8")
        return context_builder.build([html_path])


def _build_context_from_uploaded_files(uploaded_files: list[Any]):
    """Construit un contexte depuis des fichiers ou dossiers reçus par Gradio."""
    paths = _expand_uploaded_paths(uploaded_files)
    if not any(is_html_file(path) for path in paths):
        raise ValueError("Veuillez importer au moins un fichier HTML.")
    return context_builder.build(paths)


def _build_context_from_site_directory(directory_path: str):
    """Construit un contexte depuis un dossier local en préservant l'arborescence."""
    site_root = Path(directory_path.strip().strip('"')).expanduser().resolve()
    if not site_root.is_dir():
        raise NotADirectoryError(f"Le dossier du site est introuvable : {site_root}")

    excluded_directories = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    input_files = sorted(
        (
            path
            for path in site_root.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not any(
                part in excluded_directories
                for part in path.relative_to(site_root).parts
            )
        ),
        key=str,
    )
    if not input_files:
        raise ValueError("Le dossier sélectionné ne contient aucun fichier.")

    html_files = [path for path in input_files if is_html_file(path)]
    if not html_files:
        raise ValueError("Le dossier ne contient aucun fichier HTML.")

    main_html = next(
        (
            path
            for path in html_files
            if path.parent == site_root
            and path.name.lower() in {"index.html", "index.htm"}
        ),
        html_files[0],
    )
    ordered_files = [main_html, *(path for path in input_files if path != main_html)]
    return context_builder.build(ordered_files, site_root=site_root)


async def run_audit(
    html_text: str,
    file_obj: Any,
    site_directory: str,
    folder_obj: Any,
    progress: gr.Progress = gr.Progress(),
):
    """Exécute l'audit HTML en conservant les différents modes d'importation.

    Priorité : dossier local, dossier envoyé, fichiers envoyés, texte HTML.
    Les pourcentages représentent des étapes d'interface, pas les tests finis.
    """
    uploaded_files = file_obj if isinstance(file_obj, list) else [file_obj]
    uploaded_folders = folder_obj if isinstance(folder_obj, list) else [folder_obj]
    uploaded_files = [item for item in uploaded_files if item is not None]
    uploaded_folders = [item for item in uploaded_folders if item is not None]

    try:
        progress(0.05, desc="Préparation de l'audit...")

        if site_directory and site_directory.strip():
            progress(0.15, desc="Lecture du dossier local...")
            context = _build_context_from_site_directory(site_directory)
        elif uploaded_folders or uploaded_files:
            progress(0.15, desc="Préparation des ressources importées...")
            context = _build_context_from_uploaded_files(
                [*uploaded_folders, *uploaded_files]
            )
        elif html_text and html_text.strip():
            progress(0.15, desc="Lecture du HTML saisi...")
            context = _build_context_from_html_text(html_text)
        else:
            return "Veuillez fournir du HTML, des fichiers ou un dossier.", []

        progress(0.30, desc="Exécution des tests RGAA (durée variable)...")
        audit_result = await audit_service.audit(context)

        report = audit_service.last_enrichment_report
        if report is None:
            logger.info("[Playwright] Aucun rapport d'enrichissement.")
        elif report.error is not None:
            logger.warning("[Playwright] Enrichissement incomplet : %s", report.error)
        else:
            logger.info(
                "[Playwright] %s observations, %s candidates, %s à vérifier.",
                report.total,
                report.usable_count,
                report.review_count,
            )

        progress(0.90, desc="Préparation des résultats...")
        output = _format_json(audit_result), _result_table(audit_result)
        progress(1.0, desc="Audit terminé.")
        return output
    except Exception as error:
        logger.exception("Erreur pendant l'audit HTML.")
        return f"Erreur lors de l'exécution de l'audit : {error}", []


async def test_vlm(image_file: Any, progress: gr.Progress = gr.Progress()):
    """Exécute RGAA 1.1.1 sur une image isolée avec le moteur commun."""
    if image_file is None:
        return "Veuillez charger une image.", []

    try:
        progress(0.05, desc="Vérification de l'image...")
        image_path = _uploaded_file_path(image_file)
        if not image_path.is_file():
            return f"Le fichier image est introuvable : {image_path}", []

        progress(0.25, desc="Construction du contexte de l'image...")
        with TemporaryDirectory(prefix="accessicode_vlm_") as temporary_directory:
            html_path = Path(temporary_directory) / "index.html"
            image_name = html.escape(image_path.name, quote=True)
            html_source = (
                '<!DOCTYPE html><html lang="fr"><head>'
                '<meta charset="UTF-8"><title>Audit d’image AccessiCode</title>'
                f'</head><body><img src="{image_name}"></body></html>'
            )
            html_path.write_text(html_source, encoding="utf-8")
            context = context_builder.build([html_path, image_path])

        progress(0.40, desc="Analyse VLM en cours (durée variable)...")
        audit_result = await image_audit_service.audit(context)
        progress(0.90, desc="Préparation des résultats VLM...")
        output = _format_json(audit_result), _result_table(audit_result)
        progress(1.0, desc="Analyse VLM terminée.")
        return output
    except Exception as error:
        logger.exception("Erreur pendant l'audit VLM.")
        return f"Erreur lors de l'exécution du test VLM : {error}", []


def build_ui():
    """Construit l'ancienne interface d'audit, conservée temporairement."""
    with gr.Blocks(title="AccessiCode - Audit d'accessibilité Web") as demo:
        gr.Markdown("# ♿ AccessiCode — Audit d'accessibilité Web")
        gr.Markdown(
            "Analyse de pages HTML et de leurs ressources, "
            "selon les contrôles RGAA implémentés."
        )

        with gr.Tabs():
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
                            label="Importer des fichiers HTML, CSS et images",
                            file_count="multiple",
                            file_types=[
                                ".html", ".htm", ".css", ".png", ".jpg",
                                ".jpeg", ".webp", ".gif", ".svg",
                            ],
                            type="filepath",
                        )
                        folder_input = gr.File(
                            label="Ou importer un dossier de site complet",
                            file_count="directory",
                            type="filepath",
                        )
                        site_directory = gr.Textbox(
                            label="Ou saisir un chemin local de dossier",
                            placeholder="C:\\chemin\\vers\\mon-site",
                            info=(
                                "Mode bureau : le dossier doit exister sur "
                                "l'ordinateur qui exécute AccessiCode."
                            ),
                        )
                        gr.Markdown(
                            "Priorité des sources : dossier local, dossier importé, "
                            "fichiers importés, puis HTML collé."
                        )
                        btn_audit = gr.Button(
                            "🔍 Lancer l'audit RGAA", variant="primary"
                        )
                    with gr.Column(scale=1):
                        dataframe_output = gr.Dataframe(
                            headers=[
                                "Test RGAA", "Statut", "Éléments testés",
                                "Résumé", "Anomalies",
                            ],
                            label="Résultats des contrôles",
                        )
                        json_output = gr.Code(
                            language="json", label="Rapport JSON détaillé"
                        )

            with gr.Tab("VLM - Audit d'image"):
                with gr.Row():
                    with gr.Column(scale=1):
                        vlm_image_input = gr.File(
                            label="Image à analyser",
                            file_types=["image"],
                            type="filepath",
                        )
                        btn_vlm = gr.Button(
                            "🔍 Lancer l'audit VLM", variant="primary"
                        )
                    with gr.Column(scale=1):
                        vlm_dataframe_output = gr.Dataframe(
                            headers=[
                                "Test RGAA", "Statut", "Éléments testés",
                                "Résumé", "Anomalies",
                            ],
                            label="Résultats de l'audit VLM",
                        )
                        vlm_output = gr.Textbox(label="Rapport VLM", lines=12)

        btn_audit.click(
            fn=run_audit,
            inputs=[html_input, file_input, site_directory, folder_input],
            outputs=[json_output, dataframe_output],
        )
        btn_vlm.click(
            fn=test_vlm,
            inputs=[vlm_image_input],
            outputs=[vlm_output, vlm_dataframe_output],
        )
    return demo


def launch_desktop():
    """Démarre l'ancienne interface Gradio dans une fenêtre pywebview."""
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

import sys
from pathlib import Path

# Inclusion de la racine du projet au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import json
import time
import threading
import webview
import gradio as gr
from src.accessi_code.service.core import AuditService

# Initialisation du service métier d'audit
audit_service = AuditService()

def run_audit(html_text: str, file_obj):
    """
    Fonction d'audit déclenchée par l'UI.
    """
    if file_obj is not None:
        try:
            with open(file_obj.name, 'r', encoding='utf-8') as f:
                html_text = f.read()
        except Exception as e:
            return f"Erreur de lecture du fichier : {str(e)}", []

    if not html_text or not html_text.strip():
        return "Veuillez coller du HTML ou charger un fichier .html.", []

    try:
        result = asyncio.run(audit_service.audit_html_content(html_text))
    except Exception as e:
        return f"Erreur lors de l'exécution de l'audit LLM : {str(e)}", []

    table_data = []
    if isinstance(result, dict) and "evaluations" in result:
        for ev in result["evaluations"]:
            table_data.append([
                ev.get("image_id", "-"),
                ev.get("src", "-"),
                ev.get("rgpa_wcag_status", "-"),
                ev.get("is_decorative", False),
                ev.get("suggested_code", "-")
            ])

    json_formatted = json.dumps(result, indent=2, ensure_ascii=False)
    return json_formatted, table_data


def build_ui():
    """
    Construction de l'interface Gradio Blocks.
    """
    with gr.Blocks(title="AccessiCode - Audit Accessibilité A11y") as demo:
        gr.Markdown("# ♿ AccessiCode - Audit d'accessibilité Web (LLM - RGAA / WCAG)")
        gr.Markdown("Application de bureau pour l'audit d'accessibilité des images HTML.")

        with gr.Row():
            with gr.Column(scale=1):
                html_input = gr.Textbox(
                    lines=12,
                    placeholder="Collez votre code HTML ici...",
                    label="Code HTML à analyser"
                )
                file_input = gr.File(
                    label="Ou chargez un fichier HTML (ex: tests/index.html)",
                    file_types=[".html"]
                )
                btn_audit = gr.Button("🔍 Lancer l'audit LLM", variant="primary")

            with gr.Column(scale=1):
                dataframe_output = gr.Dataframe(
                    headers=["ID", "Source", "Statut RGAA", "Décorative", "Suggestion Code"],
                    label="Synthèse des évaluations"
                )
                json_output = gr.Code(
                    language="json",
                    label="Rapport JSON Détaillé (Retour LLM)"
                )

        btn_audit.click(
            fn=run_audit,
            inputs=[html_input, file_input],
            outputs=[json_output, dataframe_output]
        )
    return demo


def launch_desktop():
    """
    Lancement du serveur en arrière-plan et création de la fenêtre native.
    """
    demo = build_ui()

    # 1. Démarrage de Gradio dans un thread secondaire
    thread = threading.Thread(
        target=lambda: demo.launch(
            server_name="127.0.0.1",
            server_port=7860,
            prevent_thread_lock=True,
            show_error=False
        ),
        daemon=True
    )
    thread.start()

    # 2. Attente de l'initialisation du serveur HTTP local
    time.sleep(1.2)

    # 3. Création et ouverture de la fenêtre Desktop native
    window = webview.create_window(
        title="AccessiCode - Desktop App",
        url="http://127.0.0.1:7860",
        width=1280,
        height=850,
        resizable=True
    )
    
    # Démarrage de la boucle GUI native
    webview.start()

if __name__ == "__main__":
    launch_desktop()
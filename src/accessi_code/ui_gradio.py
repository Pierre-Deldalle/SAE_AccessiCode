import sys
from pathlib import Path

# Les deux chemins sont nécessaires : l'UI importe via src.accessi_code,
# tandis que les critères utilisent le package interne accessi_code.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for project_path in (ROOT_DIR, SRC_DIR):
    if str(project_path) not in sys.path:
        sys.path.insert(0, str(project_path))

import asyncio
import json
import time
import threading
from dataclasses import asdict
import webview
import gradio as gr
from src.accessi_code.service.core import AuditService
from src.accessi_code.config import settings
from src.accessi_code.ollama_client.vlm import OllamaVLM
# L'analyseur 1.7.1 combine les observations visuelles de Qwen et
# la comparaison des descriptions réalisée par Gemma.
from src.accessi_code.ai.ollama_client.image_analyzer import OllamaImageAnalyzer
from src.accessi_code.tests.theme_01_images.critere_1_1_1 import Criterion111
from src.accessi_code.tests.theme_01_images.critere_1_1_2 import Criterion112
from src.accessi_code.tests.theme_01_images.critere_1_1_3 import Criterion113
from src.accessi_code.tests.theme_01_images.criterion_1_7 import Criterion17
from src.accessi_code.tests.theme_05_tableaux.criterion_5_1_1 import Criterion511
from src.accessi_code.tests.theme_08_elements_obligatoires.criterion_8_1_1 import Criterion811
from src.accessi_code.tests.theme_11_formulaires.criterion_11_1_1 import Criterion111 as Criterion111Form

# Initialisation du service métier d'audit
audit_service = AuditService()
vlm_client = OllamaVLM(host=settings.OLLAMA_HOST, model=settings.VLM_MODEL)
# Le même client LLM est partagé avec l'audit général pour éviter de recréer
# une connexion et une configuration de modèle à chaque image.
image_analyzer = OllamaImageAnalyzer(vlm_client, audit_service.llm)
DOM_CRITERIA = (
    Criterion111(),
    Criterion112(),
    Criterion113(),
    Criterion17(),
    Criterion511(),
    Criterion811(),
    Criterion111Form(),
)


def run_dom_criteria(
    html_text: str,
    base_dir: str | None = None,
    asset_paths: list[str] | None = None,
) -> list[dict]:
    """Exécute les critères DOM commencés sur le HTML fourni."""
    asset_by_name = {
        Path(path).name: path
        for path in (asset_paths or [])
        if path
    }
    results = []
    for criterion in DOM_CRITERIA:
        if isinstance(criterion, Criterion17):
            def analyze_image(image, description):
                # Le HTML fournit le src ; on résout ensuite ce src vers le
                # fichier local avant de transmettre l'image au modèle de vision.
                image_path = image.image_path
                if not image_path or not Path(image_path).is_file():
                    image_path = asset_by_name.get(Path(image.src).name)
                if not image_path or not Path(image_path).is_file():
                    project_asset = ROOT_DIR / "test" / Path(image.src).name
                    if project_asset.is_file():
                        image_path = str(project_asset)
                if not image_path or not Path(image_path).is_file():
                    raise FileNotFoundError(
                        f"Image référencée introuvable : {image.src}. "
                        "Téléversez-la dans les ressources image."
                    )
                # Le critère reste synchrone, tandis que les clients Ollama
                # sont asynchrones : ce pont exécute une analyse complète.
                return asyncio.run(image_analyzer.analyze(
                    image.__class__(
                        src=image_path,
                        alt=image.alt,
                        element_html=image.element_html,
                        descriptions=image.descriptions,
                        context_text=image.context_text,
                        index=image.index,
                        image_path=image_path,
                        image_data=image.image_data,
                    ),
                    description,
                ))

            result = criterion.run(html_text, analyzer=analyze_image, base_dir=base_dir)
        else:
            result = criterion.run(html_text)
        serialized = asdict(result)
        serialized["status"] = result.status.value
        results.append(serialized)
    return results

def run_audit(html_text: str, file_obj):
    """
    Fonction d'audit déclenchée par l'UI.
    """
    uploaded_files = file_obj if isinstance(file_obj, list) else [file_obj]
    uploaded_files = [file for file in uploaded_files if file is not None]
    html_file = next(
        (file for file in uploaded_files if str(getattr(file, "name", file)).lower().endswith(".html")),
        None,
    )
    if html_file is not None:
        try:
            html_path = getattr(html_file, "name", html_file)
            with open(html_path, 'r', encoding='utf-8') as f:
                html_text = f.read()
        except Exception as e:
            return f"Erreur de lecture du fichier : {str(e)}", []

    if not html_text or not html_text.strip():
        return "Veuillez coller du HTML ou charger un fichier .html.", []

    # Les chemins relatifs des images sont interprétés depuis le dossier HTML.
    base_dir = str(Path(html_path).resolve().parent) if html_file is not None else None
    dom_results = run_dom_criteria(html_text, base_dir=base_dir)

    try:
        llm_result = asyncio.run(audit_service.audit_html_content(html_text))
    except Exception as e:
        llm_result = {
            "error": f"Erreur lors de l'exécution de l'audit LLM : {str(e)}"
        }

    result = {
        "dom_tests": dom_results,
        "llm_audit": llm_result,
    }
    table_data = [
        [
            dom_result["test_id"],
            dom_result["status"],
            dom_result["tested_elements"],
            dom_result["summary"],
            len(dom_result["findings"]),
        ]
        for dom_result in dom_results
    ]

    json_formatted = json.dumps(result, indent=2, ensure_ascii=False)
    return json_formatted, table_data


def test_vlm(image_file, prompt: str):
    """Envoie une image au VLM pour tester directement le modèle configuré."""
    if image_file is None:
        return "Veuillez charger une image."

    if not prompt or not prompt.strip():
        prompt = "Décris cette image en une phrase et indique son texte alternatif accessible."

    try:
        response = asyncio.run(vlm_client.generate(prompt=prompt, image=image_file))
        return response
    except Exception as e:
        return f"Erreur lors de l'exécution du test VLM : {str(e)}"


def build_ui():
    """
    Construction de l'interface Gradio Blocks.
    """
    with gr.Blocks(title="AccessiCode - Audit Accessibilité A11y") as demo:
        gr.Markdown("# ♿ AccessiCode - Audit d'accessibilité Web")
        gr.Markdown("Application de bureau pour l'audit d'accessibilité des images HTML.")

        with gr.Tabs():
            with gr.Tab("LLM - Audit HTML"):
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
                            headers=["Critère", "Statut", "Éléments testés", "Résumé", "Anomalies"],
                            label="Résultats des critères DOM"
                        )
                        json_output = gr.Code(
                            language="json",
                            label="Rapport JSON Détaillé (DOM + LLM)"
                        )

            with gr.Tab("VLM - Audit d'image"):
                with gr.Row():
                    with gr.Column(scale=1):
                        vlm_image_input = gr.File(
                            label="Image à analyser",
                            file_types=["image"],
                            type="filepath"
                        )
                        vlm_prompt_input = gr.Textbox(
                            label="Prompt VLM",
                            value="Décris cette image en une phrase et indique son texte alternatif accessible."
                        )
                        btn_vlm = gr.Button("🔍 Tester le VLM", variant="primary")

                    with gr.Column(scale=1):
                        vlm_output = gr.Textbox(
                            label="Réponse du VLM",
                            lines=12
                        )

        btn_audit.click(
            fn=run_audit,
            inputs=[html_input, file_input],
            outputs=[json_output, dataframe_output]
        )
        btn_vlm.click(
            fn=test_vlm,
            inputs=[vlm_image_input, vlm_prompt_input],
            outputs=[vlm_output]
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
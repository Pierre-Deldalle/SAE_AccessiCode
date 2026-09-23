"""
Lance l'interface Gradio dans une fenêtre desktop avec PyWebView.
"""

import threading
import time
import sys
from pathlib import Path

import webview

# Permet le lancement direct avec `python src/accessi_code/ui/desktop.py`.
# Dans ce cas, Python ajoute le dossier `ui` au chemin, mais pas `src`.
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from accessi_code.ui.app import create_app


HOST = "127.0.0.1"
PORT = 7860


def start_gradio():
    """Démarre le serveur Gradio en arrière-plan."""
    app = create_app()

    app.launch(
        server_name=HOST,
        server_port=PORT,
        prevent_thread_lock=True,
        show_error=True,
    )


def launch_desktop():
    """Ouvre l'application dans une fenêtre desktop native."""
    # Lance Gradio dans un thread séparé pour éviter de bloquer PyWebView.
    thread = threading.Thread(
        target=start_gradio,
        daemon=True,
    )
    thread.start()

    # Laisse le temps au serveur local de démarrer avant d'ouvrir la fenêtre.
    time.sleep(1.5)

    # Crée la fenêtre desktop qui affiche l'interface Gradio locale.
    webview.create_window(
        title="AccessiCode",
        url=f"http://{HOST}:{PORT}",
        maximized=True,
        resizable=True,
    )

    # Lance la boucle graphique de PyWebView.
    webview.start()


if __name__ == "__main__":
    launch_desktop()
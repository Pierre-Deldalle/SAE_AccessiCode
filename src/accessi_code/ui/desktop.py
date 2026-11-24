"""
Lance l'interface Gradio dans une fenêtre desktop avec PyWebView.
"""

import sys
import threading
import time
import urllib.request
from pathlib import Path

import webview

# Permet le lancement direct avec `python src/accessi_code/ui/desktop.py`.
# Dans ce cas, Python ajoute le dossier `ui` au chemin, mais pas `src`.
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from accessi_code.ui.app import create_app, launch_options  # noqa: E402 (après l'ajout de src au chemin)

HOST = "127.0.0.1"
PORT = 7860
# Délai maximal d'attente du serveur Gradio avant d'ouvrir la fenêtre.
STARTUP_TIMEOUT_SECONDS = 30


def wait_for_server(url: str, timeout: float = STARTUP_TIMEOUT_SECONDS) -> bool:
    """Attend que le serveur local réponde, pour ne pas ouvrir une fenêtre vide."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_gradio():
    """Démarre le serveur Gradio en arrière-plan."""
    app = create_app()

    app.launch(
        server_name=HOST,
        server_port=PORT,
        prevent_thread_lock=True,
        show_error=True,
        **launch_options(),
    )


def launch_desktop():
    """Ouvre l'application dans une fenêtre desktop native."""
    # Lance Gradio dans un thread séparé pour éviter de bloquer PyWebView.
    thread = threading.Thread(
        target=start_gradio,
        daemon=True,
    )
    thread.start()

    # Ouvre la fenêtre dès que le serveur local répond.
    url = f"http://{HOST}:{PORT}"
    if not wait_for_server(url):
        print(f"Le serveur AccessiCode ne répond pas sur {url} : la fenêtre s'ouvre quand même.")

    # Crée la fenêtre desktop qui affiche l'interface Gradio locale.
    webview.create_window(
        title="AccessiCode",
        url=url,
        maximized=True,
        resizable=True,
    )

    # Lance la boucle graphique de PyWebView.
    webview.start()


if __name__ == "__main__":
    launch_desktop()

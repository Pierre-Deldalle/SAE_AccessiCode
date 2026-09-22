import threading
import time

import webview

from accessi_code.ui.app import create_app


HOST = "127.0.0.1"
PORT = 7860


def start_gradio():
    app = create_app()

    app.launch(
        server_name=HOST,
        server_port=PORT,
        prevent_thread_lock=True,
        show_error=True,
    )


def launch_desktop():
    thread = threading.Thread(
        target=start_gradio,
        daemon=True,
    )
    thread.start()

    time.sleep(1.5)

    webview.create_window(
        title="AccessiCode",
        url=f"http://{HOST}:{PORT}",
        maximized=True,
        resizable=True,
    )

    webview.start()


if __name__ == "__main__":
    launch_desktop()
from pathlib import Path

import gradio as gr


def create_image(
    image_path: str | Path,
    *,
    height: int | None = None,
    width: int | None = None,
    elem_id: str | None = None,
) -> gr.Image:
    return gr.Image(
        value=str(image_path),
        height=height,
        width=width,
        show_label=False,
        interactive=False,
        container=False,
        elem_id=elem_id,
    )
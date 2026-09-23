import gradio as gr


def create_file_drop(
    *,
    file_count: str = "multiple",
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
):
    """
    Crée une zone de sélection / drag & drop de fichiers.
    """

    return gr.File(
        file_count=file_count,
        show_label=False,
        container=False,
        elem_id=elem_id,
        elem_classes=elem_classes,
    )
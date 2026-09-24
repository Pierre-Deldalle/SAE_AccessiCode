import gradio as gr


def create_textbox(
    *,
    placeholder: str = "",
    value: str = "",
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
):
    """
    Crée une zone de texte simple.
    """

    return gr.Textbox(
        value=value,
        placeholder=placeholder,
        show_label=False,
        container=False,
        elem_id=elem_id,
        elem_classes=elem_classes,
    )
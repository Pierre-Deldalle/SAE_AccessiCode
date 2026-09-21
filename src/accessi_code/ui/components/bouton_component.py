import gradio as gr


def create_button(
    text: str,
    *,
    variant: str = "secondary",
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
) -> gr.Button:
    return gr.Button(
        value=text,
        variant=variant,
        elem_id=elem_id,
        elem_classes=elem_classes,
    )
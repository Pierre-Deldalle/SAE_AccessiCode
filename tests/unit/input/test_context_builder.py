from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.capabilities import Capability


def create_text_file(
    directory: Path,
    name: str,
    content: str,
) -> Path:
    """
    Crée un fichier texte utilisé comme entrée d'un audit.
    """
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / name
    path.write_text(content, encoding="utf-8")

    return path


def create_binary_file(
    directory: Path,
    name: str,
    content: bytes = b"fake file content",
) -> Path:
    """
    Crée un faux fichier binaire utilisé comme entrée d'un audit.

    Son contenu réel n'a pas d'importance pour le ContextBuilder,
    qui ne décode pas encore les images.
    """
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / name
    path.write_bytes(content)

    return path


def create_builder(tmp_path: Path) -> AuditContextBuilder:
    """
    Crée un builder dont le workspace est isolé dans tmp_path.
    """
    return AuditContextBuilder(
        workspace_root=tmp_path / "workspace",
    )


def test_build_context_with_html(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        """
        <!DOCTYPE html>
        <html lang="fr">
            <head>
                <title>AccessiCode</title>
            </head>
            <body>
                <h1>Test</h1>
            </body>
        </html>
        """,
    )

    builder = create_builder(tmp_path)

    context = builder.build([html])

    assert context.html_source is not None
    assert context.dom is not None
    assert context.html_path is not None

    assert context.doctype is not None
    assert context.doctype.lower() == "<!doctype html>"

    assert context.has_capability(Capability.HTML_SOURCE)
    assert context.has_capability(Capability.DOM)
    assert context.has_capability(Capability.SOURCE_FILES)


def test_context_contains_all_input_files(tmp_path: Path):
    input_directory = tmp_path / "inputs"

    html = create_text_file(
        input_directory,
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    css = create_text_file(
        input_directory,
        "style.css",
        "body { color: black; }",
    )

    javascript = create_text_file(
        input_directory,
        "script.js",
        "console.log('AccessiCode');",
    )

    image = create_binary_file(
        input_directory,
        "logo.png",
    )

    builder = create_builder(tmp_path)

    context = builder.build(
        [
            html,
            css,
            javascript,
            image,
        ]
    )

    assert len(context.files) == 4

    original_names = {file.original_name for file in context.files}

    assert original_names == {
        "index.html",
        "style.css",
        "script.js",
        "logo.png",
    }


def test_image_files_are_detected(tmp_path: Path):
    input_directory = tmp_path / "inputs"

    html = create_text_file(
        input_directory,
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    logo = create_binary_file(
        input_directory,
        "logo.png",
    )

    banner = create_binary_file(
        input_directory,
        "banner.webp",
    )

    builder = create_builder(tmp_path)

    context = builder.build(
        [
            html,
            logo,
            banner,
        ]
    )

    assert len(context.image_files) == 2

    names = {image.name for image in context.image_files}

    assert names == {
        "logo.png",
        "banner.webp",
    }

    assert context.has_capability(Capability.IMAGES)


def test_no_images_means_no_image_capability(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    builder = create_builder(tmp_path)

    context = builder.build([html])

    assert context.image_files == []

    assert not context.has_capability(Capability.IMAGES)


def test_context_without_html_is_still_created(tmp_path: Path):
    image = create_binary_file(
        tmp_path / "inputs",
        "logo.png",
    )

    builder = create_builder(tmp_path)

    context = builder.build([image])

    assert context.html_path is None
    assert context.html_source is None
    assert context.dom is None
    assert context.doctype is None

    assert context.has_capability(Capability.SOURCE_FILES)

    assert context.has_capability(Capability.IMAGES)

    assert not context.has_capability(Capability.HTML_SOURCE)

    assert not context.has_capability(Capability.DOM)


def test_empty_input_creates_empty_context(tmp_path: Path):
    builder = create_builder(tmp_path)

    context = builder.build([])

    assert context.files == []
    assert context.image_files == []

    assert context.html_path is None
    assert context.html_source is None
    assert context.dom is None
    assert context.doctype is None

    assert context.get_capabilities() == set()


def test_non_html_files_are_preserved(tmp_path: Path):
    css = create_text_file(
        tmp_path / "inputs",
        "style.css",
        "body { color: red; }",
    )

    builder = create_builder(tmp_path)

    context = builder.build([css])

    assert len(context.files) == 1
    assert context.files[0].original_name == "style.css"

    assert context.html_source is None
    assert context.dom is None

    assert context.has_capability(Capability.SOURCE_FILES)


def test_multiple_html_files_use_first_one(tmp_path: Path):
    input_directory = tmp_path / "inputs"

    first_html = create_text_file(
        input_directory,
        "first.html",
        """
        <!DOCTYPE html>
        <html>
            <head>
                <title>First</title>
            </head>
        </html>
        """,
    )

    second_html = create_text_file(
        input_directory,
        "second.html",
        """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Second</title>
            </head>
        </html>
        """,
    )

    builder = create_builder(tmp_path)

    context = builder.build(
        [
            first_html,
            second_html,
        ]
    )

    title = context.dom.find("title")

    assert title is not None
    assert title.get_text() == "First"

    assert context.html_path is not None
    assert context.html_path.name == "first.html"


def test_has_multiple_required_capabilities(tmp_path: Path):
    input_directory = tmp_path / "inputs"

    html = create_text_file(
        input_directory,
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    image = create_binary_file(
        input_directory,
        "logo.png",
    )

    builder = create_builder(tmp_path)

    context = builder.build(
        [
            html,
            image,
        ]
    )

    required = {
        Capability.SOURCE_FILES,
        Capability.HTML_SOURCE,
        Capability.DOM,
        Capability.IMAGES,
    }

    assert context.has_capabilities(required)


def test_missing_required_capability_returns_false(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    builder = create_builder(tmp_path)

    context = builder.build([html])

    required = {
        Capability.DOM,
        Capability.SCREENSHOT,
    }

    assert not context.has_capabilities(required)

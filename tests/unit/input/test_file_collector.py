from pathlib import Path

import pytest

from accessi_code.input.file_collector import FileCollector


def create_text_file(
    directory: Path,
    name: str,
    content: str,
) -> Path:
    """
    Crée un fichier texte utilisé pour les tests.
    """
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / name
    path.write_text(content, encoding="utf-8")

    return path


def create_collector(tmp_path: Path) -> FileCollector:
    """
    Crée un FileCollector avec un workspace temporaire.
    """
    return FileCollector(
        workspace_root=tmp_path / "workspace",
    )


def test_workspace_is_created(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    collector = create_collector(tmp_path)

    _, workspace_path, _ = collector.collect([html])

    assert workspace_path.exists()
    assert workspace_path.is_dir()

    source_directory = workspace_path / "source"

    assert source_directory.exists()
    assert source_directory.is_dir()


def test_audit_id_is_generated(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    collector = create_collector(tmp_path)

    audit_id, _, _ = collector.collect([html])

    assert audit_id
    assert isinstance(audit_id, str)
    assert len(audit_id) > 0


def test_each_audit_has_a_different_id(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    collector = create_collector(tmp_path)

    audit_id_1, workspace_1, _ = collector.collect([html])
    audit_id_2, workspace_2, _ = collector.collect([html])

    assert audit_id_1 != audit_id_2
    assert workspace_1 != workspace_2


def test_source_file_is_copied_into_workspace(tmp_path: Path):
    source = """
    <!DOCTYPE html>
    <html>
        <body>
            <p>Hello AccessiCode</p>
        </body>
    </html>
    """

    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        source,
    )

    collector = create_collector(tmp_path)

    _, workspace_path, _ = collector.collect([html])

    copied_file = workspace_path / "source" / "index.html"

    assert copied_file.exists()
    assert copied_file != html

    assert copied_file.read_text(encoding="utf-8") == source


def test_original_file_is_not_removed_or_modified(tmp_path: Path):
    source = "<!DOCTYPE html><html><body>Original</body></html>"

    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        source,
    )

    collector = create_collector(tmp_path)

    collector.collect([html])

    assert html.exists()
    assert html.read_text(encoding="utf-8") == source


def test_audit_file_metadata_is_created(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        "<!DOCTYPE html><html></html>",
    )

    collector = create_collector(tmp_path)

    _, _, files = collector.collect([html])

    assert len(files) == 1

    audit_file = files[0]

    assert audit_file.original_name == "index.html"
    assert audit_file.extension == ".html"
    assert audit_file.mime_type == "text/html"
    assert audit_file.path.exists()


def test_missing_input_file_raises_error(tmp_path: Path):
    missing_file = tmp_path / "inputs" / "does_not_exist.html"

    collector = create_collector(tmp_path)

    with pytest.raises(FileNotFoundError):
        collector.collect([missing_file])


def test_files_with_same_name_are_not_overwritten(tmp_path: Path):
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"

    first_file = create_text_file(
        first_directory,
        "style.css",
        "body { color: red; }",
    )

    second_file = create_text_file(
        second_directory,
        "style.css",
        "body { color: blue; }",
    )

    collector = create_collector(tmp_path)

    _, _, files = collector.collect(
        [
            first_file,
            second_file,
        ]
    )

    assert len(files) == 2

    stored_names = {file.path.name for file in files}

    assert stored_names == {
        "style.css",
        "style_1.css",
    }

    contents = {file.path.read_text(encoding="utf-8") for file in files}

    assert contents == {
        "body { color: red; }",
        "body { color: blue; }",
    }

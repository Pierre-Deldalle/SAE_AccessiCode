from pathlib import Path

from accessi_code.input.extractors.html import (
    extract_doctype,
    extract_html,
)


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


def test_dom_contains_expected_elements(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        """
        <!DOCTYPE html>
        <html lang="fr">
            <body>
                <img src="logo.png" alt="Logo AccessiCode">

                <form>
                    <label for="email">Email</label>
                    <input id="email" type="email">
                </form>
            </body>
        </html>
        """,
    )

    extraction = extract_html(html)

    images = extraction.dom.find_all("img")
    forms = extraction.dom.find_all("form")
    inputs = extraction.dom.find_all("input")

    assert len(images) == 1
    assert images[0].get("alt") == "Logo AccessiCode"

    assert len(forms) == 1

    assert len(inputs) == 1
    assert inputs[0].get("id") == "email"
    assert inputs[0].get("type") == "email"


def test_html_source_is_preserved(tmp_path: Path):
    source = """
    <!DOCTYPE html>
    <html lang="fr">
        <body>
            <h1>AccessiCode</h1>
        </body>
    </html>
    """

    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        source,
    )

    extraction = extract_html(html)

    assert extraction.source == source


def test_html_without_doctype(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        """
        <html lang="fr">
            <body>
                <h1>Sans DOCTYPE</h1>
            </body>
        </html>
        """,
    )

    extraction = extract_html(html)

    assert extraction.source is not None
    assert extraction.dom is not None
    assert extraction.doctype is None


def test_doctype_is_extracted(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        """
        <!DOCTYPE html>
        <html></html>
        """,
    )

    extraction = extract_html(html)

    assert extraction.doctype == "<!DOCTYPE html>"


def test_doctype_is_case_insensitive(tmp_path: Path):
    html = create_text_file(
        tmp_path / "inputs",
        "index.html",
        """
        <!doctype HTML>
        <html></html>
        """,
    )

    extraction = extract_html(html)

    assert extraction.doctype is not None
    assert extraction.doctype.lower() == "<!doctype html>"


def test_extract_doctype_returns_none_when_missing():
    source = """
    <html>
        <body></body>
    </html>
    """

    assert extract_doctype(source) is None


def test_extract_doctype_returns_complete_declaration():
    source = """
    <!DOCTYPE html>
    <html></html>
    """

    assert extract_doctype(source) == "<!DOCTYPE html>"
from pathlib import Path

import pytest

from accessi_code.input.file_collector import FileCollector


def test_individual_files_are_flattened(tmp_path: Path):
    source = tmp_path / "inputs"
    source.mkdir()

    html = source / "index.html"
    css = source / "style.css"

    html.write_text("<html></html>", encoding="utf-8")
    css.write_text("body { color: red; }", encoding="utf-8")

    collector = FileCollector(tmp_path / "workspace")

    _, workspace, files = collector.collect([html, css])

    assert (workspace / "source" / "index.html").is_file()
    assert (workspace / "source" / "style.css").is_file()
    assert len(files) == 2


def test_site_import_preserves_directory_structure(tmp_path: Path):
    site = tmp_path / "site"
    css_directory = site / "css"
    css_directory.mkdir(parents=True)

    html = site / "index.html"
    css = css_directory / "style.css"

    html.write_text(
        '<link rel="stylesheet" href="css/style.css">',
        encoding="utf-8",
    )
    css.write_text(
        "body { color: red; }",
        encoding="utf-8",
    )

    collector = FileCollector(tmp_path / "workspace")

    _, workspace, files = collector.collect(
        [html, css],
        site_root=site,
    )

    copied_html = workspace / "source" / "index.html"
    copied_css = workspace / "source" / "css" / "style.css"

    assert copied_html.is_file()
    assert copied_css.is_file()
    assert copied_css.read_text(encoding="utf-8") == ("body { color: red; }")

    assert {file.path for file in files} == {
        copied_html,
        copied_css,
    }


def test_site_import_rejects_files_outside_root(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()

    outside = tmp_path / "outside.css"
    outside.write_text("body {}", encoding="utf-8")

    collector = FileCollector(tmp_path / "workspace")

    with pytest.raises(ValueError, match="extérieur"):
        collector.collect(
            [outside],
            site_root=site,
        )


def test_site_import_rejects_duplicate_files(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()

    css = site / "style.css"
    css.write_text("body {}", encoding="utf-8")

    collector = FileCollector(tmp_path / "workspace")

    with pytest.raises(ValueError, match="plusieurs fois"):
        collector.collect(
            [css, css],
            site_root=site,
        )

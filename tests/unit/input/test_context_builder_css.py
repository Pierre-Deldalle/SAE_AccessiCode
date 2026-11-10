from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.capabilities import Capability


def test_builder_preserves_site_structure_and_extracts_css(
    tmp_path: Path,
):
    site = tmp_path / "site"
    css_directory = site / "css"
    css_directory.mkdir(parents=True)

    html = site / "index.html"
    css = css_directory / "style.css"

    html.write_text(
        """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <link rel="stylesheet" href="css/style.css">
            <title>Site de test</title>
        </head>
        <body>
            <p class="warning">Attention</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    css.write_text(
        ".warning { color: red; }",
        encoding="utf-8",
    )

    builder = AuditContextBuilder(
        workspace_root=tmp_path / "workspace",
    )

    context = builder.build(
        [html, css],
        site_root=site,
    )

    copied_html = context.workspace_path / "source" / "index.html"
    copied_css = context.workspace_path / "source" / "css" / "style.css"

    assert context.html_path == copied_html
    assert context.dom is not None

    assert context.css_files == [copied_css]
    assert context.css_sources[copied_css] == (".warning { color: red; }")

    assert context.has_capability(Capability.DOM)
    assert context.has_capability(Capability.HTML_SOURCE)
    assert context.has_capability(Capability.CSS_SOURCE)

    # Extraire du CSS ne signifie pas disposer de styles calculés.
    assert not context.has_capability(Capability.COMPUTED_STYLES)

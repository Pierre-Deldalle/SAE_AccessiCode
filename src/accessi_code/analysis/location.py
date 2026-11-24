"""Localisation d'un élément HTML dans sa source."""

import re
from pathlib import Path

from bs4 import Tag

from accessi_code.models.audit_context import AuditContext

_SNIPPET_LIMIT = 200
_OPENING_TAG = re.compile(r"""<(?:[^>"']|"[^"]*"|'[^']*')*>""")


def html_opening_tag(html: str) -> str:
    """Extrait la balise ouvrante d'un élément HTML sérialisé."""
    opening = _OPENING_TAG.match(html)
    return opening.group() if opening is not None else html


def locate(tag: Tag | None) -> tuple[int | None, str | None]:
    """Renvoie la ligne de la balise et un extrait de sa représentation HTML."""
    if tag is None:
        return None, None

    snippet = str(tag)
    if len(snippet) > _SNIPPET_LIMIT:
        snippet = html_opening_tag(snippet)
        if len(snippet) > _SNIPPET_LIMIT:
            snippet = snippet[: _SNIPPET_LIMIT - 1] + "…"
    return tag.sourceline, snippet


def source_file_name(context: AuditContext, path: str | Path) -> str:
    """Retrouve le nom importé ou le chemin relatif au site pour une copie de travail."""
    resolved = Path(path).resolve()
    original_name = next(
        (file.original_name for file in context.files if file.path.resolve() == resolved),
        resolved.name,
    )
    source_root = (context.workspace_path / "source").resolve()
    if resolved.is_relative_to(source_root):
        return resolved.relative_to(source_root).with_name(original_name).as_posix()
    return original_name

"""
Emplacement d'un élément dans le fichier source, pour situer une observation.

Ne décide d'aucun statut RGAA.
"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Tag
from bs4.dammit import EntitySubstitution
from bs4.formatter import HTMLFormatter

from accessi_code.models.audit_context import AuditContext

SNIPPET_LIMIT = 200


class _SourceOrderFormatter(HTMLFormatter):
    """Formateur HTML qui garde les attributs dans l'ordre du code source (BeautifulSoup les trie)."""

    def attributes(self, tag: Tag):  # type: ignore[override]
        return list(tag.attrs.items()) if tag.attrs else []


_FORMATTER = _SourceOrderFormatter(entity_substitution=EntitySubstitution.substitute_xml)


def _html(tag: Tag) -> str:
    return tag.decode(formatter=_FORMATTER)


def element_snippet(tag: Tag, limit: int = SNIPPET_LIMIT) -> str:
    """
    Extrait HTML de l'élément, espaces normalisés : l'élément entier s'il est court,
    sinon sa seule balise ouvrante ; tronqué à ``limit`` caractères.
    """
    html = " ".join(_html(tag).split())
    if len(html) > limit:
        # BeautifulSoup échappe « > » dans les valeurs d'attributs : le premier « > » ferme la balise.
        html = html[: html.find(">") + 1] or html
    if len(html) > limit:
        html = html[: limit - 1] + "…"
    return html


def locate(tag: Tag | None) -> tuple[int | None, str | None]:
    """(numéro de ligne dans le fichier HTML, extrait HTML) ; (None, None) sans élément."""
    if not isinstance(tag, Tag):
        return None, None
    line = tag.sourceline if isinstance(tag.sourceline, int) else None
    return line, element_snippet(tag)


def opening_tag(tag: Tag, **changes: str | None) -> str:
    """
    Balise ouvrante de l'élément avec ses vrais attributs, modifiés par ``changes``
    (une valeur None retire l'attribut), pour montrer une correction « avant / après ».
    """
    attrs = {name: changes.get(name, value) for name, value in tag.attrs.items()}
    attrs.update({name: value for name, value in changes.items() if name not in attrs})
    attrs = {name: value for name, value in attrs.items() if value is not None}
    rebuilt = BeautifulSoup("", "html.parser").new_tag(tag.name, attrs=attrs)
    html = _html(rebuilt)
    return html[: html.find(">") + 1].replace("/>", ">")


def source_file_name(context: AuditContext, path: Path | str | None) -> str | None:
    """
    Nom d'un fichier de l'audit tel que l'utilisateur l'a fourni : chemin dans le
    site importé (« pages/contact.html »), ou nom d'origine d'un fichier déposé seul
    (sa copie de travail peut avoir été renommée pour éviter un doublon).
    """
    if path is None:
        return None
    path = Path(path)
    original = next((item.original_name for item in context.files if Path(item.path) == path), None)
    try:
        relative = path.relative_to(context.workspace_path / "source").as_posix()
    except ValueError:
        relative = None
    if relative and (original is None or Path(relative).name == original):
        return relative
    return original or path.name

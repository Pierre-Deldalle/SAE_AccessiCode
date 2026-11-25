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


# Balises vides écrites comme en HTML (<input …>), sans la barre oblique de XHTML.
_FORMATTER = _SourceOrderFormatter(entity_substitution=EntitySubstitution.substitute_xml, void_element_close_prefix="")


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


def locate_in_text(tag: Tag | None, offset: int) -> tuple[int | None, str | None]:
    """
    Emplacement d'une position dans le texte d'un élément de la page (``<script>``, ``<style>`` en ligne).

    ``offset`` est un indice dans ``tag.get_text()``. La ligne est celle du fichier HTML
    (ligne de la balise ouvrante + retours à la ligne avant ``offset``) ; l'extrait est la
    ligne de code correspondante. Position invalide → emplacement de l'élément lui-même.
    """
    if not isinstance(tag, Tag):
        return None, None
    text = tag.get_text()
    if not 0 <= offset <= len(text):
        return locate(tag)
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    code = " ".join(text[start : end if end != -1 else len(text)].split())
    if len(code) > SNIPPET_LIMIT:
        code = code[: SNIPPET_LIMIT - 1] + "…"
    line = tag.sourceline + text.count("\n", 0, offset) if isinstance(tag.sourceline, int) else None
    return line, code or element_snippet(tag)


def locate_in_source(text: str, offset: int) -> tuple[int | None, str | None]:
    """
    Emplacement d'une position dans le texte d'un fichier (script ``.js``, feuille ``.css``) :
    (numéro de ligne dans ce fichier, ligne de code correspondante). Position invalide → (None, None).
    """
    if not 0 <= offset <= len(text):
        return None, None
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    code = " ".join(text[start : end if end != -1 else len(text)].split())
    if len(code) > SNIPPET_LIMIT:
        code = code[: SNIPPET_LIMIT - 1] + "…"
    return text.count("\n", 0, offset) + 1, code or None


def location_fields(tag: Tag | None, offset: int | None = None) -> dict[str, int | str | None]:
    """
    Champs ``line`` et ``snippet`` pour un Finding construit à la main :
    ``Finding(..., **location_fields(tag))``. Avec ``offset``, voir ``locate_in_text``.

    ``file`` n'est pas renseigné : le runner y place la page auditée.
    """
    line, snippet = locate(tag) if offset is None else locate_in_text(tag, offset)
    return {"line": line, "snippet": snippet}


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

"""
Localisation d'un élément HTML dans le fichier source.

Ces fonctions servent uniquement à indiquer où se trouve un élément (numéro de
ligne et extrait HTML) ; elles ne décident d'aucun statut RGAA.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import escape

from bs4 import Tag
from bs4.dammit import EntitySubstitution
from bs4.formatter import HTMLFormatter

SNIPPET_MAX_LENGTH = 200

_WHITESPACE = re.compile(r"\s+")


# Attributs booléens HTML : présents ou absents, sans valeur (``<video controls>``).
BOOLEAN_ATTRIBUTES = frozenset(
    {
        "allowfullscreen",
        "async",
        "autofocus",
        "autoplay",
        "checked",
        "controls",
        "default",
        "defer",
        "disabled",
        "formnovalidate",
        "hidden",
        "inert",
        "ismap",
        "loop",
        "multiple",
        "muted",
        "nomodule",
        "novalidate",
        "open",
        "playsinline",
        "readonly",
        "required",
        "reversed",
        "selected",
    }
)


def _is_bare(name: str, value: object) -> bool:
    return value is None or (value == "" and name in BOOLEAN_ATTRIBUTES)


class _SourceOrderFormatter(HTMLFormatter):
    """
    Rendu proche du fichier source : attributs dans leur ordre d'origine.

    Les attributs booléens connus sont écrits sans valeur (``controls``) ; les autres
    attributs vides gardent ``attr=""`` : le parseur ne distingue pas ``alt`` de ``alt=""``,
    et la seconde forme est la plus parlante pour un audit.
    """

    def attributes(self, tag: Tag):  # type: ignore[override]
        return [(key, None if _is_bare(key, value) else value) for key, value in tag.attrs.items()]


_FORMATTER = _SourceOrderFormatter(
    entity_substitution=EntitySubstitution.substitute_xml,
    void_element_close_prefix=None,
)


def locate(tag: Tag | None) -> tuple[int | None, str | None]:
    """
    Retourne la ligne de l'élément dans le fichier HTML et un extrait de son code.

    La ligne provient de ``Tag.sourceline`` (renseignée par le parseur
    ``html.parser`` ou ``lxml``) ; elle vaut None si le parseur ne la fournit pas.
    L'extrait contient l'élément complet s'il est court, sinon sa seule balise
    ouvrante, et ne dépasse jamais ``SNIPPET_MAX_LENGTH`` caractères.
    """
    if not isinstance(tag, Tag):
        return None, None
    return tag.sourceline, html_snippet(tag)


def locate_in_text(tag: Tag | None, offset: int) -> tuple[int | None, str | None]:
    """
    Localise une position dans le contenu texte d'un élément inline (``<script>``, ``<style>``).

    ``offset`` est un indice dans ``tag.get_text()``. La ligne retournée est celle du
    fichier HTML (ligne de la balise ouvrante + retours à la ligne précédant l'offset) ;
    l'extrait est la ligne de code correspondante. Ligne inconnue → None.
    """
    if not isinstance(tag, Tag):
        return None, None
    text = tag.get_text()
    if not 0 <= offset <= len(text):
        return locate(tag)
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    code_line = _truncate(_compact(text[start : end if end != -1 else len(text)]), SNIPPET_MAX_LENGTH)
    line = None if tag.sourceline is None else tag.sourceline + text.count("\n", 0, offset)
    return line, code_line or html_snippet(tag)


def location_fields(tag: Tag | None, offset: int | None = None) -> dict[str, int | str | None]:
    """
    Champs ``line`` et ``snippet`` d'un Finding, à déplier : ``Finding(..., **location_fields(tag))``.

    Avec ``offset``, la position est cherchée dans le texte de l'élément (voir ``locate_in_text``).
    """
    line, snippet = locate(tag) if offset is None else locate_in_text(tag, offset)
    return {"line": line, "snippet": snippet}


def html_snippet(tag: Tag, max_length: int = SNIPPET_MAX_LENGTH) -> str:
    """Extrait HTML lisible de l'élément, sur une seule ligne, tronqué à ``max_length`` caractères."""
    full = _compact(tag.decode(formatter=_FORMATTER))
    if len(full) <= max_length:
        return full
    return _truncate(opening_tag(tag), max_length)


def opening_tag(tag: Tag) -> str:
    """Balise ouvrante de l'élément, attributs compris (ex. ``<video src="a.mp4" controls>``)."""
    return render_opening_tag(tag.name, tag.attrs.items())


def render_opening_tag(
    name: str,
    attributes: Iterable[tuple[str, object]],
    *,
    value_limit: int | None = None,
) -> str:
    """
    Écrit une balise ouvrante à partir de son nom et de ses attributs, dans l'ordre fourni.

    Une valeur None, ou vide pour un attribut booléen, donne un attribut sans valeur.
    ``value_limit`` raccourcit les valeurs trop longues (utile pour un exemple court).
    """
    parts = [name]
    for key, value in attributes:
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        if _is_bare(key, value):
            parts.append(key)
            continue
        text = str(value)
        if value_limit is not None:
            text = _truncate(text, value_limit)
        parts.append(f'{key}="{escape(text, quote=True)}"')
    return _compact("<" + " ".join(parts) + ">")


def _compact(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"

"""Localisation d'un élément HTML dans sa source."""

import re

from bs4 import Tag

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

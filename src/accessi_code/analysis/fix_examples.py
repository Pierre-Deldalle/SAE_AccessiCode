"""
Exemples de correction « avant → après » à joindre aux recommandations.

Ces fonctions ne servent que pour les corrections mécaniques (ajouter un attribut,
changer une valeur) et reprennent les vraies valeurs de l'élément trouvé. Elles ne
décident d'aucun statut et ne proposent jamais de texte qui dépend du sens
(alternative, transcription…) : ce rôle revient à l'IA.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping

from bs4 import Tag

from accessi_code.analysis.location import opening_tag

# Éléments qui reçoivent le focus clavier sans tabindex.
_NATIVELY_FOCUSABLE = frozenset({"a", "area", "button", "input", "select", "summary", "textarea"})


def attribute_fix_example(
    tag: Tag,
    *,
    set_attributes: Mapping[str, str] | None = None,
    remove_attributes: Iterable[str] = (),
) -> str | None:
    """
    Exemple « <balise avant> → <balise après> » construit avec ``opening_tag`` (vrais attributs).

    ``set_attributes`` ajoute ou remplace des attributs (valeur "" pour un attribut booléen
    comme ``controls``) ; ``remove_attributes`` en retire. Retourne None si l'élément n'est
    pas une balise ou si la modification ne change rien.
    """
    if not isinstance(tag, Tag):
        return None

    changes: dict[str, str | None] = dict(set_attributes or {})
    changes.update({name: None for name in remove_attributes})

    before = opening_tag(tag)
    after = opening_tag(tag, **changes)
    if before == after:
        return None
    return f"{before} → {after}"


def keyboard_focus_example(control: Tag, *, fixed_by: Callable[[Tag], bool] | None = None) -> str | None:
    """
    Exemple pour rendre un contrôle atteignable au clavier en lui donnant ``tabindex="0"``.

    Seulement quand cette correction suffit : tabindex négatif ou invalide, ou élément non
    focalisable nativement sans tabindex. Aucun exemple pour un contrôle désactivé ou pour
    un lien sans ``href`` (la bonne destination dépend du site).

    ``fixed_by`` est la règle du test appelant : l'exemple n'est proposé que si le contrôle
    corrigé la respecte, pour ne jamais suggérer une correction insuffisante.
    """
    if not isinstance(control, Tag):
        return None
    if "disabled" in control.attrs or str(control.get("aria-disabled", "")).lower() == "true":
        return None
    if control.name == "a" and not control.get("href"):
        return None

    tabindex = control.get("tabindex")
    if tabindex is not None:
        try:
            if int(str(tabindex)) >= 0:
                return None
        except ValueError:
            pass
    elif control.name in _NATIVELY_FOCUSABLE:
        return None

    if fixed_by is not None:
        fixed = copy.copy(control)
        fixed["tabindex"] = "0"
        if not fixed_by(fixed):
            return None
    return attribute_fix_example(control, set_attributes={"tabindex": "0"})


def first_keyboard_fix_example(controls: Iterable[Tag], rule: Callable[[Tag], bool]) -> str | None:
    """Exemple ``tabindex="0"`` pour le premier contrôle qui ne respecte pas ``rule``, si cela suffit à le corriger."""
    failing = next((control for control in controls if not rule(control)), None)
    return keyboard_focus_example(failing, fixed_by=rule) if failing is not None else None


CONTENT_LIMIT = 60


def shorten(text: str, limit: int = CONTENT_LIMIT) -> str:
    """Texte aux espaces normalisés, coupé à ``limit`` caractères (« … » final)."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _content(tag: Tag, limit: int = CONTENT_LIMIT) -> str:
    """Contenu HTML de l'élément s'il est court, sinon « … »."""
    html = " ".join(tag.decode_contents().split())
    return html if len(html) <= limit else "…"


def _renamed(opening: str, old: str, new: str) -> str:
    return f"<{new}{opening[len(old) + 1 :]}"


def rename_example(
    tag: Tag,
    name: str,
    *,
    set_attributes: Mapping[str, str] | None = None,
    remove_attributes: Iterable[str] = (),
    text: str | None = None,
) -> str | None:
    """
    Exemple « <div id="x">Logo</div> → <header id="x">Logo</header> » : l'élément change de balise
    (``name``) en gardant ses vrais attributs, modifiés comme dans ``attribute_fix_example``.

    ``text`` remplace le contenu (par exemple un titre proposé par l'IA). Un contenu long est
    remplacé par « … ». Retourne None si l'élément n'est pas une balise ou si rien ne change.
    """
    if not isinstance(tag, Tag):
        return None
    changes: dict[str, str | None] = dict(set_attributes or {})
    changes.update({attribute: None for attribute in remove_attributes})
    content = _content(tag)
    new_content = content if text is None else shorten(text)
    before = f"{opening_tag(tag)}{content}</{tag.name}>"
    after = f"{_renamed(opening_tag(tag, **changes), tag.name, name)}{new_content}</{name}>"
    return None if before == after else f"{before} → {after}"


def wrap_example(tag: Tag, wrapper: str, *, text: str | None = None) -> str | None:
    """
    Exemple « <ul class="menu">…</ul> → <nav><ul class="menu">…</ul></nav> » : élément entouré de ``wrapper``.

    ``text`` : texte de l'élément à montrer (raccourci) à la place de son contenu HTML.
    """
    if not isinstance(tag, Tag):
        return None
    content = _content(tag) if text is None else shorten(text)
    element = f"{opening_tag(tag)}{content}</{tag.name}>"
    return f"{element} → <{wrapper}>{element}</{wrapper}>"


def with_example(recommendation: str | None, example: str | None) -> str | None:
    """Ajoute « Exemple : … » à une recommandation ; inchangée s'il n'y a pas de recommandation ou d'exemple."""
    if not recommendation or not example:
        return recommendation
    return f"{recommendation} Exemple : {example}"

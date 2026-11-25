"""
Outils communs aux critères 7.3 et 7.4 : composants natifs, écoutes d'événements
regroupées par élément et exemple de remplacement par un élément HTML natif.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.scripts import ListenerCall, ScriptSource, event_listeners, listener_target

ACTIVATION_EVENTS = frozenset(
    {
        "click",
        "dblclick",
        "auxclick",
        "contextmenu",
        "mousedown",
        "mouseup",
        "pointerdown",
        "pointerup",
        "touchstart",
        "touchend",
    }
)
HOVER_EVENTS = frozenset({"mouseover", "mouseenter", "pointerover", "pointerenter"})
KEY_EVENTS = frozenset({"keydown", "keyup", "keypress"})
FOCUS_EVENTS = frozenset({"focus", "focusin"})
FIELD_EVENTS = frozenset({"change", "input", "blur", "focusout"})
USER_EVENTS = ACTIVATION_EVENTS | HOVER_EVENTS | KEY_EVENTS | FOCUS_EVENTS | FIELD_EVENTS

_TEXT_INPUTS = frozenset({"", "text", "search", "email", "tel", "url", "password", "number", "date"})
_NAVIGATION_URL = re.compile(
    r"(?:location(?:\s*\.\s*href)?\s*=|location\s*\.\s*(?:assign|replace)\s*\()\s*['\"]([^'\"]+)['\"]"
)


def is_disabled(element: Tag) -> bool:
    return element.has_attr("disabled") or str(element.get("aria-disabled") or "").lower() == "true"


def is_native_control(element: Tag) -> bool:
    """Élément HTML qui reçoit le focus et s'active au clavier sans script (bouton, lien, champ…)."""
    name = element.name
    if name in {"a", "area"}:
        return element.has_attr("href")
    if name == "input":
        return str(element.get("type") or "").strip().lower() != "hidden"
    if name in {"audio", "video"}:
        return element.has_attr("controls")
    if str(element.get("contenteditable") or "").lower() in {"", "true"} and element.has_attr("contenteditable"):
        return True
    return name in {"button", "select", "textarea", "summary", "iframe"}


def tabindex(element: Tag) -> int | None:
    try:
        return int(str(element.get("tabindex")).strip())
    except ValueError:
        return None


def is_focusable(element: Tag) -> bool:
    """Atteignable avec la touche Tab : élément natif, ou tabindex positif ou nul."""
    index = tabindex(element)
    if index is not None:
        return index >= 0
    return is_native_control(element)


def is_explicit_button_or_link(element: Tag) -> bool:
    """Bouton (button, input submit / button / image / reset) ou lien (a href) natif."""
    if element.name == "button":
        return True
    if element.name == "input":
        return str(element.get("type") or "").strip().lower() in {"submit", "button", "image", "reset"}
    return element.name in {"a", "area"} and element.has_attr("href")


def is_text_field(element: Tag) -> bool:
    if element.name in {"select", "textarea"}:
        return True
    return element.name == "input" and str(element.get("type") or "").strip().lower() in _TEXT_INPUTS


@dataclass
class ElementHandlers:
    """Écoutes d'événements d'un élément, en attribut ou ajoutées par un script."""

    element: Tag
    listeners: list[ListenerCall] = field(default_factory=list)

    @property
    def events(self) -> set[str]:
        return {listener.event for listener in self.listeners}

    def code(self, events: frozenset[str] | set[str]) -> str:
        return " ; ".join(listener.code.strip() for listener in self.listeners if listener.event in events)


def handlers_by_element(
    sources: list[ScriptSource], soup: BeautifulSoup, events: frozenset[str] = USER_EVENTS
) -> tuple[list[ElementHandlers], list[ListenerCall], list[ListenerCall]]:
    """
    Écoutes regroupées par élément, dans l'ordre du document ; écoutes globales
    (document, window, body) ; écoutes de script dont la cible n'est pas trouvée.
    """
    grouped: dict[int, ElementHandlers] = {}
    global_listeners: list[ListenerCall] = []
    unresolved: list[ListenerCall] = []
    for listener in event_listeners(sources, soup, set(events)):
        target = listener_target(sources, soup, listener)
        if isinstance(target, Tag):
            grouped.setdefault(id(target), ElementHandlers(target)).listeners.append(listener)
        elif target == "document":
            global_listeners.append(listener)
        else:
            unresolved.append(listener)
    ordered = [grouped[id(element)] for element in soup.find_all(True) if id(element) in grouped]
    return ordered, global_listeners, unresolved


def native_replacement(element: Tag, code: str = "") -> str:
    """
    « Exemple : avant → après » qui remplace un élément cliquable par son équivalent natif :
    un lien si le script change de page vers une adresse écrite dans le code (ou si le
    composant a le rôle link, avec une adresse à compléter), sinon un bouton.
    """
    url = _NAVIGATION_URL.search(code)
    removed: dict[str, str | None] = {"role": None, "tabindex": None}
    if url:
        removed.update({name: None for name in element.attrs if str(name).lower().startswith("on")})
        head = f'<a href="{url.group(1)}"'
    elif str(element.get("role") or "").strip().lower() == "link":
        head = '<a href="[adresse de destination]"'
    else:
        head = '<button type="button"'
    rest = opening_tag(element, **removed)[len(element.name) + 1 :]
    after = head + (rest if rest.startswith(" ") or rest == ">" else " " + rest)
    return f" Exemple : {opening_tag(element)} → {after}"

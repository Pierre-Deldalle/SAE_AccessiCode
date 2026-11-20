"""
Composants d'interface générés ou contrôlés par script (thème RGAA 7).

Repère les composants, leur rôle (explicite ou implicite), leur nom accessible
et leur intitulé visible. Le calcul du nom reste partiel : il suit l'ordre
d'aria-labelledby, aria-label, label, contenu, title, placeholder, sans
remplacer le calcul complet du navigateur. Aucune décision RGAA n'est prise ici.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import get_labelledby_text, get_matching_label, get_wrapping_label
from accessi_code.analysis.structure import accessible_text, is_hidden

# Rôles WAI-ARIA des composants d'interface (widgets) et de leurs conteneurs interactifs.
INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "checkbox",
        "combobox",
        "grid",
        "gridcell",
        "link",
        "listbox",
        "menu",
        "menubar",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "option",
        "progressbar",
        "radio",
        "radiogroup",
        "scrollbar",
        "searchbox",
        "slider",
        "spinbutton",
        "switch",
        "tab",
        "tablist",
        "tabpanel",
        "textbox",
        "tree",
        "treegrid",
        "treeitem",
        "dialog",
        "alertdialog",
    }
)

# Rôles dont le nom peut venir du contenu (WAI-ARIA « name from content »).
NAME_FROM_CONTENT = frozenset(
    {
        "button",
        "checkbox",
        "gridcell",
        "link",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "option",
        "radio",
        "switch",
        "tab",
        "treeitem",
    }
)

# Conteneurs dont le nom n'est pas obligatoire (WAI-ARIA 1.2) : leurs éléments sont jugés un par un.
NAME_OPTIONAL = frozenset({"menu", "menubar", "tablist", "scrollbar", "gridcell"})

# États obligatoires (WAI-ARIA 1.2) lorsque le rôle est porté par un élément non natif.
REQUIRED_STATES: dict[str, tuple[str, ...]] = {
    "checkbox": ("aria-checked",),
    "radio": ("aria-checked",),
    "switch": ("aria-checked",),
    "menuitemcheckbox": ("aria-checked",),
    "menuitemradio": ("aria-checked",),
    "slider": ("aria-valuenow",),
    "scrollbar": ("aria-valuenow",),
    "combobox": ("aria-expanded",),
}

# Éléments qui portent un gestionnaire sans être des composants d'interface.
NOT_COMPONENTS = frozenset({"html", "body", "head", "form", "script", "style", "template", "noscript", "iframe"})

_EVENT_ATTRIBUTE = re.compile(r"^on[a-z]+$")

_INPUT_ROLES = {
    "button": "button",
    "submit": "button",
    "reset": "button",
    "image": "button",
    "checkbox": "checkbox",
    "radio": "radio",
    "range": "slider",
    "number": "spinbutton",
    "search": "searchbox",
}
_TEXT_INPUTS = {"", "text", "email", "tel", "url", "password"}
_DEFAULT_BUTTON_LABELS = {"submit": "Envoyer", "reset": "Réinitialiser"}


def normalize(value: str) -> str:
    return " ".join(value.split())


def explicit_role(element: Tag) -> str:
    """Premier rôle déclaré (role peut contenir une liste de repli)."""
    tokens = str(element.get("role") or "").strip().lower().split()
    return tokens[0] if tokens else ""


def implicit_role(element: Tag) -> str:
    """Rôle natif d'un élément HTML interactif, ou chaîne vide."""
    name = element.name
    if name == "button":
        return "button"
    if name == "a":
        return "link" if element.has_attr("href") else ""
    if name == "input":
        kind = str(element.get("type") or "").strip().lower()
        if kind == "hidden":
            return ""
        if kind in _INPUT_ROLES:
            return _INPUT_ROLES[kind]
        return "textbox"
    if name == "select":
        multiple = element.has_attr("multiple") or str(element.get("size") or "1").strip() not in {"", "0", "1"}
        return "listbox" if multiple else "combobox"
    if name == "textarea":
        return "textbox"
    if name == "summary":
        return "button"
    if name == "option":
        return "option"
    if name == "progress":
        return "progressbar"
    return ""


def component_role(element: Tag) -> tuple[str, str]:
    """(rôle, source) : rôle explicite s'il est un rôle de composant, sinon rôle natif."""
    role = explicit_role(element)
    if role in INTERACTIVE_ROLES:
        return role, "role"
    native = implicit_role(element)
    if native:
        return native, "natif"
    return "", "aucun"


def has_event_handler(element: Tag) -> bool:
    return any(_EVENT_ATTRIBUTE.match(str(name).lower()) for name in element.attrs)


def script_components(soup: BeautifulSoup) -> list[Tag]:
    """
    Composants contrôlés par script : éléments avec un gestionnaire d'événement
    (``onclick``…) ou un rôle de composant d'interface, visibles, dans l'ordre du document.
    """
    components: list[Tag] = []
    for element in soup.find_all(True):
        if element.name in NOT_COMPONENTS:
            continue
        if not (has_event_handler(element) or explicit_role(element) in INTERACTIVE_ROLES):
            continue
        if is_hidden(element):
            continue
        components.append(element)
    return components


def _is_text_field(element: Tag) -> bool:
    if element.name in {"select", "textarea"}:
        return True
    return element.name == "input" and str(element.get("type") or "").strip().lower() not in {
        "button",
        "submit",
        "reset",
        "image",
        "hidden",
    }


def _label_text(element: Tag, soup: BeautifulSoup) -> str:
    for label in (get_matching_label(element, soup), get_wrapping_label(element)):
        if isinstance(label, Tag):
            text = normalize(label.get_text(" ", strip=True))
            if text:
                return text
    return ""


def visible_label(element: Tag, soup: BeautifulSoup) -> str:
    """Intitulé visible : texte affiché du composant, ou étiquette d'un champ."""
    if _is_text_field(element):
        return _label_text(element, soup)
    role, _ = component_role(element)
    if element.name == "input":
        kind = str(element.get("type") or "").strip().lower()
        return normalize(str(element.get("value") or _DEFAULT_BUTTON_LABELS.get(kind, "")))
    if role in NAME_FROM_CONTENT or element.name in {"button", "a", "summary"}:
        return normalize(element.get_text(" ", strip=True))
    return ""


def component_name(element: Tag, soup: BeautifulSoup) -> tuple[str, str]:
    """(nom accessible, source) ; ("", "aucun") si aucun nom n'est trouvé."""
    valid, text = get_labelledby_text(element, soup)
    if valid and normalize(text):
        return normalize(text), "aria-labelledby"

    label = normalize(str(element.get("aria-label") or ""))
    if label:
        return label, "aria-label"

    if _is_text_field(element):
        text = _label_text(element, soup)
        if text:
            return text, "label"

    if element.name == "input":
        kind = str(element.get("type") or "").strip().lower()
        if kind == "image":
            alt = normalize(str(element.get("alt") or ""))
            if alt:
                return alt, "alt"
        elif kind in {"button", "submit", "reset"}:
            value = normalize(str(element.get("value") or _DEFAULT_BUTTON_LABELS.get(kind, "")))
            if value:
                return value, "value"

    role, _ = component_role(element)
    if role in NAME_FROM_CONTENT or element.name in {"button", "a", "summary"}:
        text = accessible_text(element)
        if text:
            return text, "contenu"

    title = normalize(str(element.get("title") or ""))
    if title:
        return title, "title"

    placeholder = normalize(str(element.get("placeholder") or ""))
    if placeholder and _is_text_field(element):
        return placeholder, "placeholder"

    return "", "aucun"


def missing_states(element: Tag, role: str, source: str) -> list[str]:
    """États obligatoires absents pour un rôle explicite posé sur un élément non natif."""
    if source != "role" or implicit_role(element) == role:
        return []
    return [state for state in REQUIRED_STATES.get(role, ()) if not element.has_attr(state)]


def component_identifier(element: Tag, index: int) -> str:
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return f"{element.name}#{element_id.strip()}"
    return f"{element.name}[index={index}]"


def interface_controls(soup: BeautifulSoup, limit: int = 40) -> list[str]:
    """
    Contrôles d'interface de la page sous la forme « rôle « nom » » (boutons,
    champs, composants à rôle), pour donner du contexte à un jugement.
    """
    controls: list[str] = []
    for element in soup.find_all(["button", "input", "select", "textarea", "summary"]) + script_components(soup):
        if element.name == "input" and str(element.get("type") or "").lower() == "hidden":
            continue
        role, _ = component_role(element)
        name, _ = component_name(element, soup)
        entry = f"{role or element.name} « {name} »" if name else f"{role or element.name} (sans nom)"
        if entry not in controls:
            controls.append(entry)
        if len(controls) >= limit:
            break
    return controls

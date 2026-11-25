"""
Exemples « avant / après » des corrections mécaniques du thème 11, construits avec les
vrais attributs de l'élément trouvé. Les textes qui dépendent du sens (intitulé d'une
étiquette, légende d'un groupe) restent entre crochets, à compléter par l'utilisateur.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from accessi_code.analysis.forms import clean
from accessi_code.analysis.location import opening_tag

# Éléments HTML qu'un label for peut désigner.
_LABELABLE = frozenset({"input", "select", "textarea", "button", "meter", "output", "progress"})

LABEL_PLACEHOLDER = "[intitulé du champ]"
LEGEND_PLACEHOLDER = "[nature commune des champs]"
CATEGORY_PLACEHOLDER = "[catégorie des options]"


def example(before: str, after: str) -> str:
    """Texte à ajouter à la fin d'une recommandation."""
    return f" Exemple : {before} → {after}"


def free_id(field: Tag, soup: BeautifulSoup) -> str:
    """Identifiant à donner au champ : son id, sinon tiré de son name (et de sa valeur pour un choix), libre."""
    existing = clean(field.get("id"))
    if existing:
        return existing
    base = clean(field.get("name")) or field.name or "champ"
    if clean(field.get("type")).lower() in {"radio", "checkbox"} and clean(field.get("value")):
        base = f"{base}-{clean(field.get('value'))}"
    base = re.sub(r"\s+", "-", base)
    candidate, number = base, 2
    while soup.find(id=candidate) is not None:
        candidate, number = f"{base}-{number}", number + 1
    return candidate


def label_example(field: Tag, soup: BeautifulSoup) -> str:
    """
    Étiquette à ajouter au champ :
    - composant ARIA (div role=…) : aria-label, car un label for ne s'applique qu'aux champs HTML ;
    - case à cocher ou bouton radio suivi de son texte : ce texte placé dans un label for, après le champ ;
    - autre champ : label for placé avant, avec le placeholder comme intitulé s'il existe.
    Le champ reçoit un id s'il n'en a pas.
    """
    if field.name not in _LABELABLE:
        return example(opening_tag(field), opening_tag(field, **{"aria-label": LABEL_PLACEHOLDER}))
    field_id = free_id(field, soup)
    after = opening_tag(field, id=field_id)
    following = field.next_sibling
    if clean(field.get("type")).lower() in {"radio", "checkbox"} and isinstance(following, NavigableString):
        text = clean(str(following))
        if text and not isinstance(following, Comment):
            return example(f"{opening_tag(field)} {text}", f'{after} <label for="{field_id}">{text}</label>')
    text = clean(field.get("placeholder")) or LABEL_PLACEHOLDER
    return example(opening_tag(field), f'<label for="{field_id}">{text}</label>{after}')


def fieldset_example(first: Tag) -> str:
    """Regroupement de choix dans un fieldset avec sa légende."""
    return example(
        opening_tag(first), f"<fieldset><legend>{LEGEND_PLACEHOLDER}</legend>{opening_tag(first)} … </fieldset>"
    )


def legend_example(group: Tag) -> str:
    """Légende d'un fieldset, ou aria-label d'un groupe ARIA."""
    if group.name == "fieldset":
        legend = group.find("legend")
        if isinstance(legend, Tag):
            return example(f"{opening_tag(legend)}</legend>", f"{opening_tag(legend)}{LEGEND_PLACEHOLDER}</legend>")
        return example(opening_tag(group), f"{opening_tag(group)}<legend>{LEGEND_PLACEHOLDER}</legend>")
    return example(opening_tag(group), opening_tag(group, **{"aria-label": LEGEND_PLACEHOLDER}))


def optgroup_example(group: Tag, label: str | None = None) -> str:
    """Attribut label d'un optgroup (proposition de l'IA si elle existe)."""
    return example(opening_tag(group), opening_tag(group, label=label or CATEGORY_PLACEHOLDER))

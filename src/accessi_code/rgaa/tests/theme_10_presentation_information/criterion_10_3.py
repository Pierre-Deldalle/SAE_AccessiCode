"""
RGAA 4.1.2 — critère 10.3 : dans chaque page web, l'information reste-t-elle
compréhensible lorsque les feuilles de styles sont désactivées ?

Test 10.3.1. Sans feuille de style, le contenu est restitué dans l'ordre du
code. Le risque vient donc des propriétés CSS qui affichent le contenu dans un
autre ordre : ``order``, inversion flex (``*-reverse``), placement explicite dans
une grille, positionnement absolu ou fixe, flottement à droite.

- aucune de ces propriétés n'est appliquée à un élément du document → PASS ;
- sinon, chaque règle concernée est signalée → NEEDS_REVIEW : seul un humain
  peut dire si l'ordre du code reste compréhensible.

Pas d'IA : l'ordre d'affichage réel demande le rendu de la page.
Les techniques de masquage visuel (``clip``, ``width: 1px``…) ne sont pas
des changements d'ordre et sont ignorées.
"""

from __future__ import annotations

import re
from typing import Any

import soupsieve
from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.css import inline_style, stylesheet_rules
from accessi_code.analysis.sensory import identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

PASS_SUMMARY = "Aucune propriété CSS ne modifie l'ordre d'affichage : le contenu s'affiche dans l'ordre du code."
RECOMMENDATION = (
    "Désactiver les feuilles de style et vérifier que le contenu, lu dans l'ordre du code, reste compréhensible ; "
    "sinon, réorganiser le code dans l'ordre de lecture."
)

_NEUTRAL = {"", "0", "auto", "initial", "inherit", "unset", "revert", "none", "normal"}
_GRID_PLACEMENT = ("grid-area", "grid-row", "grid-column", "grid-row-start", "grid-column-start")
_VISUALLY_HIDDEN = re.compile(r"clip|width\s*:\s*1px|height\s*:\s*1px|-9999|-10000", re.IGNORECASE)
_PSEUDO_CLASS = re.compile(r":(?:hover|focus|focus-visible|focus-within|active|visited)\b")
# Le contenu généré (::before, ::after) relève du critère 10.2.
_PSEUDO_ELEMENT = re.compile(r"::?(?:before|after|first-line|first-letter|marker|placeholder)\b")


def reordering(properties: dict[str, str]) -> list[str]:
    """Déclarations qui peuvent afficher le contenu dans un ordre différent du code."""
    found: list[str] = []
    value = properties.get("order", "").strip().lower()
    if value not in _NEUTRAL:
        found.append(f"order: {value}")
    for name in ("flex-direction", "flex-flow"):
        value = properties.get(name, "").strip().lower()
        if "reverse" in value:
            found.append(f"{name}: {value}")
    for name in _GRID_PLACEMENT:
        value = properties.get(name, "").strip().lower()
        if value not in _NEUTRAL:
            found.append(f"{name}: {value}")
    if properties.get("grid-template-areas", "").strip().lower() not in _NEUTRAL:
        found.append("grid-template-areas")
    value = properties.get("position", "").strip().lower()
    if value in {"absolute", "fixed"}:
        serialized = " ".join(f"{key}:{item}" for key, item in properties.items())
        if not _VISUALLY_HIDDEN.search(serialized):
            found.append(f"position: {value}")
    value = properties.get("float", "").strip().lower()
    if value in {"right", "inline-end"}:
        found.append(f"float: {value}")
    return found


class Test1031(RGAATest):
    """10.3.1 : contenu compréhensible dans l'ordre du code."""

    test_id = "10.3.1"
    criterion_id = "10.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 10.3.1 nécessite un DOM.")
        soup = context.dom

        outcomes: list[Outcome] = []
        for rule in stylesheet_rules(context):
            declarations = reordering(rule.properties)
            if not declarations:
                continue
            elements = _matched(soup, rule.selector)
            if not elements:
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    rule.selector,
                    f"La règle « {rule.selector} {{ {'; '.join(declarations)} }} » peut afficher "
                    f"{len(elements)} élément(s) dans un ordre différent de celui du code.",
                    RECOMMENDATION,
                    declarations=declarations,
                    source=rule.source,
                    elements=[identifier(tag, index) for index, tag in enumerate(elements[:5])],
                )
            )

        for index, tag in enumerate(soup.find_all(style=True)):
            declarations = reordering(inline_style(tag))
            if declarations:
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        identifier(tag, index),
                        f"Le style en ligne « {'; '.join(declarations)} » peut afficher cet élément "
                        "dans un ordre différent de celui du code.",
                        RECOMMENDATION,
                        declarations=declarations,
                        source="inline",
                    )
                )

        if not outcomes:
            return TestResult(self.test_id, self.criterion_id, TestStatus.PASS, PASS_SUMMARY)
        return build_result(self, outcomes, empty_summary=PASS_SUMMARY, noun="règle(s) CSS")


def _matched(soup: BeautifulSoup, selector: str) -> list[Tag]:
    """Éléments du document visés par le sélecteur (pseudo-classes retirées, pseudo-éléments exclus)."""
    if _PSEUDO_ELEMENT.search(selector):
        return []
    cleaned = _PSEUDO_CLASS.sub("", selector).strip()
    if not cleaned:
        return []
    try:
        return [tag for tag in soupsieve.select(cleaned, soup) if isinstance(tag, Tag)]
    except Exception:
        return []

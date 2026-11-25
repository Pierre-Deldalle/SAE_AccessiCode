"""
RGAA 4.1.2 — critère 7.1 : chaque script est-il, si nécessaire, compatible
avec les technologies d'assistance ?

Composants concernés : éléments avec un gestionnaire d'événement (``onclick``…)
ou un rôle WAI-ARIA de composant d'interface (``analysis/components.py``).

- 7.1.1 (sans IA) : le composant expose un rôle et un nom, et les états
  obligatoires de son rôle (aria-checked, aria-valuenow, aria-expanded) ;
- 7.1.2 : la restitution par les technologies d'assistance ne peut être
  vérifiée qu'avec un lecteur d'écran → NEEDS_REVIEW, jamais PASS ni FAIL ;
- 7.1.3 : nom absent, rôle absent, ou intitulé visible absent du nom → FAIL
  sans IA ; sinon l'IA juge la pertinence du nom et du rôle.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import (
    NAME_OPTIONAL,
    component_identifier,
    component_name,
    component_role,
    missing_states,
    normalize,
    script_components,
    visible_label,
)
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

EMPTY_SUMMARY = "Aucun composant d'interface généré ou contrôlé par script."
NOUN = "composant(s) contrôlé(s) par script"
API_RECOMMENDATION = (
    "Donner au composant un rôle WAI-ARIA adapté, un nom accessible et les états de son rôle, "
    "ou utiliser un élément HTML natif équivalent."
)
NAME_RECOMMENDATION = "Donner au composant un nom qui décrit sa fonction et un rôle qui correspond à son comportement."

# Gestionnaire qui change de page : le composant se comporte comme un lien.
NAVIGATION = re.compile(r"location|href|window\.open|navigate", re.IGNORECASE)
# Valeur initiale proposée pour un état obligatoire absent (à adapter à l'état réel du composant).
# Attributs qui remplacent l'intitulé visible : les retirer rend au composant son intitulé.
NAME_OVERRIDES = frozenset({"aria-label", "aria-labelledby"})
STATE_EXAMPLES = {"aria-checked": "false", "aria-expanded": "false", "aria-valuenow": "[valeur actuelle]"}


def example(element: Tag, changes: dict[str, str | None]) -> str:
    """« Exemple : avant → après » sur la balise réelle du composant ; vide sans changement."""
    if not changes:
        return ""
    return f" Exemple : {opening_tag(element)} → {opening_tag(element, **changes)}"


def api_changes(element: Tag, role: str, states: list[str]) -> dict[str, str | None]:
    """Attributs à ajouter pour exposer un rôle et les états obligatoires (le nom dépend du sens)."""
    changes: dict[str, str | None] = {}
    if not role:
        handlers = " ".join(str(value) for name, value in element.attrs.items() if str(name).startswith("on"))
        changes["role"] = "link" if NAVIGATION.search(handlers) else "button"
        if not element.has_attr("tabindex"):
            changes["tabindex"] = "0"
    for state in states:
        changes[state] = STATE_EXAMPLES.get(state, "[valeur]")
    return changes


class ComponentTest(RGAATest):
    criterion_id = "7.1"
    required_capabilities = frozenset({Capability.DOM})

    def _components(self, context: AuditContext) -> tuple[BeautifulSoup, list[Tag]]:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom, script_components(context.dom)


class Test711(ComponentTest):
    """7.1.1 : nom, rôle et états exposés à l'API d'accessibilité."""

    test_id = "7.1.1"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup, components = self._components(context)
        if not components:
            return not_applicable(self, EMPTY_SUMMARY)

        outcomes: list[Outcome] = []
        for index, element in enumerate(components):
            role, role_source = component_role(element)
            name, name_source = component_name(element, soup)
            problems: list[str] = []
            if not role:
                problems.append("aucun rôle de composant (ni rôle WAI-ARIA, ni élément HTML natif)")
            if not name and role not in NAME_OPTIONAL:
                problems.append("aucun nom accessible")
            states = missing_states(element, role, role_source)
            if states:
                problems.append(f"état(s) obligatoire(s) du rôle {role} absent(s) : {', '.join(states)}")

            status = TestStatus.FAIL if problems else TestStatus.PASS
            outcomes.append(
                make_outcome(
                    status,
                    component_identifier(element, index),
                    f"Le composant n'expose pas ses informations d'accessibilité : {' ; '.join(problems)}."
                    if problems
                    else "",
                    API_RECOMMENDATION + example(element, api_changes(element, role, states)),
                    node=element,
                    role=role,
                    role_source=role_source,
                    name=name,
                    name_source=name_source,
                    missing_states=states,
                )
            )
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun=NOUN)


class Test712(ComponentTest):
    """7.1.2 : restitution correcte par les technologies d'assistance (vérification humaine)."""

    test_id = "7.1.2"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        _soup, components = self._components(context)
        if not components:
            return not_applicable(self, EMPTY_SUMMARY)

        return build_result(
            self,
            [
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    component_identifier(element, index),
                    "La restitution de ce composant (nom, rôle, valeur, changements d'état) doit être vérifiée "
                    "avec une technologie d'assistance.",
                    "Tester le composant avec un lecteur d'écran (NVDA, JAWS, VoiceOver).",
                    node=element,
                    role=component_role(element)[0],
                )
                for index, element in enumerate(components)
            ],
            empty_summary=EMPTY_SUMMARY,
            noun=NOUN,
        )


class Test713(ComponentTest):
    """7.1.3 : nom et rôle pertinents, nom contenant l'intitulé visible."""

    test_id = "7.1.3"

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup, components = self._components(context)
        if not components:
            return not_applicable(self, EMPTY_SUMMARY)

        outcomes: list[Outcome | None] = [None] * len(components)
        to_judge: list[tuple[int, RelevanceItem]] = []

        for position, element in enumerate(components):
            identifier = component_identifier(element, position)
            role, _ = component_role(element)
            name, name_source = component_name(element, soup)
            label = visible_label(element, soup)
            evidence = {"role": role, "name": name, "name_source": name_source, "visible_label": label}

            if not name and role in NAME_OPTIONAL:
                # Conteneur (menu, tablist…) : son nom n'est pas obligatoire, ses éléments sont jugés.
                outcomes[position] = make_outcome(TestStatus.NOT_APPLICABLE)
                continue

            if not name or not role:
                missing = " ni ".join(
                    part for part, absent in (("de rôle", not role), ("de nom accessible", not name)) if absent
                )
                outcomes[position] = make_outcome(
                    TestStatus.FAIL,
                    identifier,
                    f"Le composant n'a pas {missing} : il ne peut pas être pertinent.",
                    NAME_RECOMMENDATION + example(element, api_changes(element, role, [])),
                    node=element,
                    **evidence,
                )
                continue

            if _label_missing_from_name(label, name):
                outcomes[position] = make_outcome(
                    TestStatus.FAIL,
                    identifier,
                    f"Le nom accessible « {name} » ne contient pas l'intitulé visible « {label} ».",
                    "Faire commencer le nom accessible par l'intitulé visible du composant."
                    + (example(element, {name_source: None}) if name_source in NAME_OVERRIDES else ""),
                    node=element,
                    **evidence,
                )
                continue

            to_judge.append(
                (
                    position,
                    RelevanceItem(
                        text=name,
                        element_html=str(element)[:400],
                        context=normalize(element.parent.get_text(" ", strip=True))[:300]
                        if isinstance(element.parent, Tag)
                        else "",
                        details={"role": role, "visible_label": label, "name_source": name_source},
                    ),
                )
            )

        verdicts = await judge_relevance(services, "component_name", [item for _, item in to_judge])
        for (position, item), verdict in zip(to_judge, verdicts, strict=True):
            recommendation = verdict.recommendation(NAME_RECOMMENDATION)
            if verdict.suggestion:
                recommendation += example(components[position], {"aria-label": verdict.suggestion})
            outcomes[position] = make_outcome(
                verdict.status,
                component_identifier(components[position], position),
                verdict.message(
                    f"Le nom « {item.text} » ou le rôle {item.details['role']} du composant n'est pas pertinent.",
                    f"La pertinence du nom « {item.text} » et du rôle {item.details['role']} reste à vérifier.",
                ),
                recommendation,
                node=components[position],
                **item.details,
                **verdict.evidence,
            )

        return build_result(
            self, [item for item in outcomes if item is not None], empty_summary=EMPTY_SUMMARY, noun=NOUN
        )


def _words(text: str) -> str:
    """Texte réduit à ses lettres et chiffres : la ponctuation (« Recherche : ») est ignorée."""
    return normalize("".join(character if character.isalnum() else " " for character in text)).lower()


def _label_missing_from_name(label: str, name: str) -> bool:
    """L'intitulé visible (hors symboles) n'apparaît pas dans le nom accessible."""
    label = _words(label)
    if not label:
        return False
    return label not in _words(name)

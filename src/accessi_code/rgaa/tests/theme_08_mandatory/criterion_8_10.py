"""
RGAA 4.1.2 — critère 8.10 : dans chaque page web, les changements du sens de
lecture sont-ils signalés ?

Le sens d'un texte se déduit de ses lettres (écritures hébraïque, arabe…),
sans IA :

- 8.10.1 : chaque texte écrit dans le sens opposé au sens par défaut de la
  page est placé dans un élément dont l'attribut dir (ou celui d'un parent)
  indique ce sens → PASS, sinon FAIL. Aucun texte de ce type → NOT_APPLICABLE ;
- 8.10.2 : chaque attribut dir (hors html) a une valeur conforme, rtl ou ltr
  (``auto`` n'est pas admis par le RGAA), et pertinente : elle correspond au
  sens du texte de l'élément.
"""

from __future__ import annotations

from copy import copy
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.language import (
    DIRECTIONS,
    default_direction,
    effective_direction,
    letter_counts,
    opposite_direction_elements,
    text_direction,
    text_without_marked,
)
from accessi_code.analysis.location import html_opening_tag
from accessi_code.analysis.sensory import identifier
from accessi_code.analysis.structure import is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_08_mandatory._common import html_example

LABELS = {"rtl": "de droite à gauche", "ltr": "de gauche à droite"}


def _direction_recommendation(tag: Tag, direction: str | None, recommendation: str) -> str:
    if direction is None or tag.name in {"[document]", "html", "body"} or tag.find(True) is not None:
        return recommendation

    rtl, ltr = letter_counts(tag.get_text())
    # Un texte mixte peut nécessiter de baliser un passage seulement.
    opposite_count = ltr if direction == "rtl" else rtl
    if opposite_count or not (rtl or ltr):
        return recommendation

    corrected = copy(tag)
    corrected["dir"] = direction
    return html_example(recommendation, html_opening_tag(str(tag)), html_opening_tag(str(corrected)))


class _TextDirectionTest(RGAATest):
    criterion_id = "8.10"
    required_capabilities = frozenset({Capability.DOM})

    def _dom(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom


class Test8101(_TextDirectionTest):
    """8.10.1 : les textes de sens opposé sont signalés par dir."""

    test_id = "8.10.1"
    empty_summary = "Aucun texte écrit dans un sens de lecture différent du sens par défaut."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._dom(context)
        default = default_direction(soup)
        expected = "ltr" if default == "rtl" else "rtl"
        elements = opposite_direction_elements(soup)
        if not elements:
            return not_applicable(self, self.empty_summary)

        outcomes: list[Outcome] = []
        for index, (tag, text) in enumerate(elements):
            actual = effective_direction(tag, default)
            recommendation = f'Placer le passage dans un élément portant dir="{expected}".'
            outcomes.append(
                make_outcome(
                    TestStatus.PASS if actual == expected else TestStatus.FAIL,
                    identifier(tag, index),
                    ""
                    if actual == expected
                    else f"Ce texte écrit {LABELS[expected]} n'est pas placé dans un élément "
                    f'portant dir="{expected}".',
                    _direction_recommendation(tag, expected, recommendation) if actual != expected else None,
                    node=tag,
                    text=text[:200],
                    expected=expected,
                    effective=actual,
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty_summary, noun="texte(s)")


class Test8102(_TextDirectionTest):
    """8.10.2 : valeur de dir conforme (rtl ou ltr) et pertinente."""

    test_id = "8.10.2"
    empty_summary = "Aucun changement de sens de lecture (attribut dir) dans la page."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._dom(context)
        elements = [
            tag
            for tag in soup.find_all(attrs={"dir": True})
            if tag.name != "html" and tag.find_parent(["head", "template"]) is None and not is_hidden(tag)
        ]
        if not elements:
            return not_applicable(self, self.empty_summary)

        outcomes: list[Outcome] = []
        for index, tag in enumerate(elements):
            value = str(tag.get("dir") or "").strip().lower()
            element = identifier(tag, index)
            text = text_without_marked(tag, attributes=("dir",))
            direction = text_direction(text)
            if value not in DIRECTIONS:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        element,
                        f'La valeur dir="{value}" n\'est pas conforme : seules rtl et ltr sont admises.',
                        _direction_recommendation(
                            tag, direction, "Remplacer la valeur par rtl ou ltr selon le sens de lecture du texte."
                        ),
                        node=tag,
                        dir=value,
                    )
                )
                continue
            if direction is None:
                outcomes.append(make_outcome(TestStatus.NOT_APPLICABLE))
                continue
            relevant = direction == value
            outcomes.append(
                make_outcome(
                    TestStatus.PASS if relevant else TestStatus.FAIL,
                    element,
                    ""
                    if relevant
                    else f'La valeur dir="{value}" ne correspond pas au texte, écrit {LABELS[direction]}.',
                    _direction_recommendation(tag, direction, f'Utiliser dir="{direction}" pour ce texte.')
                    if not relevant
                    else None,
                    node=tag,
                    dir=value,
                    text_direction=direction,
                    text=text[:200],
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty_summary, noun="attribut(s) dir")

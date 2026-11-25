"""
RGAA 4.1.2 — critère 9.3 : dans chaque page web, chaque liste est-elle
correctement structurée ?

- Listes balisées : le balisage est vérifié dans le DOM (ul/ol + li,
  role="list" + role="listitem", dl + dt + dd).
- Listes visuelles non balisées (lignes commençant par des puces ou des
  numéros) : l'IA juge s'il s'agit bien d'une liste, auquel cas elle doit
  être balisée.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import StructureCandidate
from accessi_code.analysis.dom import get_element_identifier
from accessi_code.analysis.fix_examples import rename_example, shorten, with_example, wrap_example
from accessi_code.analysis.location import element_snippet
from accessi_code.analysis.structure import (
    is_hidden,
    list_candidates,
    list_structure_problems,
    text_lines,
    visual_list_items,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_structure
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

_NOT_CONTENT = {"script", "style", "template", "noscript"}
# Nombre d'éléments montrés dans l'exemple d'une liste visuelle à baliser.
EXAMPLE_ITEMS = 3


def list_fix_example(tag: Tag) -> str | None:
    """
    Correction du premier enfant mal balisé d'une liste : <li> dans ul / ol (un div, span ou p
    change de balise, un autre élément est entouré de <li>), role="listitem" dans role="list".
    Aucun exemple pour une liste vide ou une liste de description : la correction dépend du contenu.
    """
    children = [child for child in tag.find_all(True, recursive=False) if child.name not in _NOT_CONTENT]
    if tag.name in {"ul", "ol"}:
        wrong = next((child for child in children if child.name != "li"), None)
        if wrong is None:
            return None
        return rename_example(wrong, "li") if wrong.name in {"div", "span", "p"} else wrap_example(wrong, "li")
    if str(tag.get("role") or "").strip().lower() == "list":
        wrong = next((child for child in children if str(child.get("role") or "").lower() != "listitem"), None)
        return rename_example(wrong, wrong.name, set_attributes={"role": "listitem"}) if wrong else None
    return None


def visual_list_example(tag: Tag, *, ordered: bool) -> str | None:
    """Liste visuelle réécrite avec <ul> ou <ol> et <li>, à partir de ses vrais éléments (les premiers)."""
    items = visual_list_items(tag, ordered=ordered)
    if not items:
        return None
    name = "ol" if ordered else "ul"
    shown = "".join(f"<li>{shorten(item, 40)}</li>" for item in items[:EXAMPLE_ITEMS])
    more = "<li>…</li>" if len(items) > EXAMPLE_ITEMS else ""
    # Liste faite de paragraphes consécutifs : seul le premier est montré avant la correction.
    series = len(text_lines(tag)) < len(items)
    return f"{element_snippet(tag, 100)}{' …' if series else ''} → <{name}>{shown}{more}</{name}>"


class _ListTest(RGAATest):
    """Structure des listes d'un type donné."""

    criterion_id = "9.3"
    required_capabilities = frozenset({Capability.DOM})

    list_tag: ClassVar[str]
    label: ClassVar[str]
    recommendation: ClassVar[str]
    # None : pas de repérage de listes visuelles pour ce type.
    candidates_ordered: ClassVar[bool | None] = None
    with_aria_lists: ClassVar[bool] = False

    def lists(self, soup: BeautifulSoup) -> list[Tag]:
        found = [tag for tag in soup.find_all(self.list_tag) if not is_hidden(tag)]
        if self.with_aria_lists:
            found += [
                tag
                for tag in soup.find_all(attrs={"role": True})
                if str(tag.get("role")).strip().lower() == "list"
                and tag.name not in {"ul", "ol"}
                and self._aria_list_matches(tag)
                and not is_hidden(tag)
            ]
        return found

    def _aria_list_matches(self, tag: Tag) -> bool:
        return True

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        soup = context.dom

        lists = self.lists(soup)
        candidates = (
            list_candidates(soup, ordered=self.candidates_ordered) if self.candidates_ordered is not None else []
        )
        if not lists and not candidates:
            return not_applicable(self, f"Aucune {self.label} dans la page.")

        outcomes = []
        for index, tag in enumerate(lists):
            problems = list_structure_problems(tag)
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    get_element_identifier(tag, index),
                    "La liste est mal structurée : " + " ; ".join(problems) + ".",
                    with_example(self.recommendation, list_fix_example(tag)),
                    node=tag,
                )
                if problems
                else make_outcome(TestStatus.PASS)
            )

        items = [
            StructureCandidate(
                text="\n".join(text_lines(tag))[:500],
                element_html=str(tag)[:500],
                context=_previous_text(tag),
            )
            for tag in candidates
        ]
        verdicts = await judge_structure(services, "list", items)
        for index, (tag, verdict) in enumerate(zip(candidates, verdicts, strict=True)):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    get_element_identifier(tag, index),
                    verdict.message(
                        f"Ce passage est une {self.label} qui n'est pas balisée comme telle.",
                        f"Ce passage ressemble à une {self.label} non balisée.",
                    ),
                    with_example(self.recommendation, visual_list_example(tag, ordered=bool(self.candidates_ordered)))
                    if verdict.status is TestStatus.FAIL
                    else self.recommendation,
                    node=tag,
                    text=items[index].text[:200],
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary=f"Aucune {self.label} dans la page.", noun="liste(s)")


def _previous_text(tag: Tag, limit: int = 200) -> str:
    sibling = tag.find_previous_sibling()
    return sibling.get_text(" ", strip=True)[:limit] if isinstance(sibling, Tag) else ""


class Test931(_ListTest):
    """9.3.1 : chaque liste non ordonnée est structurée avec ul + li ou role="list" + role="listitem"."""

    test_id = "9.3.1"
    list_tag = "ul"
    label = "liste non ordonnée"
    recommendation = 'Baliser la liste avec <ul> et <li> (ou role="list" et role="listitem").'
    candidates_ordered = False
    with_aria_lists = True

    def _aria_list_matches(self, tag: Tag) -> bool:
        # Une liste ARIA dont les items sont numérotés relève de 9.3.2.
        return not _numbered(tag)


class Test932(_ListTest):
    """9.3.2 : chaque liste ordonnée est structurée avec ol + li ou role="list" + role="listitem"."""

    test_id = "9.3.2"
    list_tag = "ol"
    label = "liste ordonnée"
    recommendation = 'Baliser la liste avec <ol> et <li> (ou role="list" et role="listitem").'
    candidates_ordered = True
    with_aria_lists = True

    def _aria_list_matches(self, tag: Tag) -> bool:
        return _numbered(tag)


class Test933(_ListTest):
    """9.3.3 : chaque liste de description est structurée avec dl, dt et dd."""

    test_id = "9.3.3"
    list_tag = "dl"
    label = "liste de description"
    recommendation = "Baliser la liste avec <dl>, <dt> pour les termes et <dd> pour les descriptions."


def _numbered(tag: Tag) -> bool:
    items = tag.find_all(attrs={"role": "listitem"}, recursive=False)
    return bool(items) and all(re.match(r"^\s*\d+[.)]\s", item.get_text(" ", strip=True)) for item in items)

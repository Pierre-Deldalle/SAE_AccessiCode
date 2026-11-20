"""
RGAA 4.1.2 — critère 7.2 : pour chaque script ayant une alternative, cette
alternative est-elle pertinente ?

Test 7.2.1 : chaque alternative ``<noscript>`` est jugée par l'IA (donne-t-elle
accès à des contenus et fonctionnalités similaires ?). Une alternative vide
est non conforme sans appel IA. Les ``<noscript>`` de l'en-tête et ceux qui
ne contiennent qu'une image de suivi (pixel 1×1) ne sont pas des alternatives
destinées à l'utilisateur et sont ignorés.

Test 7.2.2 : non encore implémenté (suivi des mises à jour du DOM).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

EMPTY_SUMMARY = "Aucun script avec une alternative <noscript>."
RECOMMENDATION = (
    "Fournir dans l'alternative un accès aux mêmes contenus et fonctionnalités que le script "
    "(contenu équivalent, lien vers une page alternative, formulaire traité côté serveur)."
)


def normalize(value: str) -> str:
    return " ".join(value.split())


def _is_tracking_pixel(tag: Tag) -> bool:
    width = str(tag.get("width") or "").strip()
    height = str(tag.get("height") or "").strip()
    style = str(tag.get("style") or "").replace(" ", "").lower()
    return (width in {"0", "1"} and height in {"0", "1"}) or "display:none" in style


def user_alternatives(soup: BeautifulSoup) -> list[Tag]:
    """<noscript> du corps de page, hors images ou cadres de suivi."""
    alternatives: list[Tag] = []
    for noscript in soup.find_all("noscript"):
        if noscript.find_parent("head") is not None:
            continue
        embedded = noscript.find_all(["img", "iframe"])
        if embedded and not normalize(noscript.get_text(" ", strip=True)) and all(map(_is_tracking_pixel, embedded)):
            continue
        alternatives.append(noscript)
    return alternatives


def script_context(noscript: Tag) -> str:
    """Scripts voisins et texte autour de l'alternative, pour situer la fonctionnalité remplacée."""
    parts: list[str] = []
    for script in [noscript.find_previous_sibling("script"), noscript.find_next_sibling("script")]:
        if isinstance(script, Tag):
            src = str(script.get("src") or "").strip()
            code = normalize(script.get_text(" ", strip=True))[:200]
            parts.append(f"Script voisin : {src or code or '(vide)'}")
    if isinstance(noscript.parent, Tag):
        around = normalize(noscript.parent.get_text(" ", strip=True))[:300]
        if around:
            parts.append(f"Contenu autour : {around}")
    return " — ".join(parts)


def noscript_identifier(noscript: Tag, index: int) -> str:
    element_id = noscript.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return f"noscript#{element_id.strip()}"
    return f"noscript[index={index}]"


class Test721(RGAATest):
    """7.2.1 : pertinence de l'alternative à un script."""

    test_id = "7.2.1"
    criterion_id = "7.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 7.2.1 nécessite un DOM.")

        alternatives = user_alternatives(context.dom)
        if not alternatives:
            return not_applicable(self, EMPTY_SUMMARY)

        outcomes: list[Outcome | None] = [None] * len(alternatives)
        to_judge: list[tuple[int, RelevanceItem]] = []
        for index, noscript in enumerate(alternatives):
            text = normalize(noscript.get_text(" ", strip=True))
            has_content = bool(text) or noscript.find(["a", "form", "img", "iframe", "video"]) is not None
            if not has_content:
                outcomes[index] = make_outcome(
                    TestStatus.FAIL,
                    noscript_identifier(noscript, index),
                    "L'alternative <noscript> est vide : elle ne donne accès à aucun contenu.",
                    RECOMMENDATION,
                )
                continue
            to_judge.append(
                (
                    index,
                    RelevanceItem(
                        text=text or "(aucun texte)",
                        element_html=str(noscript)[:400],
                        context=script_context(noscript),
                    ),
                )
            )

        verdicts = await judge_relevance(services, "script_alternative", [item for _, item in to_judge])
        for (index, item), verdict in zip(to_judge, verdicts, strict=True):
            outcomes[index] = make_outcome(
                verdict.status,
                noscript_identifier(alternatives[index], index),
                verdict.message(
                    "L'alternative au script ne donne pas accès à des contenus et fonctionnalités similaires.",
                    "La pertinence de l'alternative au script reste à vérifier.",
                ),
                RECOMMENDATION,
                alternative=item.text[:300],
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=EMPTY_SUMMARY,
            noun="alternative(s) <noscript>",
        )


class Test722(RGAATest):
    test_id = "7.2.2"
    criterion_id = "7.2"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 7.2.2 nécessite un DOM.")

        soup = context.dom

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NOT_APPLICABLE,
            summary="Le test 7.2.2 nécessite un suivi des changements DOM en temps réel qui n'est pas encore implémenté.",
            tested_elements=0,
        )

    def _get_element_identifier(self, element: Tag, index: int) -> str:
        """Generate a unique identifier for the element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"

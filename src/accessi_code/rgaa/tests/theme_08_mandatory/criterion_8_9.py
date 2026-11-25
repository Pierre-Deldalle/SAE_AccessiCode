"""
RGAA 4.1.2 — critère 8.9 : dans chaque page web, les balises (à l'exception
de <div>, <span> et <table>) ne doivent pas être utilisées uniquement à des fins
de présentation. Cette règle est-elle respectée ?

Test 8.9.1. Pré-filtre DOM des usages de présentation :

- paragraphe ou titre vide (espacement) → FAIL, sans IA ;
- sauts de ligne <br> consécutifs (espacement) → FAIL, sans IA ;
- <blockquote> : l'IA dit s'il contient réellement une citation ; sinon il
  sert à indenter → FAIL ; incertain → NEEDS_REVIEW.

Aucun usage repéré → PASS (la règle porte sur la page entière).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.ai.schemas import StructureCandidate, StructureCandidateAnalysis
from accessi_code.analysis.location import element_snippet
from accessi_code.analysis.sensory import element_context, identifier
from accessi_code.analysis.structure import HEADING_TAGS, accessible_text, is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_batch
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome
from accessi_code.rgaa.tests.theme_08_mandatory._common import html_example

PASS_SUMMARY = (
    "Aucune balise utilisée uniquement pour la présentation n'a été repérée "
    "(paragraphes ou titres vides, sauts de ligne répétés, blockquote d'indentation)."
)
SPACING_RECOMMENDATION = "Supprimer la balise et gérer les espacements avec les feuilles de style (margin, padding)."
BREAK_RECOMMENDATION = "Garder un seul saut de ligne si nécessaire et gérer l'espacement supplémentaire en CSS."
QUOTE_RECOMMENDATION = "Réserver blockquote aux citations et gérer l'indentation avec les feuilles de style."
_EMBEDDED = ["img", "svg", "canvas", "video", "audio", "iframe", "object", "embed", "input", "select", "textarea"]


def _visible(tag: Tag) -> bool:
    return tag.find_parent(["head", "template", "noscript"]) is None and not is_hidden(tag)


def empty_elements(soup: BeautifulSoup) -> list[Tag]:
    """Paragraphes et titres sans texte ni contenu embarqué."""
    return [
        tag
        for tag in soup.find_all(["p", *HEADING_TAGS])
        if _visible(tag) and not accessible_text(tag).replace("\xa0", "").strip() and tag.find(_EMBEDDED) is None
    ]


def repeated_breaks(soup: BeautifulSoup) -> list[list[Tag]]:
    """Suites d'au moins deux <br> consécutifs (séparés par des blancs)."""
    found: list[list[Tag]] = []
    for br in soup.find_all("br"):
        if not _visible(br):
            continue
        previous = br.previous_sibling
        while isinstance(previous, NavigableString) and not previous.strip():
            previous = previous.previous_sibling
        if isinstance(previous, Tag) and previous.name == "br":
            continue  # déjà compté avec le premier de la suite
        group = [br]
        for sibling in br.next_siblings:
            if isinstance(sibling, NavigableString) and not sibling.strip():
                continue
            if not isinstance(sibling, Tag) or sibling.name != "br":
                break
            group.append(sibling)
        if len(group) > 1:
            found.append(group)
    return found


class Test891(RGAATest):
    """8.9.1 : pas de balise utilisée uniquement pour la présentation."""

    test_id = "8.9.1"
    criterion_id = "8.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 8.9.1 nécessite un DOM.")
        soup = context.dom

        outcomes: list[Outcome] = []
        for index, tag in enumerate(empty_elements(soup)):
            recommendation = SPACING_RECOMMENDATION
            if not tag.has_attr("id") and tag.find(True) is None:
                recommendation = html_example(recommendation, element_snippet(tag), "<!-- Espacement géré en CSS -->")
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(tag, index),
                    f"L'élément <{tag.name}> est vide : il ne sert qu'à créer un espacement.",
                    recommendation,
                    node=tag,
                    usage="empty_element",
                )
            )
        for index, group in enumerate(repeated_breaks(soup)):
            br = group[0]
            parent = br.parent if isinstance(br.parent, Tag) else br
            recommendation = BREAK_RECOMMENDATION
            if not any(tag.attrs for tag in group[1:]):
                recommendation = html_example(
                    recommendation, "".join(element_snippet(tag) for tag in group), element_snippet(br)
                )
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    f"{identifier(parent, index)} > br",
                    "Des sauts de ligne <br> consécutifs sont utilisés pour créer un espacement.",
                    recommendation,
                    node=br,
                    usage="repeated_br",
                )
            )

        quotes = [tag for tag in soup.find_all("blockquote") if _visible(tag)]
        items = [
            StructureCandidate(
                text=" ".join(tag.get_text(" ", strip=True).split())[:500],
                element_html=str(tag)[:400],
                context=element_context(tag),
            )
            for tag in quotes
        ]
        verdicts = await judge_batch(
            services,
            "structure_analyzer",
            "classify_candidates",
            "presentation_quote",
            items,
            verdict_field="should_be_marked",
            expected_type=StructureCandidateAnalysis,
            when_true=TestStatus.PASS,
            when_false=TestStatus.FAIL,
        )
        for index, (tag, verdict) in enumerate(zip(quotes, verdicts, strict=True)):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(tag, index),
                    verdict.message(
                        "L'élément blockquote ne contient pas de citation : il sert uniquement à indenter.",
                        "Vérifier que cet élément blockquote contient une citation.",
                    ),
                    verdict.recommendation(QUOTE_RECOMMENDATION),
                    node=tag,
                    usage="blockquote",
                    **verdict.evidence,
                )
            )

        if not outcomes:
            return TestResult(self.test_id, self.criterion_id, TestStatus.PASS, PASS_SUMMARY, tested_elements=1)
        return build_result(self, outcomes, empty_summary=PASS_SUMMARY, noun="usage(s) de balise")

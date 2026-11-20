"""
RGAA 4.1.2 — critère 9.1 : dans chaque page web, l'information est-elle
structurée par l'utilisation appropriée de titres ?

- 9.1.1 : la hiérarchie entre les titres est-elle pertinente ? Le texte officiel
  n'interdit pas les sauts de niveau : un saut (ou un premier titre qui n'est
  pas de niveau 1) est un point d'attention que l'IA juge au regard du plan.
- 9.1.2 : le contenu de chaque titre est-il pertinent ? Titre vide : non conforme ;
  sinon l'IA compare le titre au contenu de la section.
- 9.1.3 : chaque passage de texte constituant un titre est-il balisé (hx ou
  role="heading" + aria-level) ? role="heading" sans aria-level : non conforme ;
  les passages mis en forme comme des titres sont soumis à l'IA.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceAnalysis, RelevanceItem, StructureCandidate
from accessi_code.analysis.dom import get_element_identifier
from accessi_code.analysis.structure import (
    Heading,
    heading_candidates,
    headings,
    invalid_aria_headings,
    section_text,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import (
    AI_ERROR_MESSAGE,
    NO_AI_MESSAGE,
    analysis_evidence,
    get_analyzer,
    judge_relevance,
    judge_structure,
    status_from_verdict,
)
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable


def _dom(context: AuditContext, test_id: str) -> BeautifulSoup:
    if not isinstance(context.dom, BeautifulSoup):
        raise ValueError(f"Le test {test_id} nécessite un DOM.")
    return context.dom


def _identifier(tag: Tag, soup: BeautifulSoup) -> str:
    return get_element_identifier(tag, soup.find_all(tag.name).index(tag))


def suspicious_levels(outline: list[Heading]) -> list[str]:
    """Sauts de niveau et premier titre qui n'est pas de niveau 1."""
    remarks: list[str] = []
    if outline and outline[0].level != 1:
        remarks.append(f"le premier titre est de niveau {outline[0].level} : « {outline[0].text[:80]} »")
    for previous, current in zip(outline, outline[1:], strict=False):
        if current.level > previous.level + 1:
            remarks.append(f"h{previous.level} → h{current.level} : « {current.text[:80]} »")
    return remarks


class Test911(RGAATest):
    """9.1.1 : la hiérarchie entre les titres est-elle pertinente ?"""

    test_id = "9.1.1"
    criterion_id = "9.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        outline = headings(soup)
        if not outline:
            return not_applicable(self, "Aucun titre dans la page.")

        remarks = suspicious_levels(outline)
        metadata = {"headings": len(outline), "levels": [item.level for item in outline], "remarks": remarks}
        if not remarks:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                f"{len(outline)} titre(s) : hiérarchie sans saut de niveau.",
                tested_elements=len(outline),
                metadata=metadata,
            )

        recommendation = "Organiser les niveaux de titres selon la structure réelle du contenu."
        analyzer = get_analyzer(services, "structure_analyzer")
        if analyzer is None:
            return self._result(
                TestStatus.NEEDS_REVIEW,
                f"La hiérarchie présente des sauts de niveau à vérifier. {NO_AI_MESSAGE}",
                recommendation,
                outline,
                metadata,
            )
        try:
            analysis = await analyzer.analyze_heading_hierarchy([(item.level, item.text) for item in outline], remarks)
            if not isinstance(analysis, RelevanceAnalysis):
                raise TypeError("RelevanceAnalysis attendu.")
        except Exception as error:
            metadata["error"] = f"{type(error).__name__}: {error}"
            return self._result(TestStatus.ERROR, AI_ERROR_MESSAGE, "Relancer l'audit.", outline, metadata)

        metadata["analysis"] = analysis_evidence(analysis)
        status = status_from_verdict(analysis.relevant, analysis.confidence)
        if status is TestStatus.PASS:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                f"{len(outline)} titre(s) : les sauts de niveau restent cohérents avec le contenu.",
                tested_elements=len(outline),
                metadata=metadata,
            )
        problems = " ; ".join(analysis.problems)
        message = (
            f"La hiérarchie des titres n'est pas pertinente. {analysis.explanation} {problems}".strip()
            if status is TestStatus.FAIL
            else f"La pertinence de la hiérarchie des titres reste incertaine. {analysis.explanation}".strip()
        )
        return self._result(status, message, recommendation, outline, metadata)

    def _result(self, status, message, recommendation, outline, metadata) -> TestResult:
        outcome = make_outcome(status, "titres de la page", message, recommendation, remarks=metadata["remarks"])
        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            message,
            findings=[outcome.finding] if outcome.finding else [],
            tested_elements=len(outline),
            metadata=metadata,
        )


class Test912(RGAATest):
    """9.1.2 : le contenu de chaque titre est-il pertinent ?"""

    test_id = "9.1.2"
    criterion_id = "9.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        outline = headings(soup)
        if not outline:
            return not_applicable(self, "Aucun titre dans la page.")

        recommendation = "Rédiger un titre qui décrit le contenu de la section qu'il introduit."
        outcomes = []
        to_judge = [item for item in outline if item.text]
        for item in outline:
            if not item.text:
                outcomes.append(
                    make_outcome(TestStatus.FAIL, _identifier(item.tag, soup), "Le titre est vide.", recommendation)
                )

        items = [
            RelevanceItem(
                text=item.text,
                element_html=str(item.tag)[:300],
                context=section_text(item, outline),
                details={"niveau": f"h{item.level}"},
            )
            for item in to_judge
        ]
        verdicts = await judge_relevance(services, "heading", items)
        for item, verdict in zip(to_judge, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    _identifier(item.tag, soup),
                    verdict.message(
                        f"Le titre « {item.text[:100]} » n'est pas pertinent.",
                        f"La pertinence du titre « {item.text[:100]} » reste à vérifier.",
                    ),
                    recommendation,
                    heading=item.text,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun titre dans la page.", noun="titre(s)")


class Test913(RGAATest):
    """9.1.3 : chaque passage de texte constituant un titre est-il structuré comme un titre ?"""

    test_id = "9.1.3"
    criterion_id = "9.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        outline = headings(soup)
        invalid = invalid_aria_headings(soup)
        candidates = heading_candidates(soup)

        if not outline and not invalid and not candidates:
            return not_applicable(self, "Aucun titre ni passage ressemblant à un titre.")

        recommendation = 'Baliser chaque titre avec h1 à h6 (ou role="heading" et aria-level).'
        outcomes = [make_outcome(TestStatus.PASS) for _ in outline]
        outcomes += [
            make_outcome(
                TestStatus.FAIL,
                _identifier(tag, soup),
                "L'élément a role=\"heading\" mais pas d'attribut aria-level valide (1 à 6).",
                'Ajouter aria-level="x" ou utiliser une balise hx.',
            )
            for tag in invalid
        ]

        structure_items = [
            StructureCandidate(
                text=tag.get_text(" ", strip=True),
                element_html=str(tag)[:400],
                context=_following_text(tag),
            )
            for tag in candidates
        ]
        verdicts = await judge_structure(services, "heading", structure_items)
        for tag, item, verdict in zip(candidates, structure_items, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    _identifier(tag, soup),
                    verdict.message(
                        f"Le passage « {item.text[:100]} » est un titre mais n'est pas balisé comme tel.",
                        f"Le passage « {item.text[:100]} » ressemble à un titre non balisé.",
                    ),
                    recommendation,
                    text=item.text,
                    **verdict.evidence,
                )
            )
        return build_result(
            self, outcomes, empty_summary="Aucun passage ressemblant à un titre non balisé.", noun="titre(s)"
        )


def _following_text(tag: Tag, limit: int = 300) -> str:
    sibling = tag.find_next_sibling()
    return sibling.get_text(" ", strip=True)[:limit] if isinstance(sibling, Tag) else ""

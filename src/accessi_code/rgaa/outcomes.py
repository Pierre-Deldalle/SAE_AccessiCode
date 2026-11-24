"""
Construction du résultat d'un test RGAA qui examine plusieurs éléments.

Un test produit un ``Outcome`` par élément (statut et, si besoin, l'observation
qui l'explique) ; ``build_result`` en déduit le statut global selon la priorité
des CONVENTIONS (FAIL > ERROR > NEEDS_REVIEW > NOT_TESTED > PASS > NOT_APPLICABLE).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bs4 import Tag

from accessi_code.analysis.location import locate
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.ai_decision import count_statuses, worst_status


@dataclass
class Outcome:
    """Statut d'un élément et l'observation qui l'explique."""

    status: TestStatus
    finding: Finding | None = None


def make_outcome(
    status: TestStatus,
    element: str | None = None,
    message: str = "",
    recommendation: str | None = None,
    *,
    node: Tag | None = None,
    file: str | None = None,
    line: int | None = None,
    **evidence: Any,
) -> Outcome:
    """Outcome avec un Finding, sauf pour PASS et NOT_APPLICABLE sans message."""
    if element is None or (status in {TestStatus.PASS, TestStatus.NOT_APPLICABLE} and not message):
        return Outcome(status)
    node_line, snippet = locate(node)
    return Outcome(
        status,
        Finding(
            element=element,
            message=message,
            recommendation=recommendation,
            evidence=evidence,
            line=line if line is not None else node_line,
            snippet=snippet,
            file=file,
        ),
    )


def build_result(
    test: Any,
    outcomes: list[Outcome],
    *,
    empty_summary: str,
    noun: str = "élément(s)",
    metadata: dict[str, Any] | None = None,
) -> TestResult:
    """TestResult agrégé ; aucun élément applicable → NOT_APPLICABLE avec ``empty_summary``."""
    statuses = [item.status for item in outcomes]
    counts = count_statuses(statuses)
    status = worst_status(statuses)
    tested = sum(1 for item in statuses if item is not TestStatus.NOT_APPLICABLE)

    if status is TestStatus.NOT_APPLICABLE:
        summary = empty_summary
    else:
        summary = (
            f"{tested} {noun} concerné(s) : {counts['pass']} conforme(s), "
            f"{counts['fail']} non conforme(s), {counts['needs_review']} à vérifier"
            + (f", {counts['error']} erreur(s)" if counts["error"] else "")
            + "."
        )

    return TestResult(
        test_id=test.test_id,
        criterion_id=test.criterion_id,
        status=status,
        summary=summary,
        findings=[item.finding for item in outcomes if item.finding is not None],
        tested_elements=tested,
        metadata={"candidates": len(outcomes), "statuses": counts, **(metadata or {})},
    )


def not_applicable(test: Any, summary: str) -> TestResult:
    return TestResult(test.test_id, test.criterion_id, TestStatus.NOT_APPLICABLE, summary)

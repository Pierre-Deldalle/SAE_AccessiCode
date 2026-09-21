
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_TESTED = "not_tested"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Finding:
    """Un problème ou une observation concernant un élément."""

    element: str
    message: str
    recommendation: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Résultat d'un test RGAA."""

    test_id: str
    criterion_id: str
    status: TestStatus
    summary: str
    findings: list[Finding] = field(default_factory=list)
    tested_elements: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
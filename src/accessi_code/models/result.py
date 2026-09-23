from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_TESTED = "not_tested"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"

@dataclass
class Finding:
    element: str
    message: str
    recommendation: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    test_id: str
    criterion_id: str
    status: TestStatus
    summary: str
    findings: list[Finding]
    tested_elements: int
    metadata: dict[str, Any]
"""Tests du calcul des synthèses par thématique."""

from accessi_code.models.audit_result import AuditResult, CriterionResult
from accessi_code.models.result import TestResult as Result
from accessi_code.models.result import TestStatus
from accessi_code.service.theme_summary import ThemeState, compute_score, summarize_themes


def criterion(cid: str, status: TestStatus) -> CriterionResult:
    test = Result(test_id=f"{cid}.1", criterion_id=cid, status=status, summary="")
    return CriterionResult(criterion_id=cid, status=status, summary="", tests=[test])


def result(*criteria: CriterionResult) -> AuditResult:
    return AuditResult(audit_id="a", status=TestStatus.FAIL, criteria=list(criteria))


def by_number(summaries):
    return {s.theme.number: s for s in summaries}


def test_score_uses_only_decided_criteria():
    criteria = [
        criterion("1.1", TestStatus.PASS),
        criterion("1.2", TestStatus.FAIL),
        criterion("1.3", TestStatus.NEEDS_REVIEW),
        criterion("1.4", TestStatus.NOT_APPLICABLE),
        criterion("1.5", TestStatus.ERROR),
    ]
    assert compute_score(criteria) == 50


def test_no_decided_criterion_means_no_score():
    assert compute_score([criterion("6.1", TestStatus.NEEDS_REVIEW)]) is None
    assert compute_score([]) is None


def test_always_thirteen_themes_in_order():
    summaries = summarize_themes(None, selected=set(), implemented=set())
    assert [s.theme.number for s in summaries] == list(range(1, 14))
    assert all(s.state == ThemeState.NOT_SELECTED for s in summaries)


def test_states_are_distinguished():
    audit = result(
        criterion("1.1", TestStatus.PASS),
        criterion("6.1", TestStatus.NEEDS_REVIEW),
        criterion("8.1", TestStatus.ERROR),
        criterion("11.1", TestStatus.NOT_TESTED),
        criterion("5.1", TestStatus.NOT_APPLICABLE),
    )
    summaries = by_number(summarize_themes(audit, selected={1, 2, 5, 6, 8, 11}, implemented={1, 5, 6, 8, 11}))

    assert summaries[1].state == ThemeState.SCORED and summaries[1].score == 100
    assert summaries[2].state == ThemeState.NOT_IMPLEMENTED and summaries[2].score is None
    assert summaries[3].state == ThemeState.NOT_SELECTED
    assert summaries[5].state == ThemeState.NOT_APPLICABLE
    assert summaries[6].state == ThemeState.NEEDS_REVIEW and summaries[6].score is None
    assert summaries[8].state == ThemeState.ERROR
    assert summaries[11].state == ThemeState.NOT_TESTED


def test_pending_review_counts_review_and_errors():
    audit = result(
        criterion("1.1", TestStatus.PASS),
        criterion("1.2", TestStatus.NEEDS_REVIEW),
        criterion("1.3", TestStatus.ERROR),
    )
    summary = by_number(summarize_themes(audit, selected={1}, implemented={1}))[1]
    assert summary.score == 100
    assert summary.pending_review == 2

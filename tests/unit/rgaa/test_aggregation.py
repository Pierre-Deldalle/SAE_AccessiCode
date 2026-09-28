from pathlib import Path

from accessi_code.models.audit_context import (
    AuditContext,
)
from accessi_code.models.result import (
    TestResult as Result,
)
from accessi_code.models.result import (
    TestStatus as Status,
)
from accessi_code.rgaa.aggregation import (
    ResultAggregator,
)


def create_context(
    tmp_path: Path,
) -> AuditContext:
    return AuditContext(
        audit_id="audit-123",
        workspace_path=tmp_path,
    )


def create_result(
    test_id: str,
    criterion_id: str,
    status: Status,
) -> Result:
    return Result(
        test_id=test_id,
        criterion_id=criterion_id,
        status=status,
        summary="Test.",
    )


def test_results_are_grouped_by_criterion(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1.1.1",
            "1.1",
            Status.PASS,
        ),
        create_result(
            "1.1.2",
            "1.1",
            Status.PASS,
        ),
        create_result(
            "5.1.1",
            "5.1",
            Status.FAIL,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    assert len(audit.criteria) == 2

    assert audit.criteria[0].criterion_id == "1.1"

    assert len(audit.criteria[0].tests) == 2


def test_fail_has_priority(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1",
            "1.1",
            Status.PASS,
        ),
        create_result(
            "2",
            "1.1",
            Status.ERROR,
        ),
        create_result(
            "3",
            "1.1",
            Status.FAIL,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    assert audit.criteria[0].status == Status.FAIL

    assert audit.status == Status.FAIL


def test_pass_and_not_applicable_gives_pass(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1",
            "1.1",
            Status.PASS,
        ),
        create_result(
            "2",
            "1.1",
            Status.NOT_APPLICABLE,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    assert audit.criteria[0].status == Status.PASS


def test_pass_and_not_tested_gives_not_tested(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1",
            "1.1",
            Status.PASS,
        ),
        create_result(
            "2",
            "1.1",
            Status.NOT_TESTED,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    assert audit.criteria[0].status == Status.NOT_TESTED


def test_all_not_applicable_gives_not_applicable(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1",
            "1.1",
            Status.NOT_APPLICABLE,
        ),
        create_result(
            "2",
            "1.1",
            Status.NOT_APPLICABLE,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    assert audit.criteria[0].status == Status.NOT_APPLICABLE


def test_empty_audit_is_not_tested(
    tmp_path,
):
    aggregator = ResultAggregator()

    audit = aggregator.aggregate(
        create_context(tmp_path),
        [],
    )

    assert audit.status == Status.NOT_TESTED

    assert audit.statistics.total_tests == 0


def test_statistics_are_correct(
    tmp_path,
):
    aggregator = ResultAggregator()

    results = [
        create_result(
            "1",
            "1",
            Status.PASS,
        ),
        create_result(
            "2",
            "2",
            Status.FAIL,
        ),
        create_result(
            "3",
            "3",
            Status.NEEDS_REVIEW,
        ),
        create_result(
            "4",
            "4",
            Status.ERROR,
        ),
        create_result(
            "5",
            "5",
            Status.NOT_TESTED,
        ),
    ]

    audit = aggregator.aggregate(
        create_context(tmp_path),
        results,
    )

    stats = audit.statistics

    assert stats.total_tests == 5
    assert stats.total_criteria == 5

    assert stats.passed_tests == 1
    assert stats.failed_tests == 1
    assert stats.needs_review_tests == 1
    assert stats.error_tests == 1
    assert stats.not_tested_tests == 1

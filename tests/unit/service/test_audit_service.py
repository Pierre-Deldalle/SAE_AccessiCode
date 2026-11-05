import pytest

from accessi_code.models.audit_context import (
    AuditContext,
)
from accessi_code.models.audit_result import (
    AuditResult,
)
from accessi_code.models.result import (
    TestResult as Result,
)
from accessi_code.models.result import (
    TestStatus as Status,
)
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import (
    TestRegistry as Registry,
)
from accessi_code.service.audit_service import (
    AuditService,
)


class PassingTest(RGAATest):
    test_id = "fake.1"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="OK",
        )


class FailingTest(RGAATest):
    test_id = "fake.2"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.FAIL,
            summary="Échec volontaire.",
        )


@pytest.mark.asyncio
async def test_audit_service_runs_and_aggregates(
    tmp_path,
):
    registry = Registry(
        [
            PassingTest(),
            FailingTest(),
        ]
    )

    service = AuditService(registry=registry)

    context = AuditContext(
        audit_id="audit-test",
        workspace_path=tmp_path,
    )

    result = await service.audit(context)

    assert isinstance(
        result,
        AuditResult,
    )

    assert result.audit_id == "audit-test"

    assert result.status == Status.FAIL

    assert result.statistics.total_tests == 2

    assert result.statistics.passed_tests == 1

    assert result.statistics.failed_tests == 1

    assert len(result.criteria) == 1

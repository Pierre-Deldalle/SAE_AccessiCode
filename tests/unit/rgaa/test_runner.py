from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.audit_context import (
    AuditContext,
)
from accessi_code.models.capabilities import (
    Capability,
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
from accessi_code.rgaa.runner import (
    TestRunner as Runner,
)


def create_context(
    tmp_path: Path,
    *,
    with_dom: bool = False,
) -> AuditContext:
    dom = None

    if with_dom:
        dom = BeautifulSoup(
            "<!DOCTYPE html><html></html>",
            "html.parser",
        )

    return AuditContext(
        audit_id="test-audit",
        workspace_path=tmp_path,
        dom=dom,
    )


class PassingTest(RGAATest):
    test_id = "fake.pass"
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
            summary="Succès.",
        )


class SecondPassingTest(RGAATest):
    test_id = "fake.pass.2"
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
            summary="Succès 2.",
        )


class CrashingTest(RGAATest):
    test_id = "fake.crash"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        raise RuntimeError("Erreur volontaire")


class RequiresDomTest(RGAATest):
    test_id = "fake.dom"
    criterion_id = "fake"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    def __init__(self):
        self.executed = False

    async def run(
        self,
        context,
        services=None,
    ):
        self.executed = True

        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="DOM disponible.",
        )


class InvalidReturnTest(RGAATest):
    test_id = "fake.invalid"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return "pas un Result"


class WrongIdTest(RGAATest):
    test_id = "fake.expected"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return Result(
            test_id="fake.wrong",
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="Identifiant invalide.",
        )


class ServiceAwareTest(RGAATest):
    test_id = "fake.services"
    criterion_id = "fake"

    def __init__(self):
        self.received_services = None

    async def run(
        self,
        context,
        services=None,
    ):
        self.received_services = services

        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="Services reçus.",
        )


@pytest.mark.asyncio
async def test_runner_executes_all_tests_in_order(
    tmp_path,
):
    registry = Registry(
        [
            PassingTest(),
            SecondPassingTest(),
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(create_context(tmp_path))

    assert [result.test_id for result in results] == [
        "fake.pass",
        "fake.pass.2",
    ]


@pytest.mark.asyncio
async def test_missing_capability_returns_not_tested(
    tmp_path,
):
    test = RequiresDomTest()

    registry = Registry(
        [
            test,
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(
        create_context(
            tmp_path,
            with_dom=False,
        )
    )

    assert len(results) == 1

    result = results[0]

    assert result.status == Status.NOT_TESTED

    assert test.executed is False

    assert "dom" in result.metadata["missing_capabilities"]


@pytest.mark.asyncio
async def test_available_capability_executes_test(
    tmp_path,
):
    test = RequiresDomTest()

    registry = Registry(
        [
            test,
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(
        create_context(
            tmp_path,
            with_dom=True,
        )
    )

    assert results[0].status == Status.PASS

    assert test.executed is True


@pytest.mark.asyncio
async def test_exception_becomes_error_and_audit_continues(
    tmp_path,
):
    registry = Registry(
        [
            CrashingTest(),
            PassingTest(),
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(create_context(tmp_path))

    assert len(results) == 2

    assert results[0].status == Status.ERROR

    assert results[1].status == Status.PASS

    assert results[0].metadata["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_invalid_return_type_becomes_error(
    tmp_path,
):
    registry = Registry(
        [
            InvalidReturnTest(),
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(create_context(tmp_path))

    assert results[0].status == Status.ERROR

    assert results[0].metadata["error_type"] == "TypeError"


@pytest.mark.asyncio
async def test_wrong_test_id_becomes_error(
    tmp_path,
):
    registry = Registry(
        [
            WrongIdTest(),
        ]
    )

    runner = Runner(registry)

    results = await runner.run_all(create_context(tmp_path))

    assert results[0].status == Status.ERROR


@pytest.mark.asyncio
async def test_services_are_forwarded_to_tests(
    tmp_path,
):
    expected_services = object()

    test = ServiceAwareTest()

    registry = Registry(
        [
            test,
        ]
    )

    runner = Runner(
        registry,
        services=expected_services,
    )

    await runner.run_all(create_context(tmp_path))

    assert test.received_services is expected_services

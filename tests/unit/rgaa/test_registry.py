import pytest

from accessi_code.models.audit_context import (
    AuditContext,
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


class FakeTest(RGAATest):
    test_id = "fake.1"
    criterion_id = "fake"

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> Result:
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="OK",
        )


class OtherFakeTest(RGAATest):
    test_id = "fake.2"
    criterion_id = "fake"

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> Result:
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="OK",
        )


def test_register_test():
    registry = Registry()

    test = FakeTest()

    registry.register(test)

    assert len(registry) == 1
    assert registry.get("fake.1") is test


def test_register_many_preserves_order():
    first = FakeTest()
    second = OtherFakeTest()

    registry = Registry(
        [
            first,
            second,
        ]
    )

    assert registry.get_all() == (
        first,
        second,
    )


def test_duplicate_test_id_is_rejected():
    registry = Registry(
        [
            FakeTest(),
        ]
    )

    with pytest.raises(ValueError):
        registry.register(FakeTest())


def test_register_many_is_atomic():
    registry = Registry()

    tests = [
        FakeTest(),
        FakeTest(),
    ]

    with pytest.raises(ValueError):
        registry.register_many(tests)

    assert len(registry) == 0


def test_invalid_object_is_rejected():
    registry = Registry()

    with pytest.raises(TypeError):
        registry.register(
            object()  # type: ignore[arg-type]
        )


def test_contains_test_id():
    registry = Registry(
        [
            FakeTest(),
        ]
    )

    assert "fake.1" in registry
    assert "fake.999" not in registry

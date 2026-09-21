from accessi_code.models.result import TestStatus
from accessi_code.tests.theme_08_elements_obligatoires.criterion_8_1_1 import (
    Criterion811,
)


def test_valid_html5_doctype():
    result = Criterion811().run("<!DOCTYPE html><html><body></body></html>")

    assert result.status == TestStatus.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_doctype_is_case_insensitive_and_can_have_whitespace():
    result = Criterion811().run(
        "<!doctype   HTML>\n<html><body></body></html>"
    )

    assert result.status == TestStatus.PASS


def test_missing_doctype():
    result = Criterion811().run("<html><body></body></html>")

    assert result.status == TestStatus.FAIL
    assert len(result.findings) == 1


def test_doctype_after_html():
    result = Criterion811().run("<html><body></body></html><!DOCTYPE html>")

    assert result.status == TestStatus.FAIL
    assert "avant" in result.findings[0].message


def test_invalid_doctype():
    result = Criterion811().run("<!DOCTYPE invalid><html></html>")

    assert result.status == TestStatus.FAIL
    assert "valide" in result.findings[0].message
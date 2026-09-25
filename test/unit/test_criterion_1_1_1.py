"""Tests unitaires du contrôle RGAA 1.1.1 des images HTML."""

from accessi_code.models.result import TestStatus as ResultStatus
from accessi_code.tests.theme_01_images.critere_1_1_1 import Criterion111


def test_img_with_alt():
    result = Criterion111().run('<img src="logo.png" alt="Logo">')

    assert result.status == ResultStatus.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_img_with_title():
    result = Criterion111().run('<img src="logo.png" title="Logo">')

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_img_with_aria_label():
    result = Criterion111().run('<img src="logo.png" aria-label="Logo">')

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_img_with_aria_labelledby():
    html = '<span id="logo-label">Logo de la société</span><img src="logo.png" aria-labelledby="logo-label">'

    result = Criterion111().run(html)

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_role_img_accepts_only_aria_attributes():
    html = '<div role="img" aria-label="Illustration"></div>'

    result = Criterion111().run(html)

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_role_img_does_not_accept_alt_or_title():
    html = '<div role="img" alt="Illustration" title="Illustration"></div>'

    result = Criterion111().run(html)

    assert result.status == ResultStatus.FAIL
    assert len(result.findings) == 1


def test_img_without_textual_alternative():
    result = Criterion111().run('<img src="logo.png">')

    assert result.status == ResultStatus.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_empty_alternative_attributes_are_invalid():
    html = '<img src="logo.png" alt="" aria-label="   ">'

    result = Criterion111().run(html)

    assert result.status == ResultStatus.FAIL
    assert len(result.findings) == 1


def test_no_images():
    result = Criterion111().run("<main><p>Aucune image.</p></main>")

    assert result.status == ResultStatus.NOT_APPLICABLE
    assert result.tested_elements == 0

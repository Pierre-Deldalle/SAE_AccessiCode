"""Tests unitaires du contrôle RGAA 1.1.3 des boutons image HTML."""

from accessi_code.models.result import TestStatus as ResultStatus
from accessi_code.tests.theme_01_images.critere_1_1_3 import Criterion113


def test_input_image_with_alt():
    result = Criterion113().run('<input type="image" src="send.png" alt="Envoyer">')

    assert result.status == ResultStatus.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_input_image_with_aria_label():
    html = '<input type="image" src="send.png" aria-label="Envoyer">'

    result = Criterion113().run(html)

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_input_image_with_aria_labelledby():
    html = (
        '<span id="send-label">Envoyer le formulaire</span>'
        '<input type="image" src="send.png" aria-labelledby="send-label">'
    )

    result = Criterion113().run(html)

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_input_image_with_title():
    result = Criterion113().run('<input type="image" src="send.png" title="Envoyer">')

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_input_image_without_textual_alternative():
    result = Criterion113().run('<input type="image" src="send.png">')

    assert result.status == ResultStatus.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_empty_alternative_attributes_are_invalid():
    html = '<input type="image" src="send.png" alt="" aria-label=" " title="">'

    result = Criterion113().run(html)

    assert result.status == ResultStatus.FAIL
    assert len(result.findings) == 1


def test_only_input_image_elements_are_checked():
    html = '<input type="text" aria-label="Nom"><img src="logo.png"><input type="image" src="send.png" alt="Envoyer">'

    result = Criterion113().run(html)

    assert result.status == ResultStatus.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_no_input_image():
    result = Criterion113().run('<main><input type="submit" value="Envoyer"></main>')

    assert result.status == ResultStatus.NOT_APPLICABLE
    assert result.tested_elements == 0

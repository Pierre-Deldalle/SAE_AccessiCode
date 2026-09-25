"""Tests unitaires du contrôle RGAA 1.1.2 des zones réactives HTML."""

from accessi_code.models.result import TestStatus as ResultStatus
from accessi_code.tests.theme_01_images.critere_1_1_2 import Criterion112


def test_area_with_alt():
    html = '<map name="navigation"><area href="home.html" alt="Accueil"></map>'

    result = Criterion112().run(html)

    assert result.status == ResultStatus.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_area_with_aria_label():
    html = '<map name="navigation"><area href="home.html" aria-label="Accueil"></map>'

    result = Criterion112().run(html)

    assert result.status == ResultStatus.PASS
    assert result.findings == []


def test_area_without_textual_alternative():
    html = '<map name="navigation"><area href="home.html"></map>'

    result = Criterion112().run(html)

    assert result.status == ResultStatus.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_empty_area_alternative_attributes_are_invalid():
    html = '<map name="navigation"><area href="home.html" alt="" aria-label=" "></map>'

    result = Criterion112().run(html)

    assert result.status == ResultStatus.FAIL
    assert len(result.findings) == 1


def test_multiple_areas_are_checked_individually():
    html = """
    <map name="navigation">
        <area href="home.html" alt="Accueil">
        <area href="contact.html">
        <area href="help.html" aria-label="Aide">
    </map>
    """

    result = Criterion112().run(html)

    assert result.status == ResultStatus.FAIL
    assert result.tested_elements == 3
    assert len(result.findings) == 1
    assert result.findings[0].element == "area[index=1]"


def test_no_areas():
    result = Criterion112().run("<main><p>Aucune zone réactive.</p></main>")

    assert result.status == ResultStatus.NOT_APPLICABLE
    assert result.tested_elements == 0

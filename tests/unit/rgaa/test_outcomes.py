from bs4 import BeautifulSoup

from accessi_code.analysis.image_elements import find_image_elements
from accessi_code.models.result import Finding
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.outcomes import build_result, make_outcome
from accessi_code.rgaa.tests.theme_01_images._common import outcome


class _FakeTest:
    test_id = "X.Y.Z"
    criterion_id = "X.Y"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_finding_location_fields_are_optional():
    finding = Finding(element="a[index=0]", message="msg")

    assert finding.line is None
    assert finding.snippet is None


def test_make_outcome_with_node_fills_line_and_snippet():
    node = _soup('<main>\n\n<a href="#">Lire</a></main>').find("a")

    result = make_outcome(Status.FAIL, "a[index=0]", "Intitulé absent.", "Ajouter un intitulé.", node=node, kind="x")

    assert result.finding is not None
    assert result.finding.line == 3
    assert result.finding.snippet == '<a href="#">Lire</a>'
    # node ne doit pas se retrouver dans les preuves.
    assert result.finding.evidence == {"kind": "x"}


def test_make_outcome_without_node_leaves_location_empty():
    result = make_outcome(Status.NEEDS_REVIEW, "a[index=0]", "À vérifier.")

    assert result.finding is not None
    assert result.finding.line is None
    assert result.finding.snippet is None


def test_make_outcome_pass_without_message_has_no_finding_even_with_node():
    node = _soup("<a href='/'>Accueil</a>").find("a")

    assert make_outcome(Status.PASS, "a[index=0]", node=node).finding is None


def test_build_result_keeps_finding_location():
    node = _soup("<p>x</p>\n<table></table>").find("table")

    result = build_result(
        _FakeTest(),
        [make_outcome(Status.FAIL, "table[index=0]", "Problème.", node=node)],
        empty_summary="Aucun tableau.",
    )

    assert result.findings[0].line == 2
    assert result.findings[0].snippet == "<table></table>"


def test_theme_01_outcome_uses_image_tag_by_default():
    soup = _soup('<p>texte</p>\n<img src="logo.png">')
    element = find_image_elements(soup)[0]

    result = outcome(Status.FAIL, element, "Alternative absente.")

    assert result.finding is not None
    assert result.finding.line == 2
    assert result.finding.snippet == '<img src="logo.png">'


def test_theme_01_outcome_accepts_explicit_node():
    soup = _soup('<a href="/">\n<img src="logo.png"></a>')
    element = find_image_elements(soup)[0]

    result = outcome(Status.FAIL, element, "Lien image sans intitulé.", node=soup.find("a"))

    assert result.finding is not None
    assert result.finding.line == 1
    assert result.finding.snippet.startswith('<a href="/">')

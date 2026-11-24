"""Localisation des observations construites par make_outcome."""

from bs4 import BeautifulSoup

from accessi_code.models.result import Finding
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.outcomes import make_outcome


def test_make_outcome_locates_node_and_preserves_evidence():
    soup = BeautifulSoup('<p>Texte</p>\n<a href="#">Aide</a>', "html.parser")

    outcome = make_outcome(Status.FAIL, "a[index=0]", "Anomalie.", "Corriger le lien.", node=soup.a, href="#")

    assert outcome.status is Status.FAIL
    assert outcome.finding == Finding(
        "a[index=0]", "Anomalie.", "Corriger le lien.", {"href": "#"}, 2, '<a href="#">Aide</a>'
    )


def test_make_outcome_without_location_keeps_optional_fields_empty():
    outcome = make_outcome(Status.FAIL, "main", "La balise main est absente.")

    assert outcome.finding.line is None
    assert outcome.finding.snippet is None


def test_make_outcome_with_node_keeps_pass_without_message():
    soup = BeautifulSoup('<img src="x.png" alt="Description">', "html.parser")

    assert make_outcome(Status.PASS, "img[index=0]", node=soup.img).finding is None

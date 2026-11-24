"""Explications par critère : couverture du registre et complétude des entrées."""

import pytest

from accessi_code.rgaa.criteria_info import CRITERIA, RGAA_METHOD_URL, criterion_info
from accessi_code.rgaa.default_registry import build_default_registry

# Thèmes dont les explications sont rédigées ; à compléter au fil des thèmes.
DOCUMENTED_THEMES = ("2", "4", "5", "9", "12")

REGISTRY_CRITERIA = sorted(
    {test.criterion_id for test in build_default_registry() if test.criterion_id.split(".")[0] in DOCUMENTED_THEMES}
)


def test_documented_themes_have_criteria_in_registry():
    assert REGISTRY_CRITERIA == sorted(
        [
            "2.1",
            "2.2",
            *(f"4.{number}" for number in range(1, 14)),
            *(f"5.{number}" for number in range(1, 9)),
            *(f"9.{number}" for number in range(1, 5)),
            *(f"12.{number}" for number in range(1, 12)),
        ]
    )


@pytest.mark.parametrize("criterion_id", REGISTRY_CRITERIA)
def test_each_registry_criterion_has_an_entry(criterion_id):
    assert criterion_info(criterion_id) is not None


@pytest.mark.parametrize("info", CRITERIA.values(), ids=list(CRITERIA))
def test_each_entry_is_complete(info):
    assert info.title.strip().endswith("?")
    assert len(info.impact.strip()) > 40
    assert info.url == f"{RGAA_METHOD_URL}#{info.criterion_id}"


def test_unknown_criterion_gives_none():
    assert criterion_info("99.9") is None


def test_criterion_info_content():
    info = criterion_info("2.1")
    assert info is not None
    assert info.title == "Chaque cadre a-t-il un titre de cadre ?"
    assert info.url == "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#2.1"


def test_theme_9_criterion_info_content():
    info = criterion_info("9.3")
    assert info is not None
    assert info.title == "Dans chaque page web, chaque liste est-elle correctement structurée ?"
    assert "lecteur d'écran" in info.impact
    assert info.url == "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#9.3"


def test_theme_12_criterion_info_content():
    info = criterion_info("12.7")
    assert info is not None
    assert info.title == (
        "Dans chaque page web, un lien d’évitement ou d’accès rapide à la zone de contenu principal est-il présent "
        "(hors cas particuliers) ?"
    )
    assert "clavier" in info.impact
    assert info.url == "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#12.7"

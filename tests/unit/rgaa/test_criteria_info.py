"""Explications par critère : couverture du registre et complétude des entrées."""

import pytest

from accessi_code.rgaa.criteria_info import CRITERIA, RGAA_METHOD_URL, criterion_info
from accessi_code.rgaa.default_registry import build_default_registry

# Thèmes dont les explications sont rédigées ; à compléter au fil des thèmes.
DOCUMENTED_THEMES = ("2", "7", "11")

REGISTRY_CRITERIA = sorted(
    {test.criterion_id for test in build_default_registry() if test.criterion_id.split(".")[0] in DOCUMENTED_THEMES}
)


def test_documented_themes_have_criteria_in_registry():
    forms = [f"11.{number}" for number in range(1, 14)]
    assert REGISTRY_CRITERIA == sorted(["2.1", "2.2", "7.1", "7.2", "7.3", "7.4", "7.5", *forms])


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


def test_titles_are_the_official_wording():
    # Intitulés recopiés depuis le référentiel officiel (DISIC/RGAA, v4.1/JSON/criteres.json).
    assert criterion_info("7.3").title == (
        "Chaque script est-il contrôlable par le clavier et par tout dispositif de pointage (hors cas particuliers) ?"
    )
    assert criterion_info("7.4").title == (
        "Pour chaque script qui initie un changement de contexte, "
        "l'utilisateur est-il averti ou en a-t-il le contrôle ?"
    )

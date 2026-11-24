import pytest

from accessi_code.rgaa.criteria_info import CRITERIA_INFO, CriterionInfo, criterion_info
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.themes import theme_number

# Thématiques dont la table est renseignée. Ajouter ici chaque thématique complétée :
# le test vérifie alors que tous ses critères présents dans le registre ont une entrée.
COVERED_THEMES = {4}


def _registry_criteria() -> list[str]:
    return list(dict.fromkeys(test.criterion_id for test in build_default_registry()))


def _covered_registry_criteria() -> list[str]:
    return [criterion for criterion in _registry_criteria() if theme_number(criterion) in COVERED_THEMES]


def test_covered_themes_have_registry_criteria():
    assert _covered_registry_criteria()


@pytest.mark.parametrize("criterion_id", _covered_registry_criteria())
def test_each_registry_criterion_has_an_entry(criterion_id):
    info = criterion_info(criterion_id)

    assert info is not None, f"Critère {criterion_id} absent de criteria_info.py"
    assert info.criterion_id == criterion_id


@pytest.mark.parametrize("info", CRITERIA_INFO.values(), ids=lambda info: info.criterion_id)
def test_each_entry_has_title_impact_and_url(info: CriterionInfo):
    assert info.title.strip()
    # Les intitulés officiels du RGAA sont des questions.
    assert info.title.endswith("?")
    assert info.impact.strip()
    assert info.url == f"https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#{info.criterion_id}"


def test_entries_only_describe_criteria_of_the_registry():
    assert set(CRITERIA_INFO) <= set(_registry_criteria())


def test_criterion_info_unknown_criterion_returns_none():
    assert criterion_info("99.1") is None


def test_criterion_info_ignores_surrounding_spaces():
    info = criterion_info(" 4.10 ")

    assert info is not None
    assert info.criterion_id == "4.10"


def test_explicit_url_is_kept():
    info = CriterionInfo("4.1", "Titre ?", "Impact.", url="https://exemple.test/4.1")

    assert info.url == "https://exemple.test/4.1"

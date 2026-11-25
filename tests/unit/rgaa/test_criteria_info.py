"""Explications par critère : couverture du registre et complétude des entrées."""

import pytest

from accessi_code.rgaa.criteria_info import CRITERIA, RGAA_METHOD_URL, criterion_info
from accessi_code.rgaa.default_registry import build_default_registry

REGISTRY_CRITERIA = sorted({test.criterion_id for test in build_default_registry()})


def test_registry_covers_the_13_themes():
    assert {criterion.split(".")[0] for criterion in REGISTRY_CRITERIA} == {str(theme) for theme in range(1, 14)}


def test_every_entry_is_a_registry_criterion():
    assert set(CRITERIA) <= set(REGISTRY_CRITERIA)


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


def test_theme_13_criterion_info_content():
    info = criterion_info("13.7")
    assert info is not None
    assert info.title == (
        "Dans chaque page web, les changements brusques de luminosité ou les effets de flash sont-ils "
        "correctement utilisés ?"
    )
    assert "épileptique" in info.impact
    assert info.url == "https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#13.7"

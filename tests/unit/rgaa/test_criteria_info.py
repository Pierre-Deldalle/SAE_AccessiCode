"""Couverture des critères documentés et validité de leurs informations."""

import pytest

from accessi_code.rgaa.criteria_info import _CRITERIA_INFO, criterion_info
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.themes import filter_registry_by_themes


@pytest.mark.parametrize("theme", [1, 6, 8], ids=["images", "liens", "elements-obligatoires"])
def test_criteria_info_covers_registered_criteria(theme):
    registry = filter_registry_by_themes(build_default_registry(), {theme})
    registered_ids = {test.criterion_id for test in registry}

    assert registered_ids
    assert registered_ids <= _CRITERIA_INFO.keys()


def test_criteria_info_entries_have_required_fields():
    for criterion_id in _CRITERIA_INFO:
        info = criterion_info(criterion_id)
        assert info is not None
        assert info.criterion_id == criterion_id
        assert info.title.strip()
        assert info.impact.strip()
        assert info.url == f"https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#{criterion_id}"


def test_criterion_info_returns_none_for_unknown_id():
    assert criterion_info("inconnu") is None

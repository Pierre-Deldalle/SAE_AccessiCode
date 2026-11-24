import json

import pytest

from evals.datasets.loader import load_eval_cases


def test_loader_loads_valid_dataset(tmp_path):
    dataset_path = tmp_path / "train.json"

    dataset_path.write_text(
        json.dumps(
            [
                {
                    "id": "title_001",
                    "input": {
                        "title": "Contact",
                        "heading": "Contactez-nous",
                        "content": "Retrouvez nos coordonnées.",
                    },
                    "expected": {
                        "relevant": True,
                    },
                },
                {
                    "id": "title_002",
                    "input": {
                        "title": "Recette de crêpes",
                        "heading": "Contactez-nous",
                        "content": "Retrouvez nos coordonnées.",
                    },
                    "expected": {
                        "relevant": False,
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    cases = load_eval_cases(dataset_path)

    assert len(cases) == 2

    assert cases[0].id == "title_001"
    assert cases[0].expected["relevant"] is True

    assert cases[1].id == "title_002"
    assert cases[1].expected["relevant"] is False


def test_loader_rejects_duplicate_ids(tmp_path):
    dataset_path = tmp_path / "train.json"

    dataset_path.write_text(
        json.dumps(
            [
                {
                    "id": "title_001",
                    "input": {},
                    "expected": {},
                },
                {
                    "id": "title_001",
                    "input": {},
                    "expected": {},
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Identifiant de cas dupliqué",
    ):
        load_eval_cases(dataset_path)


def test_loader_rejects_non_list_dataset(tmp_path):
    dataset_path = tmp_path / "train.json"

    dataset_path.write_text(
        json.dumps(
            {
                "id": "title_001",
                "input": {},
                "expected": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="liste de cas",
    ):
        load_eval_cases(dataset_path)


def test_loader_rejects_non_object_case(tmp_path):
    dataset_path = tmp_path / "train.json"

    dataset_path.write_text(
        json.dumps(
            [
                "invalid-case",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="objet JSON",
    ):
        load_eval_cases(dataset_path)


def test_loader_raises_if_dataset_does_not_exist(tmp_path):
    dataset_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_eval_cases(dataset_path)

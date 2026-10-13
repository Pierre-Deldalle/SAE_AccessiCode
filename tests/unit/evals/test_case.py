import pytest

from evals.models.case import EvalCase


def test_from_dict_creates_eval_case():
    case = EvalCase.from_dict(
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
            "metadata": {
                "description": "Cas simple.",
            },
        }
    )

    assert case.id == "title_001"

    assert case.input_data == {
        "title": "Contact",
        "heading": "Contactez-nous",
        "content": "Retrouvez nos coordonnées.",
    }

    assert case.expected == {
        "relevant": True,
    }

    assert case.metadata == {
        "description": "Cas simple.",
    }


def test_from_dict_uses_empty_metadata_by_default():
    case = EvalCase.from_dict(
        {
            "id": "title_001",
            "input": {},
            "expected": {
                "relevant": True,
            },
        }
    )

    assert case.metadata == {}


@pytest.mark.parametrize(
    "data",
    [
        {
            "input": {},
            "expected": {},
        },
        {
            "id": "",
            "input": {},
            "expected": {},
        },
        {
            "id": 123,
            "input": {},
            "expected": {},
        },
    ],
)
def test_from_dict_rejects_invalid_id(data):
    with pytest.raises(ValueError):
        EvalCase.from_dict(data)


def test_from_dict_rejects_non_object_input():
    with pytest.raises(ValueError):
        EvalCase.from_dict(
            {
                "id": "title_001",
                "input": "not-an-object",
                "expected": {},
            }
        )


def test_from_dict_rejects_non_object_expected():
    with pytest.raises(ValueError):
        EvalCase.from_dict(
            {
                "id": "title_001",
                "input": {},
                "expected": True,
            }
        )


def test_from_dict_rejects_non_object_metadata():
    with pytest.raises(ValueError):
        EvalCase.from_dict(
            {
                "id": "title_001",
                "input": {},
                "expected": {},
                "metadata": "invalid",
            }
        )

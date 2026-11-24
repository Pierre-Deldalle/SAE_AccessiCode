from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class EvalCase:
    """
    Cas individuel utilisé pour évaluer une fonctionnalité IA.

    input_data contient les données transmises à l'analyseur.
    expected contient les résultats attendus définis humainement.
    """

    id: str
    input_data: dict[str, Any]
    expected: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> EvalCase:
        """
        Construit un EvalCase à partir d'un objet chargé depuis un dataset JSON.
        """
        case_id = data.get("id")
        input_data = data.get("input")
        expected = data.get("expected")
        metadata = data.get("metadata", {})

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Un cas d'évaluation doit posséder un id non vide.")

        if not isinstance(input_data, dict):
            raise ValueError(f"Le cas {case_id!r} doit posséder un champ 'input' de type objet.")

        if not isinstance(expected, dict):
            raise ValueError(f"Le cas {case_id!r} doit posséder un champ 'expected' de type objet.")

        if not isinstance(metadata, dict):
            raise ValueError(f"Le champ 'metadata' du cas {case_id!r} doit être un objet.")

        return cls(
            id=case_id,
            input_data=dict(input_data),
            expected=dict(expected),
            metadata=dict(metadata),
        )

from __future__ import annotations

import json
from pathlib import Path

from evals.models.case import EvalCase


def load_eval_cases(
    dataset_path: Path,
) -> list[EvalCase]:
    """
    Charge un dataset JSON et le transforme en liste d'EvalCase.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset introuvable : {dataset_path}")

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Un dataset d'évaluation doit contenir une liste de cas.")

    cases: list[EvalCase] = []
    seen_ids: set[str] = set()

    for raw_case in data:
        if not isinstance(raw_case, dict):
            raise ValueError("Chaque entrée du dataset doit être un objet JSON.")

        case = EvalCase.from_dict(raw_case)

        if case.id in seen_ids:
            raise ValueError(f"Identifiant de cas dupliqué : {case.id}")

        seen_ids.add(case.id)
        cases.append(case)

    return cases
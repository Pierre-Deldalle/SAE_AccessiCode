from __future__ import annotations

import json
from typing import Any

from json_repair import repair_json


def parse_ai_json(
    value: str,
) -> dict[str, Any]:
    """
    Transforme une réponse textuelle d'un modèle IA en objet JSON.

    La fonction :
    - retire les éventuelles balises Markdown ;
    - isole le premier objet JSON ;
    - tente une réparation légère si le JSON est invalide.
    """
    text = value.strip()

    if not text:
        raise ValueError("La réponse IA est vide.")

    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) >= 2:
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        text = text[start : end + 1]

    if not text:
        raise ValueError("La réponse IA ne contient aucun objet JSON.")

    try:
        parsed = json.loads(text)

    except json.JSONDecodeError:
        repaired = repair_json(text)

        try:
            parsed = json.loads(repaired)

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("La réponse IA ne contient pas de JSON exploitable.") from error

    if not isinstance(parsed, dict):
        raise ValueError("La réponse IA n'est pas un objet JSON.")

    return parsed

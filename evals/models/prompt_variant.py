from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PromptVariant:
    """
    Variante de prompt utilisée uniquement par le système d'évaluation.
    """

    name: str
    template: str
    path: Path | None = None

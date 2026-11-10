from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuditServices:
    """
    Services optionnels injectés dans les tests RGAA.

    Le moteur reste indépendant de leurs implémentations concrètes.
    """

    image_analyzer: Any | None = None
    page_analyzer: Any | None = None
    html_validator: Any | None = None
    language_change_analyzer: Any | None = None
    language_validity_analyzer: Any | None = None
    semantic_presentation_analyzer: Any | None = None
    text_direction_analyzer: Any | None = None
    text_direction_validity_analyzer: Any | None = None

"""Structures de réponses attendues des modèles d'analyse d'images."""

from dataclasses import dataclass, field
from typing import Literal

# Ce niveau indique la confiance déclarée par le modèle ; il ne constitue
# pas une mesure statistique de conformité au RGAA.
AIConfidence = Literal["low", "medium", "high"]


@dataclass
class VisualObservation:
    """Observations produites par le VLM, sans verdict de conformité."""

    summary: str
    # Informations visibles que la description devrait idéalement couvrir.
    important_information: list[str] = field(default_factory=list)
    # Éléments flous, illisibles ou impossibles à confirmer dans l'image.
    uncertainties: list[str] = field(default_factory=list)


@dataclass
class DescriptionAnalysis:
    """Comparaison LLM entre une description, l'image et son contexte HTML."""

    # None est volontaire : le modèle peut manquer d'éléments pour conclure.
    relevant: bool | None
    explanation: str
    # Preuves permettant d'expliquer un verdict négatif ou incertain.
    missing_information: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    # Indication qualitative à afficher avec prudence dans le rapport.
    confidence: AIConfidence = "low"
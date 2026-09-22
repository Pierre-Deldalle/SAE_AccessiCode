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


@dataclass
class LanguageAnalysis:
    """Résultat de la comparaison IA entre lang et le contenu principal."""

    # None indique que le modèle ne dispose pas de suffisamment d'éléments.
    relevant: bool | None
    # Langue détectée par le modèle, par exemple ``fr`` ou ``en``.
    detected_language: str
    explanation: str
    # Points qui empêchent éventuellement une conclusion certaine.
    uncertainties: list[str] = field(default_factory=list)
    # Confiance déclarée par le modèle, sans valeur statistique.
    confidence: AIConfidence = "low"


@dataclass
class TitleAnalysis:
    """Résultat de l'évaluation IA de la pertinence du titre de page."""

    # None permet de distinguer l'incertitude d'un titre réellement incorrect.
    relevant: bool | None
    explanation: str
    # Contradictions et incertitudes sont conservées comme éléments de preuve.
    contradictions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    confidence: AIConfidence = "low"
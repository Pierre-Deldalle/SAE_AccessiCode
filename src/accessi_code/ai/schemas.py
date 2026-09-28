from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AIConfidence = Literal[
    "low",
    "medium",
    "high",
]


@dataclass
class VisualObservation:
    """
    Observations produites par le VLM.

    Ce modèle ne représente pas un verdict RGAA.
    """

    summary: str

    important_information: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)


@dataclass
class DescriptionAnalysis:
    """
    Comparaison entre une description textuelle et le contenu visuel.
    """

    relevant: bool | None
    explanation: str

    is_detailed_description: bool | None = None

    missing_information: list[str] = field(default_factory=list)

    contradictions: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"


@dataclass
class LanguageAnalysis:
    """
    Résultat de l'analyse sémantique de la langue principale.
    """

    relevant: bool | None
    detected_language: str
    explanation: str

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"


@dataclass
class TitleAnalysis:
    """
    Résultat de l'analyse sémantique de la pertinence du titre.
    """

    relevant: bool | None
    explanation: str

    contradictions: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"


@dataclass
class ImageRoleAnalysis:
    """
    Résultat de l'analyse du rôle informationnel d'une image.

    None indique que les informations disponibles ne permettent
    pas de conclure avec suffisamment de confiance.
    """

    information_bearing: bool | None
    explanation: str

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"

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
    suggestion: str | None = None


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


# ----------------------------------------------------------------------
# Pertinence générique d'un texte (titres, intitulés, étiquettes…)
# ----------------------------------------------------------------------


@dataclass
class RelevanceItem:
    """
    Élément textuel soumis à un jugement de pertinence.

    text :
        Texte à juger (titre de cadre, intitulé de lien, étiquette…).
    element_html :
        Extrait HTML de l'élément concerné.
    context :
        Texte environnant utile au jugement.
    details :
        Informations complémentaires propres au type d'élément
        (href, type de champ, page cible…), sérialisables en JSON.
    """

    text: str
    element_html: str = ""
    context: str = ""
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class RelevanceAnalysis:
    """
    Jugement de pertinence d'un texte.

    Ce modèle ne représente pas un verdict RGAA : la décision
    appartient au test qui l'utilise.
    """

    relevant: bool | None
    explanation: str

    problems: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"
    suggestion: str | None = None


# ----------------------------------------------------------------------
# Images
# ----------------------------------------------------------------------


@dataclass
class ImageProfile:
    """
    Profil d'une image, calculé une seule fois et réutilisé par
    plusieurs critères du thème 1.

    Chaque champ vaut None lorsque l'IA ne peut pas conclure.
    """

    information_bearing: bool | None
    is_captcha: bool | None
    contains_text: bool | None
    needs_detailed_description: bool | None

    explanation: str

    # Le texte de l'image pourrait être rendu en texte stylé (CSS) sans perte (RGAA 1.8).
    text_replaceable: bool | None = None

    text_content: str = ""

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"


@dataclass
class AlternativeAnalysis:
    """
    Comparaison entre l'alternative textuelle d'une image et son contenu.
    """

    relevant: bool | None
    concise: bool | None
    explanation: str

    missing_information: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"
    suggestion: str | None = None


# ----------------------------------------------------------------------
# Information sensorielle (couleur, forme, taille, position)
# ----------------------------------------------------------------------


SensoryKind = Literal[
    "color",
    "shape_size_position",
]


@dataclass
class SensoryCandidate:
    """Passage de texte ou image susceptible de transmettre une information sensorielle."""

    text: str
    element_html: str = ""
    context: str = ""


@dataclass
class SensoryAnalysis:
    """
    Analyse d'une information transmise par une caractéristique sensorielle.

    conveys_information :
        La caractéristique sert-elle à transmettre une information ?
    relies_only_on_sensory :
        L'information repose-t-elle uniquement sur cette caractéristique ?
    alternative_relevant :
        Lorsqu'un autre moyen existe, est-il pertinent ?
    """

    conveys_information: bool | None
    relies_only_on_sensory: bool | None
    alternative_relevant: bool | None
    explanation: str

    characteristics: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"


# ----------------------------------------------------------------------
# Structuration (titres, listes, citations non balisés)
# ----------------------------------------------------------------------


StructureKind = Literal[
    "heading",
    "list",
    "quote",
    "caption",
    "status_success",
    "status_error",
    "status_progress",
]


@dataclass
class StructureCandidate:
    """Passage de texte susceptible de devoir être structuré."""

    text: str
    element_html: str = ""
    context: str = ""


@dataclass
class StructureCandidateAnalysis:
    """
    should_be_marked :
        True si le passage est visuellement un titre / une liste /
        une citation et devrait être balisé comme tel.
    """

    should_be_marked: bool | None
    explanation: str

    uncertainties: list[str] = field(default_factory=list)

    confidence: AIConfidence = "low"

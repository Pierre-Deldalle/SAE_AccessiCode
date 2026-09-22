"""Modèles décrivant les fichiers associés à un audit."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuditFile:
    """
    Décrit un fichier fourni pour un audit et sa copie de travail.

    Attributes:
        original_name: Nom du fichier au moment de son import.
        path: Chemin vers la copie conservée dans le workspace de l'audit.
        extension: Extension normalisée en minuscules, préfixée par un point.
        mime_type: Type MIME déduit du nom du fichier, s'il est connu.
    """

    original_name: str
    path: Path
    extension: str
    mime_type: str | None = None

    @property
    def exists(self) -> bool:
        """Indique si la copie du fichier existe encore sur le disque."""

        return self.path.exists()
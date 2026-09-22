from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuditFile:
    """
    Représente un fichier fourni pour un audit.
    """

    original_name: str
    path: Path
    extension: str
    mime_type: str | None = None

    @property
    def exists(self) -> bool:
        return self.path.exists()
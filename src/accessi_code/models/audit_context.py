from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from accessi_code.models.audit_file import AuditFile
from accessi_code.models.capabilities import Capability


@dataclass
class AuditContext:
    """
    Regroupe toutes les informations disponibles pour réaliser
    un audit d'accessibilité.

    L'objet est construit avant l'exécution des tests RGAA.
    """

    audit_id: str
    workspace_path: Path

    # Fichiers fournis pour l'audit
    files: list[AuditFile] = field(default_factory=list)

    # Document HTML principal
    html_path: Path | None = None
    html_source: str | None = None

    # DOM parsé
    dom: Any | None = None

    # Informations extraites du document
    doctype: str | None = None

    # Ressources visuelles disponibles
    image_files: list[Path] = field(default_factory=list)
    screenshots: list[Path] = field(default_factory=list)

    def get_capabilities(self) -> set[Capability]:
        """
        Retourne les capacités disponibles à partir
        des informations présentes dans le contexte.
        """

        capabilities: set[Capability] = set()

        if self.files:
            capabilities.add(Capability.SOURCE_FILES)

        if self.html_source is not None:
            capabilities.add(Capability.HTML_SOURCE)

        if self.dom is not None:
            capabilities.add(Capability.DOM)

        if self.image_files:
            capabilities.add(Capability.IMAGES)

        if self.screenshots:
            capabilities.add(Capability.SCREENSHOT)

        return capabilities

    def has_capability(self, capability: Capability) -> bool:
        """
        Vérifie si une capacité est disponible.
        """

        return capability in self.get_capabilities()

    def has_capabilities(
        self,
        capabilities: set[Capability],
    ) -> bool:
        """
        Vérifie si toutes les capacités demandées sont disponibles.
        """

        available = self.get_capabilities()

        return capabilities.issubset(available)
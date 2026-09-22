"""Contexte de travail partagé par les étapes d'un audit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from accessi_code.models.audit_file import AuditFile
from accessi_code.models.capabilities import Capability


@dataclass
class AuditContext:
    """
    Regroupe les fichiers et les ressources extraites pour un audit.

    Le contexte est construit avant l'exécution des tests RGAA. Les champs
    optionnels sont remplis progressivement par les extracteurs ; les
    capacités retournées par :meth:`get_capabilities` reflètent cet état.

    Attributes:
        audit_id: Identifiant unique de l'audit.
        workspace_path: Répertoire de travail contenant les copies importées.
        files: Fichiers importés et leurs métadonnées.
        html_path: Chemin du premier document HTML détecté, s'il existe.
        html_source: Contenu source du document HTML principal.
        dom: Arbre DOM BeautifulSoup du document HTML principal.
        doctype: Déclaration DOCTYPE extraite du document HTML.
        image_files: Chemins des fichiers reconnus comme images.
        screenshots: Chemins des captures disponibles pour l'audit.
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
        Calcule les capacités disponibles dans l'état courant.

        Returns:
            Un ensemble de capacités. Une liste vide ne donne aucune capacité,
            tandis que les champs HTML et DOM sont évalués indépendamment.
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
        Vérifie la présence d'une capacité particulière.

        Args:
            capability: Capacité à rechercher.

        Returns:
            ``True`` si la capacité est disponible, sinon ``False``.
        """

        return capability in self.get_capabilities()

    def has_capabilities(
        self,
        capabilities: set[Capability],
    ) -> bool:
        """
        Vérifie que toutes les capacités demandées sont disponibles.

        Args:
            capabilities: Ensemble des capacités requises.

        Returns:
            ``True`` si l'ensemble demandé est inclus dans les capacités
            courantes. Un ensemble vide est donc toujours satisfait.
        """

        available = self.get_capabilities()

        return capabilities.issubset(available)
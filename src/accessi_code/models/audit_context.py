"""Contexte de travail partagé par les étapes d'un audit."""

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

from accessi_code.models.audit_file import AuditFile
from accessi_code.models.capabilities import Capability
from accessi_code.models.color_style import (
    NonTextContrastSample,
    TextContrastSample,
)


@dataclass
class UnresolvedTextContrast:
    """
    Fragment textuel dont le contraste nécessite une vérification.

    Une observation non résolue ne constitue pas
    un défaut RGAA confirmé.
    """

    element: str
    text: str
    reason: str

    font_size_px: float | None = None
    font_weight: int | None = None

    @property
    def has_valid_typography(self) -> bool:
        """Indique si la taille et la graisse sont exploitables."""

        if self.font_size_px is None:
            return False

        if self.font_weight is None:
            return False

        if not isfinite(self.font_size_px):
            return False

        if self.font_size_px <= 0:
            return False

        if not isinstance(self.font_weight, int):
            return False

        if isinstance(self.font_weight, bool):
            return False

        if not 1 <= self.font_weight <= 1000:
            return False

        return True


@dataclass
class UnresolvedNonTextContrast:
    """
    Observation non textuelle nécessitant une vérification humaine.

    Les couleurs sont des valeurs CSS candidates.
    Leur comparaison ne suffit pas à établir un verdict RGAA 3.3.

    element:
        Sélecteur ou description de l'élément.

    kind:
        Catégorie : component, graphic ou mechanism.

    comparison:
        Type de comparaison : background ou adjacent.

    foreground_color:
        Couleur candidate de la bordure ou du graphique.

    background_color:
        Couleur candidate de la surface de référence.

    state:
        État observé : default, focus, hover, etc.

    reason:
        Motif de l'incertitude nécessitant un contrôle humain.
    """

    element: str
    kind: str
    comparison: str
    foreground_color: str | None
    background_color: str | None
    state: str | None
    reason: str


@dataclass
class AuditContext:
    """
    Regroupe les fichiers et ressources extraites pour un audit.

    Les observations non résolues servent à signaler les contrôles
    nécessitant une intervention humaine.

    Leur présence ne démontre ni conformité ni non-conformité.
    """

    audit_id: str
    workspace_path: Path

    # Fichiers fournis pour l'audit.
    files: list[AuditFile] = field(default_factory=list)

    # Document HTML principal.
    html_path: Path | None = None
    html_source: str | None = None

    # DOM parsé.
    dom: Any | None = None

    # Informations extraites du document.
    doctype: str | None = None

    # Ressources visuelles disponibles.
    image_files: list[Path] = field(default_factory=list)
    screenshots: list[Path] = field(default_factory=list)

    # Feuilles de style CSS sources.
    css_files: list[Path] = field(default_factory=list)
    css_sources: dict[Path, str] = field(default_factory=dict)

    # Échantillons de contraste.
    text_contrast_samples: list[TextContrastSample] = field(default_factory=list)
    non_text_contrast_samples: list[NonTextContrastSample] = field(default_factory=list)

    # Couverture des contrastes textuels.
    text_contrast_extraction_attempted: bool = False
    text_contrast_coverage_complete: bool = False
    text_contrast_unresolved_count: int = 0

    # Fragments textuels dont le contraste reste indéterminé.
    unresolved_text_contrasts: list[UnresolvedTextContrast] = field(default_factory=list)

    # Observations non textuelles à vérifier humainement.
    unresolved_non_text_contrasts: list[UnresolvedNonTextContrast] = field(default_factory=list)

    @property
    def text_contrast_is_partial(self) -> bool:
        """
        Une extraction automatique a été tentée,
        sans preuve de couverture exhaustive.
        """
        return self.text_contrast_extraction_attempted and not self.text_contrast_coverage_complete

    def get_capabilities(self) -> set[Capability]:
        """
        Calcule les capacités techniques disponibles.

        TEXT_CONTRAST :
            Échantillons textuels exploitables ou observations
            textuelles non résolues disponibles.

        NON_TEXT_CONTRAST :
            Échantillons non textuels exploitables disponibles.
            Les seules observations incertaines ne suffisent pas
            encore à activer cette capacité.

        COMPUTED_STYLES :
            Au moins une catégorie d'échantillons est disponible.

        Aucune capacité ne garantit une couverture exhaustive.
        """

        capabilities: set[Capability] = set()

        if self.files:
            capabilities.add(Capability.SOURCE_FILES)

        if self.html_source is not None:
            capabilities.add(Capability.HTML_SOURCE)

        if self.dom is not None:
            capabilities.add(Capability.DOM)

        if self.css_sources:
            capabilities.add(Capability.CSS_SOURCE)

        if self.image_files:
            capabilities.add(Capability.IMAGES)

        if self.screenshots:
            capabilities.add(Capability.SCREENSHOT)

        if self.text_contrast_samples or self.unresolved_text_contrasts:
            capabilities.add(Capability.TEXT_CONTRAST)

        if self.non_text_contrast_samples or self.unresolved_non_text_contrasts:
            capabilities.add(Capability.NON_TEXT_CONTRAST)

        if self.text_contrast_samples or self.non_text_contrast_samples:
            capabilities.add(Capability.COMPUTED_STYLES)

        return capabilities

    def has_capability(self, capability: Capability) -> bool:
        """Vérifie si une capacité est disponible."""
        return capability in self.get_capabilities()

    def has_capabilities(
        self,
        capabilities: set[Capability],
    ) -> bool:
        """Vérifie la présence de toutes les capacités demandées."""
        return capabilities.issubset(self.get_capabilities())

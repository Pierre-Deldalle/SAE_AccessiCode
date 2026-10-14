"""Enrichissement du contexte d'audit avec les styles du navigateur."""

from dataclasses import dataclass, field
from math import isfinite

from accessi_code.input.contrast_sample_builder import ContrastSampleBuilder
from accessi_code.input.extractors.computed_styles import (
    NonTextStyleObservation,
    TextStyleObservation,
    extract_non_text_styles,
    extract_text_styles,
)
from accessi_code.models.audit_context import (
    AuditContext,
    UnresolvedNonTextContrast,
    UnresolvedTextContrast,
)
from accessi_code.models.color_style import TextContrastSample


@dataclass
class ContextEnrichmentReport:
    """Rapport technique de l'extraction des styles calculés."""

    # Observations des contrastes textuels.
    observations: list[TextStyleObservation] = field(default_factory=list)
    usable_observations: list[TextStyleObservation] = field(default_factory=list)
    review_observations: list[TextStyleObservation] = field(default_factory=list)

    text_contrast_samples: list[TextContrastSample] = field(default_factory=list)
    rejected_observations: list[TextStyleObservation] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)

    # Observations des contrastes non textuels.
    non_text_observations: list[NonTextStyleObservation] = field(default_factory=list)

    # Erreurs indépendantes des deux extractions.
    error: str | None = None
    non_text_error: str | None = None

    @property
    def total(self) -> int:
        """Nombre total de fragments textuels observés."""
        return len(self.observations)

    @property
    def usable_count(self) -> int:
        """Nombre d'observations textuelles candidates à l'analyse."""
        return len(self.usable_observations)

    @property
    def review_count(self) -> int:
        """Nombre d'observations textuelles nécessitant une vérification."""
        return len(self.review_observations)

    @property
    def sample_count(self) -> int:
        """Nombre d'échantillons de contraste textuel préparés."""
        return len(self.text_contrast_samples)

    @property
    def rejected_count(self) -> int:
        """Nombre d'observations textuelles rejetées."""
        return len(self.rejected_observations)

    @property
    def non_text_observation_count(self) -> int:
        """Nombre d'observations non textuelles extraites."""
        return len(self.non_text_observations)


class ContextEnricher:
    """
    Extrait les styles calculés et enrichit AuditContext.

    RGAA 3.2 :
        Les échantillons textuels exploitables sont transmis
        au contexte, et les observations incertaines sont
        conservées pour vérification humaine.

    RGAA 3.3 :
        Les observations non textuelles sont conservées
        séparément. Elles ne sont pas automatiquement
        converties en NonTextContrastSample.

    Les deux extractions sont indépendantes :
        un échec non textuel n'efface pas les mesures
        textuelles déjà obtenues.

    Aucune couverture exhaustive n'est présumée.
    """

    def __init__(
        self,
        contrast_sample_builder: ContrastSampleBuilder | None = None,
    ) -> None:
        self.contrast_sample_builder = (
            contrast_sample_builder if contrast_sample_builder is not None else ContrastSampleBuilder()
        )

    async def enrich(
        self,
        context: AuditContext,
    ) -> ContextEnrichmentReport:
        """Enrichit le contexte avec les observations du navigateur."""

        report = ContextEnrichmentReport()

        if context.html_path is None:
            report.error = "Aucun document HTML disponible pour l'extraction des styles calculés."
            return report

        # Une nouvelle extraction remplace les résultats
        # textuels issus de l'extraction précédente.
        context.text_contrast_samples = []
        context.text_contrast_extraction_attempted = True
        context.text_contrast_coverage_complete = False
        context.text_contrast_unresolved_count = 0
        context.unresolved_text_contrasts = []

        # Les observations non textuelles précédentes sont
        # également invalidées.
        #
        # Les éventuels échantillons non textuels déjà fournis
        # explicitement dans le contexte ne sont pas modifiés.
        # Cette étape n'en crée aucun nouveau.
        context.unresolved_non_text_contrasts = []

        # --------------------------------------------------
        # Extraction textuelle : RGAA 3.2
        # --------------------------------------------------

        try:
            observations = await extract_text_styles(context.html_path)

            report.observations = observations

            for observation in observations:
                if self._requires_review(observation):
                    report.review_observations.append(observation)
                else:
                    report.usable_observations.append(observation)

            build_result = self.contrast_sample_builder.build(observations)

            report.text_contrast_samples = build_result.samples
            report.rejected_observations = build_result.rejected_observations
            report.rejection_reasons = build_result.rejection_reasons

            # Préparation complète avant publication.
            text_samples = list(build_result.samples)

            unresolved_text = [
                UnresolvedTextContrast(
                    element=observation.element,
                    text=observation.text,
                    reason=reason,
                    font_size_px=(
                        observation.font_size_px
                        if isfinite(observation.font_size_px) and observation.font_size_px > 0
                        else None
                    ),
                    font_weight=(
                        observation.font_weight
                        if isinstance(observation.font_weight, int)
                        and not isinstance(observation.font_weight, bool)
                        and 1 <= observation.font_weight <= 1000
                        else None
                    ),
                )
                for observation, reason in zip(
                    build_result.rejected_observations,
                    build_result.rejection_reasons,
                    strict=True,
                )
            ]

            context.text_contrast_samples = text_samples
            context.unresolved_text_contrasts = unresolved_text
            context.text_contrast_unresolved_count = len(unresolved_text)

            # Une extraction réussie ne démontre jamais,
            # à elle seule, une couverture complète.
            context.text_contrast_coverage_complete = False

        except Exception as error:
            report.error = f"Échec de l'enrichissement des styles calculés : {type(error).__name__}: {error}"

            context.text_contrast_samples = []
            context.text_contrast_unresolved_count = 0
            context.text_contrast_coverage_complete = False
            context.unresolved_text_contrasts = []

        # --------------------------------------------------
        # Extraction non textuelle : RGAA 3.3
        # --------------------------------------------------
        #
        # Cette étape est indépendante de RGAA 3.2.
        # Elle conserve les observations CSS candidates,
        # sans produire de mesures RGAA validées.

        try:
            non_text_observations = await extract_non_text_styles(context.html_path)

            unresolved_non_text = [
                UnresolvedNonTextContrast(
                    element=observation.element,
                    kind=observation.kind,
                    comparison=observation.comparison,
                    foreground_color=observation.foreground_color,
                    background_color=observation.background_color,
                    state=observation.state,
                    reason=(
                        observation.review_reason or ("Applicabilité et contraste non textuel à confirmer manuellement")
                    ),
                )
                for observation in non_text_observations
            ]

            report.non_text_observations = list(non_text_observations)

            context.unresolved_non_text_contrasts = unresolved_non_text

        except Exception as error:
            report.non_text_error = (
                f"Échec de l'extraction des contrastes non textuels : {type(error).__name__}: {error}"
            )

            context.unresolved_non_text_contrasts = []

        return report

    @staticmethod
    def _requires_review(
        observation: TextStyleObservation,
    ) -> bool:
        """Détermine si une observation textuelle nécessite une vérification."""

        if observation.review_reason is not None:
            return True

        if observation.background_color is None:
            return True

        if not observation.text.strip():
            return True

        if not observation.color.strip():
            return True

        if not isfinite(observation.font_size_px):
            return True

        if observation.font_size_px <= 0:
            return True

        if not isfinite(observation.font_weight):
            return True

        if observation.font_weight <= 0:
            return True

        return False

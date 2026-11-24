"""Conversion prudente des observations CSS en échantillons de contraste."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite

from accessi_code.input.extractors.computed_styles import TextStyleObservation
from accessi_code.models.color_style import TextContrastSample

_RGB_PATTERN = re.compile(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$")


@dataclass
class ContrastSampleBuildResult:
    """Résultat technique de la conversion des observations."""

    samples: list[TextContrastSample] = field(default_factory=list)

    rejected_observations: list[TextStyleObservation] = field(default_factory=list)

    rejection_reasons: list[str] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        """Nombre d'échantillons construits."""

        return len(self.samples)

    @property
    def rejected_count(self) -> int:
        """Nombre d'observations rejetées."""

        return len(self.rejected_observations)


class ContrastSampleBuilder:
    """
    Convertit les observations Playwright en TextContrastSample.

    Cette conversion valide les données disponibles, mais ne garantit
    pas que le fond observé correspond parfaitement au rendu visuel.

    Le résultat ne doit donc pas encore être utilisé pour déclarer
    automatiquement un critère RGAA conforme.
    """

    @staticmethod
    def _is_opaque_rgb(color: str | None) -> bool:
        """Vérifie qu'une couleur est un RGB opaque valide."""

        if color is None:
            return False

        match = _RGB_PATTERN.fullmatch(color.strip())

        if match is None:
            return False

        return all(0 <= int(channel) <= 255 for channel in match.groups())

    @staticmethod
    def _rejection_reason(
        observation: TextStyleObservation,
    ) -> str | None:
        """Retourne la raison du rejet ou None si les données sont valides."""

        if observation.review_reason is not None:
            return observation.review_reason

        if not observation.text.strip():
            return "Texte vide."

        if not ContrastSampleBuilder._is_opaque_rgb(observation.color):
            return "Couleur du texte absente ou non opaque."

        if not ContrastSampleBuilder._is_opaque_rgb(observation.background_color):
            return "Couleur de fond absente ou non opaque."

        if not isfinite(observation.font_size_px):
            return "Taille de police non finie."

        if observation.font_size_px <= 0:
            return "Taille de police invalide."

        if not isfinite(observation.font_weight):
            return "Graisse de police non finie."

        if not 1 <= observation.font_weight <= 1000:
            return "Graisse de police invalide."

        return None

    def build(
        self,
        observations: list[TextStyleObservation],
    ) -> ContrastSampleBuildResult:
        """Convertit les observations dont les données sont exploitables."""

        result = ContrastSampleBuildResult()

        for observation in observations:
            rejection_reason = self._rejection_reason(observation)

            if rejection_reason is not None:
                result.rejected_observations.append(observation)
                result.rejection_reasons.append(rejection_reason)
                continue

            # Les tests RGAA recevront les valeurs validées, sans
            # supposer qu'un contrôle de contraste complet est terminé.
            sample = TextContrastSample(
                element=observation.element,
                text=observation.text,
                color=observation.color.strip(),
                background_color=observation.background_color.strip(),
                font_size_px=observation.font_size_px,
                font_weight=observation.font_weight,
            )

            result.samples.append(sample)

        return result

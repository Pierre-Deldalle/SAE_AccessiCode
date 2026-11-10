"""Catalogue des 13 thématiques RGAA et filtrage du registre par thématique."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from accessi_code.rgaa.registry import TestRegistry


@dataclass(frozen=True, slots=True)
class RGAATheme:
    """Une thématique officielle du RGAA 4.1.2."""

    number: int
    name: str

    @property
    def label(self) -> str:
        """Libellé affiché dans l'interface, par exemple « 6. Liens »."""
        return f"{self.number}. {self.name}"


RGAA_THEMES: tuple[RGAATheme, ...] = (
    RGAATheme(1, "Images"),
    RGAATheme(2, "Cadres"),
    RGAATheme(3, "Couleurs"),
    RGAATheme(4, "Multimédia"),
    RGAATheme(5, "Tableaux"),
    RGAATheme(6, "Liens"),
    RGAATheme(7, "Scripts"),
    RGAATheme(8, "Éléments obligatoires"),
    RGAATheme(9, "Structuration de l'information"),
    RGAATheme(10, "Présentation de l'information"),
    RGAATheme(11, "Formulaires"),
    RGAATheme(12, "Navigation"),
    RGAATheme(13, "Consultation"),
)

THEMES_BY_NUMBER: dict[int, RGAATheme] = {theme.number: theme for theme in RGAA_THEMES}


def theme_number(criterion_id: str) -> int | None:
    """
    Retourne le numéro de thématique d'un critère (« 6.1 » -> 6).

    Retourne None si l'identifiant ne correspond à aucune thématique connue.
    """
    head = str(criterion_id).strip().split(".", 1)[0]
    if not head.isdigit():
        return None
    number = int(head)
    return number if number in THEMES_BY_NUMBER else None


def parse_theme_label(label: str) -> int | None:
    """Retrouve le numéro de thématique à partir d'un libellé « N. Nom »."""
    return theme_number(str(label).split(" ", 1)[0].rstrip("."))


def implemented_themes(registry: TestRegistry) -> frozenset[int]:
    """Thématiques possédant au moins un test dans le registre."""
    numbers = (theme_number(test.criterion_id) for test in registry)
    return frozenset(number for number in numbers if number is not None)


def filter_registry_by_themes(
    registry: TestRegistry,
    themes: Iterable[int],
) -> TestRegistry:
    """
    Construit un nouveau registre limité aux thématiques demandées.

    Les instances de tests sont réutilisées et l'ordre d'enregistrement
    est conservé. Le registre d'origine n'est pas modifié.
    """
    wanted = set(themes)
    return TestRegistry(test for test in registry if theme_number(test.criterion_id) in wanted)

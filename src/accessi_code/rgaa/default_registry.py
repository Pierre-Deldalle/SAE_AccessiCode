"""Registre par défaut des tests RGAA AccessiCode."""

from __future__ import annotations

from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111,
    Test112,
    Test113,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import Test171
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test311,
    Test312,
    Test313,
    Test314,
    Test315,
    Test316,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test321,
    Test322,
    Test323,
    Test324,
    Test325,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test331,
    Test332,
    Test333,
    Test334,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_1 import Test511
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_1 import (
    Test811,
    Test812,
    Test813,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_4 import Test841
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_5 import Test851
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_6 import Test861
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_1 import Test1111


def build_default_registry() -> TestRegistry:
    """Construit le registre des tests RGAA actuellement implémentés."""

    return TestRegistry(
        [
            # Thématique 1 — Images
            Test111(),
            Test112(),
            Test113(),
            Test171(),
            # Thématique 3 — Couleurs
            Test311(),
            Test312(),
            Test313(),
            Test314(),
            Test315(),
            Test316(),
            Test321(),
            Test322(),
            Test323(),
            Test324(),
            Test325(),
            Test331(),
            Test332(),
            Test333(),
            Test334(),
            # Thématique 5 — Tableaux
            Test511(),
            # Thématique 8 — Éléments obligatoires
            Test811(),
            Test812(),
            Test813(),
            Test841(),
            Test851(),
            Test861(),
            # Thématique 11 — Formulaires
            Test1111(),
        ]
    )

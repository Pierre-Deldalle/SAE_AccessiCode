
from __future__ import annotations

from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111,
    Test112,
    Test113,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import (
    Test171,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_1 import (
    Test511,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test611,
    Test612,
    Test613,
    Test614,
    Test615,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_2 import (
    Test621,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_1 import (
    Test811,
    Test812,
    Test813,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_4 import (
    Test841,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_5 import (
    Test851,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_6 import (
    Test861,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_1 import (
    Test1111,
)


def build_default_registry() -> TestRegistry:
    """
    Construit le registre des tests RGAA actuellement implémentés.
    """
    return TestRegistry(
        [
            # Thème 1 — Images
            Test111(),
            Test112(),
            Test113(),
            Test171(),
            # Thème 5 — Tableaux
            Test511(),
            # Thème 6 — Liens
            Test611(),
            Test612(),
            Test613(),
            Test614(),
            Test615(),
            Test621(),
            # Thème 8 — Éléments obligatoires
            Test811(),
            Test812(),
            Test813(),
            Test841(),
            Test851(),
            Test861(),
            # Thème 11 — Formulaires
            Test1111(),
        ]
    )

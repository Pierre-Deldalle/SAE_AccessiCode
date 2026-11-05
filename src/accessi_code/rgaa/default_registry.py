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
            Test111(),
            Test112(),
            Test113(),
            Test171(),
            Test511(),
            Test811(),
            Test812(),
            Test813(),
            Test841(),
            Test851(),
            Test861(),
            Test1111(),
        ]
    )

from __future__ import annotations

from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111,
    Test112,
    Test113,
    Test114,
    Test115,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_2 import (
    Test121,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import (
    Test171,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_9 import (
    Test191,
)
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_1 import (
    Test211,
)
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_2 import (
    Test221,
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
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_2 import (
    Test821,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_3 import (
    Test831,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_6 import (
    Test861,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_7 import (
    Test871,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_8 import (
    Test881,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_9 import (
    Test891,
)
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_10 import (
    Test8101,
    Test8102,
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
            Test114(),
            Test115(),
            Test121(),
            Test191(),
            Test171(),
            Test211(),
            Test221(),
            Test511(),
            Test811(),
            Test812(),
            Test813(),
            Test821(),
            Test831(),
            Test841(),
            Test851(),
            Test861(),
            Test871(),
            Test881(),
            Test891(),
            Test8101(),
            Test8102(),
            Test1111(),
        ]
    )

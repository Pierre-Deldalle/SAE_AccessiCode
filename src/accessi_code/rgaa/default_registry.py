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
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_1 import (
    Test411,
    Test412,
    Test413,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_2 import (
    Test421,
    Test422,
    Test423,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_3 import (
    Test431,
    Test432,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_4 import (
    Test441,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_5 import (
    Test451,
    Test452,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_6 import (
    Test461,
    Test462,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_7 import (
    Test471,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_8 import (
    Test481,
    Test482,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_9 import (
    Test491,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_10 import (
    Test4101,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_11 import (
    Test4111,
    Test4112,
    Test4113,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_12 import (
    Test4121,
    Test4122,
)
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_13 import (
    Test4131,
    Test4132,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_1 import (
    Test511,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_2 import (
    Test521,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_3 import (
    Test531,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_4 import (
    Test541,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_5 import (
    Test551,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_6 import (
    Test561,
    Test562,
    Test563,
    Test564,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_7 import (
    Test571,
    Test572,
    Test573,
    Test574,
    Test575,
)
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_8 import (
    Test581,
)
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_1 import (
    Test711,
    Test712,
    Test713,
)
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_2 import (
    Test721,
    Test722,
)
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_3 import (
    Test731,
    Test732,
)
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_4 import (
    Test741,
)
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_5 import (
    Test751,
    Test752,
    Test753,
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
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_1 import (
    Test911,
    Test912,
    Test913,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_2 import (
    Test921,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_3 import (
    Test931,
    Test932,
    Test933,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_4 import (
    Test941,
    Test942,
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
            Test411(),
            Test412(),
            Test413(),
            Test421(),
            Test422(),
            Test423(),
            Test431(),
            Test432(),
            Test441(),
            Test451(),
            Test452(),
            Test461(),
            Test462(),
            Test471(),
            Test481(),
            Test482(),
            Test491(),
            Test4101(),
            Test4111(),
            Test4112(),
            Test4113(),
            Test4121(),
            Test4122(),
            Test4131(),
            Test4132(),
            Test511(),
            Test521(),
            Test531(),
            Test541(),
            Test551(),
            Test561(),
            Test562(),
            Test563(),
            Test564(),
            Test571(),
            Test572(),
            Test573(),
            Test574(),
            Test575(),
            Test581(),
            Test711(),
            Test712(),
            Test713(),
            Test721(),
            Test722(),
            Test731(),
            Test732(),
            Test741(),
            Test751(),
            Test752(),
            Test753(),
            Test811(),
            Test812(),
            Test813(),
            Test841(),
            Test851(),
            Test861(),
            Test911(),
            Test912(),
            Test913(),
            Test921(),
            Test931(),
            Test932(),
            Test933(),
            Test941(),
            Test942(),
            Test1111(),
        ]
    )

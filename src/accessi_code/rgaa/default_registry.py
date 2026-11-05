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


from accessi_code.rgaa.tests.theme_11_forms.criterion_11_2 import (
    Test1121, Test1122, Test1123, Test1124, Test1125, Test1126,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_3 import (
    Test1131, Test1132,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_4 import (
    Test1141, Test1142, Test1143,
)

from accessi_code.rgaa.tests.theme_11_forms.criterion_11_5 import (
    Test1151,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_6 import (
    Test1161,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_7 import (
    Test1171,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_8 import (
    Test1181, Test1182, Test1183,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_9 import (
    Test1191, Test1192,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_10 import (
    Test11101, Test11102, Test11103, Test11104, Test11105, Test11106, Test11107,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_11 import (
    Test11111, Test11112,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_12 import (
    Test11121, Test11122,
)
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_13 import (
    Test11131,
)



# Thème 12 — Navigation
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_1 import (Test1211,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_2 import (Test1221,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_3 import (Test1231, Test1232, Test1233,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_4 import (Test1241, Test1242, Test1243,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_5 import (Test1251, Test1252, Test1253,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_6 import (Test1261,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_7 import (Test1271, Test1272,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_8 import (Test1281, Test1282,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_9 import (Test1291,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_10 import (Test12101,)
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_11 import (Test12111,)

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
            Test1121(), Test1122(), Test1123(), Test1124(), Test1125(), Test1126(),
            Test1131(), Test1132(),
            Test1141(), Test1142(), Test1143(),
            Test1151(),
            Test1161(),
            Test1171(),
            Test1181(),
            Test1182(),
            Test1183(),
            Test1191(),
            Test1192(),
            Test11101(),
            Test11102(),
            Test11103(),
            Test11104(),
            Test11105(),
            Test11106(),
            Test11107(),
            Test11111(),
            Test11112(),
            Test11121(),
            Test11122(),
            Test11131(),
            Test1211(),
            Test1221(),
            Test1231(),
            Test1232(),
            Test1233(),
            Test1241(),
            Test1242(),
            Test1243(),
            Test1251(),
            Test1252(),
            Test1253(),
            Test1261(),
            Test1271(),
            Test1272(),
            Test1281(),
            Test1282(),
            Test1291(),
            Test12101(),
            Test12111(),
        ]
    )

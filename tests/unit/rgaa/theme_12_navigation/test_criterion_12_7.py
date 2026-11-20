from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_6 import Test1261


def test_native_landmarks_pass(context_factory, run_rgaa):
    c = context_factory('<html><header>H</header><nav>N</nav><main>M</main><footer>F</footer></html>')
    assert run_rgaa(Test1261(), c).status == Status.PASS


def test_nested_header_review(context_factory, run_rgaa):
    c = context_factory('<main><section><header>H</header></section></main>')
    assert run_rgaa(Test1261(), c).status == Status.NEEDS_REVIEW


def test_no_zones_na(context_factory, run_rgaa):
    assert run_rgaa(Test1261(), context_factory('<p>Texte</p>')).status == Status.NOT_APPLICABLE

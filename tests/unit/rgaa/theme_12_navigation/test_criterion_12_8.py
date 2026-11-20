from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_7 import Test1271, Test1272

HTML = '<html><body><a href="#contenu">Aller au contenu</a><nav>Menu</nav><main id="contenu">Texte</main></body></html>'


def test_1271_pass(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.navigation_evidence['12.7.1'] = {'visible_on_focus': True}
    assert run_rgaa(Test1271(), c).status == Status.PASS


def test_1271_review(context_factory, run_rgaa):
    assert run_rgaa(Test1271(), context_factory(HTML)).status == Status.NEEDS_REVIEW


def test_1271_fail(context_factory, run_rgaa):
    assert run_rgaa(Test1271(), context_factory('<main id="m">Texte</main>')).status == Status.FAIL


def test_1272_pass(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.page_doms['second.html'] = BeautifulSoup(HTML, 'html.parser')
    c.navigation_evidence['12.7.2'] = {'same_visual_position': True, 'visible_on_focus': True, 'functional': True}
    assert run_rgaa(Test1272(), c).status == Status.PASS


def test_1272_review(context_factory, run_rgaa):
    assert run_rgaa(Test1272(), context_factory(HTML)).status == Status.NEEDS_REVIEW


def test_1272_fail(context_factory, run_rgaa):
    c = context_factory(HTML)
    c.navigation_evidence['12.7.2'] = {'same_visual_position': False, 'visible_on_focus': True, 'functional': True}
    assert run_rgaa(Test1272(), c).status == Status.FAIL


def test_single_page_exception(context_factory, run_rgaa):
    c = context_factory('<main>Texte</main>')
    c.navigation_evidence['12.7.1'] = {'single_page_no_need': True}
    assert run_rgaa(Test1271(), c).status == Status.NOT_APPLICABLE

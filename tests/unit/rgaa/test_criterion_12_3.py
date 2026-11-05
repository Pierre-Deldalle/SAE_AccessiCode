from bs4 import BeautifulSoup
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_2 import Test1221


def ctx(context_factory):
    html = '<html><header><nav aria-label="Menu"><a href="/">Accueil</a></nav></header><main>Page</main></html>'
    c = context_factory(html)
    c.page_doms['page2.html'] = BeautifulSoup(html, 'html.parser')
    return c


def test_visual_proof_pass(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.2.1'] = {'same_visual_position': True}
    assert run_rgaa(Test1221(), c).status == Status.PASS


def test_visual_proof_fail(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.2.1'] = {'same_visual_position': False}
    assert run_rgaa(Test1221(), c).status == Status.FAIL


def test_no_visual_proof_review(context_factory, run_rgaa):
    assert run_rgaa(Test1221(), ctx(context_factory)).status == Status.NEEDS_REVIEW


def test_one_page_na(context_factory, run_rgaa):
    assert run_rgaa(Test1221(), context_factory('<nav>Menu</nav>')).status == Status.NOT_APPLICABLE

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_4 import Test1241, Test1242, Test1243


def ctx(context_factory, second=None):
    html = '<html><header><a href="plan.html">Plan du site</a></header><main>Texte</main></html>'
    c = context_factory(html)
    c.page_doms['page2.html'] = BeautifulSoup(second or html, 'html.parser')
    return c


@pytest.mark.parametrize('cls', [Test1241, Test1243])
def test_dom_pass(context_factory, run_rgaa, cls):
    assert run_rgaa(cls(), ctx(context_factory)).status == Status.PASS


def test_visual_pass(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.4.2'] = {'same_visual_position': True}
    assert run_rgaa(Test1242(), c).status == Status.PASS


def test_visual_review(context_factory, run_rgaa):
    assert run_rgaa(Test1242(), ctx(context_factory)).status == Status.NEEDS_REVIEW


def test_visual_fail(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.4.2'] = {'same_visual_position': False}
    assert run_rgaa(Test1242(), c).status == Status.FAIL


def test_missing_link_fail(context_factory, run_rgaa):
    c = ctx(context_factory, '<html><main>Sans plan</main></html>')
    assert run_rgaa(Test1241(), c).status == Status.FAIL


def test_one_page_na(context_factory, run_rgaa):
    assert run_rgaa(Test1241(), context_factory('<a href="plan.html">Plan du site</a>')).status == Status.NOT_APPLICABLE

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_1 import Test1211


def test_two_navigation_means_pass(context_factory, run_rgaa):
    c = context_factory('<html><nav><a href="/">Accueil</a></nav><form role="search"><input type="search"></form></html>')
    assert run_rgaa(Test1211(), c).status == Status.PASS


def test_unknown_site_review(context_factory, run_rgaa):
    c = context_factory('<html><main>Bonjour</main></html>')
    assert run_rgaa(Test1211(), c).status == Status.NEEDS_REVIEW


def test_complete_site_missing_fail(context_factory, run_rgaa):
    c = context_factory('<html><main>Bonjour</main></html>')
    c.page_doms['other.html'] = c.dom
    c.site_inventory_complete = True
    assert run_rgaa(Test1211(), c).status == Status.FAIL


def test_single_page_na(context_factory, run_rgaa):
    c = context_factory('<html><main>Bonjour</main></html>')
    c.site_inventory_complete = True
    assert run_rgaa(Test1211(), c).status == Status.NOT_APPLICABLE

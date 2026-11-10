from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_3 import Test1231, Test1232, Test1233


def ctx(context_factory, href='index.html', label='Accueil'):
    c = context_factory('<html><h1>Accueil</h1></html>')
    c.page_doms['plan.html'] = BeautifulSoup(f'<html><h1>Plan du site</h1><a href="{href}">{label}</a></html>', 'html.parser')
    return c


def test_1231_pass(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.site_inventory_complete = True
    assert run_rgaa(Test1231(), c).status == Status.PASS


def test_1231_review(context_factory, run_rgaa):
    assert run_rgaa(Test1231(), ctx(context_factory)).status == Status.NEEDS_REVIEW


def test_1232_pass(context_factory, run_rgaa):
    assert run_rgaa(Test1232(), ctx(context_factory)).status == Status.PASS


def test_1232_fail(context_factory, run_rgaa):
    assert run_rgaa(Test1232(), ctx(context_factory, '#missing')).status == Status.FAIL


def test_1232_review(context_factory, run_rgaa):
    assert run_rgaa(Test1232(), ctx(context_factory, 'https://example.org/')).status == Status.NEEDS_REVIEW


def test_1233_pass(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.3.3'] = {'labels_match_destinations': {'index.html': True}}
    assert run_rgaa(Test1233(), c).status == Status.PASS


def test_1233_fail(context_factory, run_rgaa):
    c = ctx(context_factory)
    c.navigation_evidence['12.3.3'] = {'labels_match_destinations': {'index.html': False}}
    assert run_rgaa(Test1233(), c).status == Status.FAIL


def test_1233_exact_heading_pass_without_ai(context_factory, run_rgaa):
    assert run_rgaa(Test1233(), ctx(context_factory)).status == Status.PASS


def test_1233_review_when_heading_does_not_match(context_factory, run_rgaa):
    assert run_rgaa(Test1233(), ctx(context_factory, label="Découvrir le site")).status == Status.NEEDS_REVIEW


def test_no_sitemap_na(context_factory, run_rgaa):
    c = context_factory('<main>Accueil</main>')
    c.site_inventory_complete = True
    assert run_rgaa(Test1232(), c).status == Status.NOT_APPLICABLE

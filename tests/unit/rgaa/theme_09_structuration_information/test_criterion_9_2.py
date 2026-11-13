"""Critère RGAA 9.2 : structure du document."""

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_2 import Test921

FULL = (
    "<!DOCTYPE html><html><body><header><p>Logo</p></header>"
    '<nav><a href="/">Accueil</a><a href="/c">Contact</a></nav>'
    "<main><h1>Titre</h1></main><footer><p>Mentions</p></footer></body></html>"
)


def run(context_factory, run_rgaa, html, **kwargs):
    return run_rgaa(Test921(), context_factory(html, **kwargs))


def test_non_html5_doctype_is_not_applicable(context_factory, run_rgaa):
    html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "x"><html><body></body></html>'
    assert run(context_factory, run_rgaa, html).status == Status.NOT_APPLICABLE


def test_complete_structure_passes(context_factory, run_rgaa):
    assert run(context_factory, run_rgaa, FULL).status == Status.PASS


def test_missing_main_fails(context_factory, run_rgaa):
    result = run(context_factory, run_rgaa, "<!DOCTYPE html><html><body><p>Contenu</p></body></html>")
    assert result.status == Status.FAIL
    assert "<main>" in result.findings[0].message


def test_page_without_header_zone_is_not_in_default(context_factory, run_rgaa):
    html = "<!DOCTYPE html><html><body><main><h1>Titre</h1></main></body></html>"
    assert run(context_factory, run_rgaa, html).status == Status.PASS


def test_header_zone_without_header_tag_fails(context_factory, run_rgaa):
    html = '<!DOCTYPE html><html><body><div id="header">Logo</div><main>x</main></body></html>'
    result = run(context_factory, run_rgaa, html)
    assert result.status == Status.FAIL
    assert "en-tête" in result.findings[0].message


def test_navigation_zone_without_nav_fails(context_factory, run_rgaa):
    html = (
        '<!DOCTYPE html><html><body><ul class="menu"><li><a href="/">A</a></li><li><a href="/b">B</a></li></ul>'
        "<main>x</main></body></html>"
    )
    assert run(context_factory, run_rgaa, html).status == Status.FAIL


def test_nav_without_links_fails(context_factory, run_rgaa):
    html = "<!DOCTYPE html><html><body><nav><p>Texte</p></nav><main>x</main></body></html>"
    result = run(context_factory, run_rgaa, html)
    assert result.status == Status.FAIL
    assert "aucun lien" in result.findings[0].message


def test_footer_role_without_footer_tag_fails(context_factory, run_rgaa):
    html = '<!DOCTYPE html><html><body><main>x</main><div role="contentinfo">Mentions</div></body></html>'
    assert run(context_factory, run_rgaa, html).status == Status.FAIL


def test_two_visible_mains_fail(context_factory, run_rgaa):
    html = "<!DOCTYPE html><html><body><main>a</main><main>b</main></body></html>"
    assert run(context_factory, run_rgaa, html).status == Status.FAIL


def test_second_main_hidden_with_attribute_passes(context_factory, run_rgaa):
    html = "<!DOCTYPE html><html><body><main>a</main><main hidden>b</main></body></html>"
    assert run(context_factory, run_rgaa, html).status == Status.PASS


def test_main_hidden_with_css_only_still_counts(context_factory, run_rgaa):
    html = '<!DOCTYPE html><html><body><main>a</main><main style="display:none">b</main></body></html>'
    assert run(context_factory, run_rgaa, html).status == Status.FAIL

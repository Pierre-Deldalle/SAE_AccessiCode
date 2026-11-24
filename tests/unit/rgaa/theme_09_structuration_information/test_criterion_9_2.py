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


# ---- Emplacement des observations ------------------------------------


def test_header_zone_finding_is_located(context_factory, run_rgaa):
    html = '<!DOCTYPE html>\n<html><body>\n<div id="header">Logo</div>\n<main>x</main></body></html>'
    finding = run(context_factory, run_rgaa, html).findings[0]
    assert (finding.line, finding.snippet) == (3, '<div id="header">Logo</div>')


def test_nav_without_links_finding_is_located(context_factory, run_rgaa):
    html = "<!DOCTYPE html>\n<html><body>\n<main>x</main>\n<nav><p>Texte</p></nav></body></html>"
    finding = run(context_factory, run_rgaa, html).findings[0]
    assert (finding.line, finding.snippet) == (4, "<nav><p>Texte</p></nav>")


def test_missing_main_is_located_at_body(context_factory, run_rgaa):
    html = "<!DOCTYPE html>\n<html>\n<body>\n<p>Contenu</p>\n</body>\n</html>"
    finding = run(context_factory, run_rgaa, html).findings[0]
    assert (finding.line, finding.snippet) == (3, "<body> <p>Contenu</p> </body>")


def test_extra_main_is_located_at_the_second_visible_main(context_factory, run_rgaa):
    html = "<!DOCTYPE html>\n<html><body>\n<main>a</main>\n<main hidden>b</main>\n<main>c</main></body></html>"
    finding = run(context_factory, run_rgaa, html).findings[0]
    assert (finding.line, finding.snippet) == (5, "<main>c</main>")
    assert finding.evidence["lines"] == [3, 5]


# ---- Corrections proposées -------------------------------------------


def body(content: str) -> str:
    return f"<!DOCTYPE html><html><body>{content}</body></html>"


def test_zone_example_renames_the_div_and_drops_the_redundant_role(context_factory, run_rgaa):
    finding = run(context_factory, run_rgaa, body('<div id="haut" role="banner">Logo</div><main>x</main>')).findings[0]
    assert finding.recommendation == (
        "Utiliser la balise <header> pour la zone d'en-tête. "
        'Exemple : <div id="haut" role="banner">Logo</div> → <header id="haut">Logo</header>'
    )


def test_navigation_list_is_wrapped_in_nav(context_factory, run_rgaa):
    menu = '<ul class="menu"><li><a href="/">A</a></li><li><a href="/b">B</a></li></ul>'
    finding = run(context_factory, run_rgaa, body(f"{menu}<main>x</main>")).findings[0]
    assert finding.recommendation.endswith(f"Exemple : {menu} → <nav>{menu}</nav>")


def test_nav_without_links_example(context_factory, run_rgaa):
    finding = run(context_factory, run_rgaa, body('<nav aria-label="Pages"><p>Texte</p></nav><main>x</main>')).findings[
        0
    ]
    assert finding.recommendation.endswith(
        'Exemple : <nav aria-label="Pages"><p>Texte</p></nav> → <div><p>Texte</p></div>'
    )


def test_extra_main_example_adds_hidden(context_factory, run_rgaa):
    finding = run(context_factory, run_rgaa, body('<main>a</main><main class="b">c</main>')).findings[0]
    assert finding.recommendation.endswith('Exemple : <main class="b"> → <main class="b" hidden="">')


def test_missing_main_has_no_example(context_factory, run_rgaa):
    finding = run(context_factory, run_rgaa, body("<p>Contenu</p>")).findings[0]
    assert finding.recommendation == "Encadrer le contenu principal de la page avec une balise <main>."

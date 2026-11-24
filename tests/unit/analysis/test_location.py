"""Emplacement d'un élément (ligne et extrait HTML) et son report dans les Finding."""

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.location import SNIPPET_LIMIT, element_snippet, locate, opening_tag, source_file_name
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.audit_file import AuditFile
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.outcomes import make_outcome

HTML = '<html>\n<body>\n<p>Texte</p>\n<iframe src="carte.html"\n  title="Carte"></iframe>\n</body>\n</html>'


def _iframe() -> Tag:
    return BeautifulSoup(HTML, "html.parser").iframe


def test_locate_returns_line_and_snippet():
    assert locate(_iframe()) == (4, '<iframe src="carte.html" title="Carte"></iframe>')


def test_locate_without_element():
    assert locate(None) == (None, None)


def test_element_built_in_code_has_no_line():
    tag = BeautifulSoup("", "html.parser").new_tag("img", src="x.png")
    assert locate(tag) == (None, '<img src="x.png"/>')


def test_long_element_keeps_only_its_opening_tag():
    soup = BeautifulSoup(f'<div id="bloc" class="a > b">{"mot " * 100}</div>', "html.parser")
    assert element_snippet(soup.div) == '<div id="bloc" class="a &gt; b">'


def test_very_long_opening_tag_is_truncated():
    soup = BeautifulSoup(f'<iframe title="{"x" * 300}"></iframe>', "html.parser")
    snippet = element_snippet(soup.iframe)
    assert len(snippet) == SNIPPET_LIMIT
    assert snippet.endswith("…")


def test_make_outcome_fills_location_from_node():
    outcome = make_outcome(Status.FAIL, "iframe[index=0]", "Problème.", "Corriger.", node=_iframe(), src="x")
    assert outcome.finding is not None
    assert (outcome.finding.line, outcome.finding.snippet) == (4, '<iframe src="carte.html" title="Carte"></iframe>')
    assert outcome.finding.evidence == {"src": "x"}


def test_make_outcome_without_node_or_finding():
    outcome = make_outcome(Status.FAIL, "iframe[index=0]", "Problème.")
    assert outcome.finding is not None
    assert (outcome.finding.line, outcome.finding.snippet) == (None, None)
    assert make_outcome(Status.PASS, node=_iframe()).finding is None


def test_opening_tag_keeps_real_attributes_and_applies_changes():
    soup = BeautifulSoup('<iframe id="c" src="m.html" title="">texte</iframe>', "html.parser")
    assert opening_tag(soup.iframe) == '<iframe id="c" src="m.html" title="">'
    assert opening_tag(soup.iframe, title="Carte") == '<iframe id="c" src="m.html" title="Carte">'
    assert opening_tag(soup.iframe, title=None, lang="fr") == '<iframe id="c" src="m.html" lang="fr">'


def _context(tmp_path, *files: tuple[str, str]) -> AuditContext:
    source = tmp_path / "source"
    audit_files = [AuditFile(original, source / copy, ".html") for original, copy in files]
    return AuditContext(audit_id="x", workspace_path=tmp_path, files=audit_files)


def test_source_file_name_keeps_the_site_tree(tmp_path):
    context = _context(tmp_path, ("contact.html", "pages/contact.html"))
    assert source_file_name(context, tmp_path / "source" / "pages" / "contact.html") == "pages/contact.html"


def test_source_file_name_uses_original_name_of_a_renamed_copy(tmp_path):
    context = _context(tmp_path, ("index.html", "index_2.html"))
    assert source_file_name(context, tmp_path / "source" / "index_2.html") == "index.html"


def test_source_file_name_outside_the_workspace(tmp_path):
    context = _context(tmp_path)
    assert source_file_name(context, tmp_path / "ailleurs" / "page.html") == "page.html"
    assert source_file_name(context, None) is None

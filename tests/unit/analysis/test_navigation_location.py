"""Emplacement des observations du thème 12 : ``finding`` et ``page_file``."""

from bs4 import BeautifulSoup

from accessi_code.analysis.navigation import finding, page_file
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.audit_file import AuditFile

HTML = '<html lang="fr">\n<body>\n<nav>\n<a href="plan.html">Plan du site</a>\n</nav>\n</body>\n</html>'


def _context(tmp_path, *files: tuple[str, str]) -> AuditContext:
    source = tmp_path / "source"
    audit_files = [AuditFile(original, source / copy, ".html") for original, copy in files]
    dom = BeautifulSoup(HTML, "html.parser")
    return AuditContext(
        audit_id="x", workspace_path=tmp_path, files=audit_files, html_path=source / "index.html", dom=dom
    )


def test_finding_has_line_and_snippet_of_the_element():
    soup = BeautifulSoup(HTML, "html.parser")
    note = finding(soup.a, soup, "Message.", "Recommandation.", href="plan.html")
    assert note.element == "a[index=3]"
    assert note.line == 4
    assert note.snippet == '<a href="plan.html">Plan du site</a>'
    assert note.file is None
    assert note.evidence == {"href": "plan.html"}


def test_finding_keeps_the_given_file():
    soup = BeautifulSoup(HTML, "html.parser")
    note = finding(soup.nav, soup, "Message.", "Recommandation.", file="pages/plan.html")
    assert (note.file, note.line) == ("pages/plan.html", 3)


def test_finding_on_the_whole_document_has_no_line():
    soup = BeautifulSoup("<p>Texte</p>", "html.parser")
    note = finding(soup.html or soup, soup, "Message.", "Recommandation.")
    assert (note.element, note.line, note.snippet) == ("document", None, None)


def test_page_file_is_none_for_the_audited_page(tmp_path):
    context = _context(tmp_path, ("index.html", "index.html"))
    context.page_doms["index.html"] = context.dom
    assert page_file(context, context.dom) is None


def test_page_file_keeps_the_site_tree(tmp_path):
    context = _context(tmp_path, ("index.html", "index.html"), ("plan.html", "pages/plan.html"))
    other = BeautifulSoup(HTML, "html.parser")
    context.page_doms["pages/plan.html"] = other
    assert page_file(context, other) == "pages/plan.html"


def test_page_file_uses_original_name_of_a_renamed_copy(tmp_path):
    context = _context(tmp_path, ("index.html", "index.html"), ("index.html", "index_2.html"))
    other = BeautifulSoup(HTML, "html.parser")
    context.page_doms["index_2.html"] = other
    assert page_file(context, other) == "index.html"


def test_page_file_without_imported_file_uses_the_page_key(tmp_path):
    context = _context(tmp_path)
    other = BeautifulSoup(HTML, "html.parser")
    context.page_doms["plan.html"] = other
    assert page_file(context, other) == "plan.html"

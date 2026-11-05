from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_3 import Test1132


def test_builder_populates_page_doms_and_1132(tmp_path: Path, run_rgaa):
    first = tmp_path / "index.html"
    second = tmp_path / "contact.html"
    first.write_text('<label for="x">Courriel</label><input id="x" name="email">', encoding="utf-8")
    second.write_text('<label for="y">E-mail</label><input id="y" name="email">', encoding="utf-8")
    context = AuditContextBuilder(tmp_path / "workspace").build([first, second])
    assert set(context.page_doms) == {"index.html", "contact.html"}
    assert context.dom is context.page_doms["index.html"]
    result = run_rgaa(Test1132(), context)
    assert result.status == Status.PASS
    assert result.metadata["pages_analyzed"] == 2

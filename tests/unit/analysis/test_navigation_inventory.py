from pathlib import Path

from bs4 import BeautifulSoup

from accessi_code.analysis.navigation import is_site_inventory_complete, linked_page_keys
from accessi_code.input.context_builder import AuditContextBuilder


def dom(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_linked_page_keys_resolves_relative_paths() -> None:
    soup = dom(
        '<a href="contact.html">Contact</a>'
        '<a href="../index.html">Accueil</a>'
        '<a href="/blog/">Blog</a>'
        '<a href="./a-propos.htm#equipe">Équipe</a>'
    )
    assert linked_page_keys("pages/offres.html", soup) == [
        "pages/contact.html",
        "index.html",
        "blog/index.html",
        "pages/a-propos.htm",
    ]


def test_linked_page_keys_ignores_external_links_and_resources() -> None:
    soup = dom(
        '<a href="https://exemple.fr/page.html">Externe</a>'
        '<a href="mailto:a@b.fr">Mail</a>'
        '<a href="#contenu">Aller au contenu</a>'
        '<a href="guide.pdf">PDF</a>'
        '<a href="javascript:void(0)">Script</a>'
    )
    assert linked_page_keys("index.html", soup) == []


def test_link_outside_the_root_cannot_be_inventoried() -> None:
    assert linked_page_keys("index.html", dom('<a href="../autre.html">x</a>')) == [None]


def test_inventory_complete_when_every_linked_page_is_imported() -> None:
    pages = {
        "index.html": dom('<a href="contact.html">Contact</a>'),
        "contact.html": dom('<a href="index.html">Accueil</a>'),
    }
    assert is_site_inventory_complete(pages) is True


def test_inventory_incomplete_when_a_linked_page_is_missing() -> None:
    pages = {"index.html": dom('<a href="contact.html">Contact</a>')}
    assert is_site_inventory_complete(pages) is False


def test_single_page_without_internal_links_is_complete() -> None:
    assert is_site_inventory_complete({"index.html": dom("<p>Page unique</p>")}) is True


def test_no_page_is_never_complete() -> None:
    assert is_site_inventory_complete({}) is False


def test_builder_sets_site_inventory_complete(tmp_path: Path) -> None:
    index = tmp_path / "index.html"
    contact = tmp_path / "contact.html"
    index.write_text('<a href="contact.html">Contact</a>', encoding="utf-8")
    contact.write_text('<a href="index.html">Accueil</a>', encoding="utf-8")

    complete = AuditContextBuilder(tmp_path / "w1").build([index, contact])
    partial = AuditContextBuilder(tmp_path / "w2").build([index])

    assert complete.site_inventory_complete is True
    assert partial.site_inventory_complete is False

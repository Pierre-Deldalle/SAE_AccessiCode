from bs4 import BeautifulSoup

from accessi_code.analysis.structure import list_candidates, visual_list_items


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_visual_list_items_of_a_block_without_bullets():
    soup = _soup("<p>- Audit<br>- Formation<br>–  Conseil</p>")

    assert visual_list_items(soup.p, ordered=False) == ["Audit", "Formation", "Conseil"]


def test_visual_list_items_of_an_ordered_block():
    soup = _soup("<p>1. Importer<br>2) Analyser<br>Note de bas</p>")

    assert visual_list_items(soup.p, ordered=True) == ["Importer", "Analyser"]


def test_visual_list_items_of_consecutive_paragraphs():
    soup = _soup("<p>Intro</p><p>• Audit</p><p>• Formation</p><p>Fin du texte</p>")
    [candidate] = list_candidates(soup, ordered=False)

    assert visual_list_items(candidate, ordered=False) == ["Audit", "Formation"]

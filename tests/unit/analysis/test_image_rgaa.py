"""Régressions pour les sélecteurs et la résolution des alternatives du thème 1."""
from bs4 import BeautifulSoup

from accessi_code.analysis.image_rgaa import (
    alternative,
    image_elements,
    role,
    semantic_alternatives,
    text_refs,
)


def test_role_img_does_not_accept_title_as_1_1_alternative():
    soup = BeautifulSoup('<div role="img" title="Décor"></div>', 'html.parser')
    assert alternative(soup.div, soup, 'img') == []


def test_area_title_is_semantic_alternative_but_not_1_1_alternative():
    soup = BeautifulSoup('<area title="Lien" href="/a">', 'html.parser')
    assert alternative(soup.area, soup, 'area') == []
    assert semantic_alternatives(soup.area, soup, 'area') == ['Lien']


def test_canvas_aria_labelledby_resolves_text():
    soup = BeautifulSoup('<p id="t">Données</p><canvas aria-labelledby="t"></canvas>', 'html.parser')
    assert alternative(soup.canvas, soup, 'canvas') == ['Données']


def test_duplicate_aria_labelledby_id_is_invalid():
    soup = BeautifulSoup('<p id="t">A</p><p id="t">B</p><img aria-labelledby="t">', 'html.parser')
    assert text_refs(soup.img, soup, 'aria-labelledby') == ''


def test_image_elements_do_not_duplicate_nested_svg_role_img():
    soup = BeautifulSoup('<svg role="img"></svg><div role="img"></div><img alt="Photo">', 'html.parser')
    assert [e.name for e in image_elements(soup, 'img')] == ['div', 'img']
    assert [e.name for e in image_elements(soup, 'svg')] == ['svg']


def test_decorative_img_alt_empty_is_not_informative_by_markup():
    soup = BeautifulSoup('<img alt="">', 'html.parser')
    assert role(soup.img, 'img', {}) is False

from bs4 import BeautifulSoup
from accessi_code.analysis.forms import (button_name, common_group, group_candidates,
                                         group_legend, normalize, referenced_text)


def test_reference():
    soup = BeautifulSoup('<span id="x">Nom</span><input aria-labelledby="x">', 'html.parser')
    assert referenced_text(soup.input, soup, 'aria-labelledby') == 'Nom'


def test_duplicate_reference():
    soup = BeautifulSoup('<span id="x">A</span><span id="x">B</span><input aria-labelledby="x">', 'html.parser')
    assert referenced_text(soup.input, soup, 'aria-labelledby') == ''


def test_group():
    soup = BeautifulSoup('<fieldset><legend>Choix</legend><input type="radio" name="x"><input type="radio" name="x"></fieldset>', 'html.parser')
    group = group_candidates(soup)[0]
    assert common_group(group).name == 'fieldset'
    assert group_legend(common_group(group), soup) == 'Choix'


def test_normalization():
    assert normalize('É-mail !') == 'e mail'


def test_button_aria():
    soup = BeautifulSoup('<button aria-label="Envoyer">OK</button>', 'html.parser')
    assert button_name(soup.button, soup) == 'Envoyer'

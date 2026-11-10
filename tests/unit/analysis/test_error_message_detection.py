from bs4 import BeautifulSoup

from accessi_code.analysis.forms import error_text


def test_ordinary_describedby_is_not_an_error():
    soup = BeautifulSoup('<form><p id="help">Les champs sont facultatifs.</p><input aria-describedby="help"></form>', 'html.parser')
    assert error_text(soup.input, soup) == ''


def test_invalid_field_with_alert_is_an_error():
    soup = BeautifulSoup('<form><p id="err" role="alert">Erreur : saisie invalide</p><input aria-invalid="true" aria-describedby="err"></form>', 'html.parser')
    assert 'Erreur' in error_text(soup.input, soup)


def test_hidden_errormessage_not_treated_as_current_error():
    soup = BeautifulSoup('<form><p id="err">Erreur : saisie invalide</p><input aria-errormessage="err"></form>', 'html.parser')
    assert error_text(soup.input, soup) == ''

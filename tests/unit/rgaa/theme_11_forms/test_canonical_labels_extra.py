from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_2 import Test1121
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_11 import Test11111, Test11112


def test_canonical_name_and_message_labels(context_factory, run_rgaa):
    html = '<form><label for="nom">Nom</label><input id="nom" name="nom"><label for="msg">Message</label><textarea id="msg" name="message"></textarea></form>'
    assert run_rgaa(Test1121(), context_factory(html)).status == TestStatus.PASS


def test_unrelated_label_stays_review(context_factory, run_rgaa):
    html = '<form><label for="nom">Votre couleur préférée</label><input id="nom" name="nom"></form>'
    assert run_rgaa(Test1121(), context_factory(html)).status == TestStatus.NEEDS_REVIEW


def test_optional_help_not_an_error(context_factory, run_rgaa):
    html = '<form><p id="aide">Les champs sont facultatifs.</p><input aria-describedby="aide"></form>'
    assert run_rgaa(Test11111(), context_factory(html)).status == TestStatus.NOT_APPLICABLE
    assert run_rgaa(Test11112(), context_factory(html)).status == TestStatus.NOT_APPLICABLE

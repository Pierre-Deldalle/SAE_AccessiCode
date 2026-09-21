
from accessi_code.models.result import TestStatus
from accessi_code.tests.theme_11_formulaires.criterion_11_1_1 import (
    Criterion111,
)


def test_field_with_label_for():
    html = """
    <form>
        <label for="email">Adresse e-mail</label>
        <input id="email" type="email">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_field_with_aria_label():
    html = """
    <form>
        <input type="text" aria-label="Nom">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.PASS
    assert len(result.findings) == 0


def test_field_with_aria_labelledby():
    html = """
    <form>
        <span id="email-label">Adresse e-mail</span>
        <input type="email" aria-labelledby="email-label">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.PASS
    assert len(result.findings) == 0


def test_field_with_title():
    html = """
    <form>
        <input type="text" title="Nom complet">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.PASS
    assert len(result.findings) == 0


def test_field_without_label():
    html = """
    <form>
        <input type="text" id="username">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].element == "input#username"


def test_field_with_invalid_labelledby_reference():
    html = """
    <form>
        <input type="text" aria-labelledby="missing-label">
    </form>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.FAIL
    assert len(result.findings) == 1


def test_no_form_fields():
    html = """
    <main>
        <h1>Page sans formulaire</h1>
        <p>Contenu de la page.</p>
    </main>
    """

    result = Criterion111().run(html)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert result.tested_elements == 0
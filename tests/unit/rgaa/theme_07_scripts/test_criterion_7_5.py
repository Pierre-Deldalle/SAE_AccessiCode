import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_5 import (
    Test751,
    Test752,
    Test753,
)


@pytest.mark.parametrize("test_class", [Test751, Test752, Test753])
def test_no_status_messages_is_not_applicable(test_class, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory("<main><p>Texte.</p></main>"))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_751_status_message_with_role_status_passes(context_factory, run_rgaa):
    """Test that a status message with role='status' passes."""
    html = '<div role="status">Chargement terminé</div>'
    result = run_rgaa(Test751(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_751_status_message_with_aria_live_polite_and_atomic_true_passes(
    context_factory, run_rgaa,
):
    """Test that a status message with aria-live='polite' and aria-atomic='true' passes."""
    html = '<div aria-live="polite" aria-atomic="true">Sauvegarde réussie</div>'
    result = run_rgaa(Test751(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_751_status_message_without_required_attributes_fails(
    context_factory, run_rgaa,
):
    """Test that a status message without required attributes fails."""
    html = '<div>Chargement terminé</div>'
    result = run_rgaa(Test751(), context_factory(html))

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "n'utilise pas le rôle WAI-ARIA approprié" in result.findings[0].message
    assert result.tested_elements == 1


def test_751_mixed_compliant_and_non_compliant_messages(
    context_factory, run_rgaa,
):
    """Test mixed compliant and non-compliant status messages."""
    html = '''
    <div>
        <div role="status">Chargement terminé</div>
        <div>Sauvegarde réussie</div>
    </div>
    '''
    result = run_rgaa(Test751(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1


def test_752_alert_message_with_role_alert_passes(context_factory, run_rgaa):
    """Test that an alert message with role='alert' passes."""
    html = '<div role="alert">Erreur de validation</div>'
    result = run_rgaa(Test752(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_752_alert_message_with_aria_live_assertive_and_atomic_true_passes(
    context_factory, run_rgaa,
):
    """Test that an alert message with aria-live='assertive' and aria-atomic='true' passes."""
    html = '<div aria-live="assertive" aria-atomic="true">Attention : session expirée</div>'
    result = run_rgaa(Test752(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_752_alert_message_without_required_attributes_fails(
    context_factory, run_rgaa,
):
    """Test that an alert message without required attributes fails."""
    html = '<div>Erreur de validation</div>'
    result = run_rgaa(Test752(), context_factory(html))

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "n'utilise pas le rôle WAI-ARIA approprié" in result.findings[0].message
    assert result.tested_elements == 1


def test_752_mixed_compliant_and_non_compliant_messages(
    context_factory, run_rgaa,
):
    """Test mixed compliant and non-compliant alert messages."""
    html = '''
    <div>
        <div role="alert">Erreur critique</div>
        <div>Problème détecté</div>
    </div>
    '''
    result = run_rgaa(Test752(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1


def test_753_process_message_with_role_log_passes(context_factory, run_rgaa):
    """Test that a process message with role='log' passes."""
    html = '<div role="log">Étape 3 sur 5 terminée</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_753_process_message_with_role_progressbar_passes(
    context_factory, run_rgaa,
):
    """Test that a process message with role='progressbar' passes."""
    html = '<div role="progressbar">Traitement en cours</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_753_process_message_with_role_status_passes(
    context_factory, run_rgaa,
):
    """Test that a process message with role='status' passes."""
    html = '<div role="status">Étape 3 terminée</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_753_process_message_with_aria_live_polite_passes(
    context_factory, run_rgaa,
):
    """Test that a process message with aria-live='polite' passes."""
    html = '<div aria-live="polite">Chargement des données</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_753_process_message_with_aria_live_polite_and_atomic_true_passes(
    context_factory, run_rgaa,
):
    """Test that a process message with aria-live='polite' and aria-atomic='true' passes."""
    html = '<div aria-live="polite" aria-atomic="true">Sauvegarde en cours</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert len(result.findings) == 0


def test_753_process_message_without_required_attributes_fails(
    context_factory,
    run_rgaa,
):
    """Test that a process message without required attributes fails."""
    html = '<div>Étape 3 terminée</div>'
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "n'utilise pas le rôle WAI-ARIA approprié" in result.findings[0].message
    assert result.tested_elements == 1


def test_753_mixed_compliant_and_non_compliant_messages(
    context_factory, run_rgaa,
):
    """Test mixed compliant and non-compliant process messages."""
    html = '''
    <div>
        <div role="log">Étape 3 terminée</div>
        <div>Traitement en cours</div>
    </div>
    '''
    result = run_rgaa(Test753(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1
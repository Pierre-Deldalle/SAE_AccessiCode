import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_4 import (
    Test741,
)
from accessi_code.service.audit_services import AuditServices



def test_741_explicit_button_passes(context_factory, run_rgaa):
    """Test that an explicit button passes 7.4.1."""
    context = context_factory('<button onclick="doSomething()">Click me</button>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_explicit_submit_input_passes(context_factory, run_rgaa):
    """Test that an explicit submit input passes 7.4.1."""
    context = context_factory('<input type="submit" onclick="doSomething()" value="Submit">')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_explicit_button_input_passes(context_factory, run_rgaa):
    """Test that an explicit button input passes 7.4.1."""
    context = context_factory('<input type="button" onclick="doSomething()" value="Click">')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_explicit_image_input_passes(context_factory, run_rgaa):
    """Test that an explicit image input passes 7.4.1."""
    context = context_factory('<input type="image" onclick="doSomething()" src="btn.png" alt="Click">')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_explicit_link_passes(context_factory, run_rgaa):
    """Test that an explicit link passes 7.4.1."""
    context = context_factory('<a href="#" onclick="doSomething()">Link</a>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_explicit_link_with_empty_href_passes(context_factory, run_rgaa):
    """Test that an explicit link with empty href passes 7.4.1."""
    context = context_factory('<a href="" onclick="doSomething()">Link</a>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_element_with_warning_text_passes(context_factory, run_rgaa):
    """Test that an element with warning text passes 7.4.1."""
    context = context_factory('<div onclick="openPopup()">[Cliquez ici pour ouvrir une nouvelle fenêtre]</div>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_element_with_title_warning_passes(context_factory, run_rgaa):
    """Test that an element with title attribute warning passes 7.4.1."""
    context = context_factory('<div onclick="submitForm()" title="Cliquer soumettra le formulaire et ouvrira une nouvelle page">Submit</div>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_element_with_aria_label_warning_passes(context_factory, run_rgaa):
    """Test that an element with aria-label warning passes 7.4.1."""
    context = context_factory('<div onclick="deleteItem()" aria-label="Supprimer l\'élément (action irréversible)"></div>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_element_with_nearby_warning_text_passes(context_factory, run_rgaa):
    """Test that an element with nearby warning text passes 7.4.1."""
    context = context_factory('<div><span>[Attention: cette action ouvre une nouvelle fenêtre]</span><button onclick="openHelp()">Aide</button></div>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_element_without_button_link_or_warning_fails(context_factory, run_rgaa):
    """Test that an element without button/link or warning text fails 7.4.1."""
    context = context_factory('<div onclick="changePage()">Change page</div>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "n'avertit pas l'utilisateur" in result.findings[0].message
    assert "n'est pas initié par un bouton ou un lien explicite" in result.findings[0].message


def test_741_mixed_elements_passes_if_all_compliant(context_factory, run_rgaa):
    """Test that mixed compliant elements result in PASS."""
    html = '''
    <button onclick="save()" title="Enregistrer les données">Save</button>
    <a href="#" onclick="help()" aria-label="Ouvrir l'aide">?</a>
    <div onclick="openModal()">[Cliquez pour ouvrir la boîte de dialogue modal]</div>
    '''
    context = context_factory(html)
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3


def test_741_mixed_elements_fails_if_any_non_compliant(context_factory, run_rgaa):
    """Test that mixed elements with one non-compliant results in FAIL."""
    html = '''
    <button onclick="save()" title="Enregistrer">Save</button>
    <div onclick="deleteItem()">Delete</div>  <!-- No warning text, not button/link -->
    <a href="#" onclick="help()" aria-label="Help">?</a>
    '''
    context = context_factory(html)
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 3


def test_741_no_script_elements_is_not_applicable(context_factory, run_rgaa):
    """Test that absence of script elements results in NOT_APPLICABLE."""
    context = context_factory('<p>Just a paragraph</p><img src="logo.png" alt="Logo">')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


def test_741_onchange_select_with_warning_passes(context_factory, run_rgaa):
    """Test that an onchange select with warning text passes 7.4.1."""
    context = context_factory('<select onchange="loadPage(this.value)"><option value="">-- Sélectionnez une page --</option><option value="page1">Page 1 [ouvre nouvel onglet]</option></select>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_741_onchange_select_without_warning_fails(context_factory, run_rgaa):
    """Test that an onchange select without warning text fails 7.4.1."""
    context = context_factory('<select onchange="loadPage(this.value)"><option value="">-- Sélectionnez --</option><option value="page1">Page 1</option></select>')
    result = run_rgaa(Test741(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1


def test_741_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    import asyncio
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.4.1 nécessite un DOM"):
        asyncio.run(Test741().run(context, AuditServices()))


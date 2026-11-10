from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_1 import (
    Test711,
    Test712,
    Test713,
)
from accessi_code.service.audit_services import AuditServices



def test_711_button_with_accessible_name_passes(context_factory, run_rgaa):
    """Test that a button with aria-label passes 7.1.1."""
    context = context_factory('<button onclick="doSomething()" aria-label="Close">X</button>')
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_711_button_with_inner_text_passes(context_factory, run_rgaa):
    """Test that a button with inner text passes 7.1.1."""
    context = context_factory('<button onclick="doSomething()">Submit</button>')
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_711_link_with_aria_labelledby_passes(context_factory, run_rgaa):
    """Test that a link with aria-labelledby passes 7.1.1."""
    html = '''
    <span id="link-text">Go to home</span>
    <a href="#" onclick="navigateHome()" aria-labelledby="link-text">Home</a>
    '''
    context = context_factory(html)
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_711_custom_widget_with_role_passes(context_factory, run_rgaa):
    """Test that a custom widget with role passes 7.1.1."""
    context = context_factory('<div role="checkbox" aria-checked="false" onclick="toggleCheckbox()"></div>')
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_711_element_without_accessibility_fails(context_factory, run_rgaa):
    """Test that an element without accessibility support fails 7.1.1."""
    context = context_factory('<button onclick="doSomething()"></button>')
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "ne possède pas de support d'accessibilité" in result.findings[0].message


def test_711_mixed_elements_passes_if_all_compliant(context_factory, run_rgaa):
    """Test that mixed compliant elements result in PASS."""
    html = '''
    <button onclick="save()" aria-label="Save">Save</button>
    <div role="tab" onclick="selectTab(1)" aria-selected="true">Tab 1</div>
    <a href="#" onclick="help()" aria-label="Help">?</a>
    '''
    context = context_factory(html)
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3


def test_711_mixed_elements_fails_if_any_non_compliant(context_factory, run_rgaa):
    """Test that mixed elements with one non-compliant results in FAIL."""
    html = '''
    <button onclick="save()" aria-label="Save">Save</button>
    <button onclick="delete()"></button>  <!-- No accessible name (no inner text, no aria-label) -->
    <a href="#" onclick="help()" aria-label="Help">?</a>
    '''
    context = context_factory(html)
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 3


def test_711_no_script_elements_is_not_applicable(context_factory, run_rgaa):
    """Test that absence of script-controlled elements results in NOT_APPLICABLE."""
    context = context_factory('<p>Just a paragraph</p><img src="logo.png" alt="Logo">')
    result = run_rgaa(Test711(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []



def test_712_button_with_accessible_name_passes(context_factory, run_rgaa):
    """Test that a button with accessible name passes 7.1.2."""
    context = context_factory('<button onclick="doSomething()" aria-label="Close">X</button>')
    result = run_rgaa(Test712(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_712_custom_widget_with_role_and_name_passes(context_factory, run_rgaa):
    """Test that a custom widget with role and name passes 7.1.2."""
    context = context_factory('<div role="button" aria-label="Play" onclick="playVideo()"></div>')
    result = run_rgaa(Test712(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_712_element_without_accessibility_fails(context_factory, run_rgaa):
    """Test that an element without accessibility support fails 7.1.2."""
    context = context_factory('<button onclick="doSomething()"></button>')
    result = run_rgaa(Test712(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "n'est pas correctement restitué" in result.findings[0].message


def test_712_no_script_elements_is_not_applicable(context_factory, run_rgaa):
    """Test that absence of script-controlled elements results in NOT_APPLICABLE."""
    context = context_factory('<h1>Title</h1><p>Some text</p>')
    result = run_rgaa(Test712(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []



def test_713_button_with_matching_name_and_role_passes(context_factory, run_rgaa):
    """Test that a button with matching visible label and accessible name passes 7.1.3."""
    context = context_factory('<button onclick="doSomething()">Submit</button>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_713_button_with_aria_label_matching_visible_text_passes(context_factory, run_rgaa):
    """Test that a button with aria-label matching visible text passes 7.1.3."""
    context = context_factory('<button onclick="doSomething()" aria-label="Submit">Submit</button>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_713_icon_button_with_aria_label_passes(context_factory, run_rgaa):
    """Test that an icon-only button with aria-label passes 7.1.3."""
    context = context_factory('<button onclick="playVideo()" aria-label="Play Video"><span aria-hidden="true">▶</span></button>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_713_custom_widget_with_role_and_name_passes(context_factory, run_rgaa):
    """Test that a custom widget with appropriate role and name passes 7.1.3."""
    context = context_factory('<div role="slider" aria-label="Volume" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" onchange="updateVolume()"></div>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_713_button_with_mismatched_name_fails(context_factory, run_rgaa):
    """Test that a button with aria-label not matching visible text fails 7.1.3."""
    context = context_factory('<button onclick="doSomething()" aria-label="Cancel">Submit</button>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "ne possède pas de nom pertinent" in result.findings[0].message


def test_713_element_without_role_or_name_fails(context_factory, run_rgaa):
    """Test that an element without role or accessible name fails 7.1.3."""
    context = context_factory('<button onclick="doSomething()"></button>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "ne possède pas de nom pertinent" in result.findings[0].message or "pas de rôle pertinent" in result.findings[0].message


def test_713_no_script_elements_is_not_applicable(context_factory, run_rgaa):
    """Test that absence of script-controlled elements results in NOT_APPLICABLE."""
    context = context_factory('<p>Just a paragraph</p>')
    result = run_rgaa(Test713(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []



def test_711_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    import asyncio
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.1.1 nécessite un DOM"):
        asyncio.run(Test711().run(context, AuditServices()))


def test_712_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    import asyncio
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.1.2 nécessite un DOM"):
        asyncio.run(Test712().run(context, AuditServices()))


def test_713_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    import asyncio
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.1.3 nécessite un DOM"):
        asyncio.run(Test713().run(context, AuditServices()))
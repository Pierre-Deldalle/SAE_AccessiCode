from __future__ import annotations

from bs4 import BeautifulSoup
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_3 import Test731, Test732


@pytest.mark.asyncio
async def test_731_not_applicable_when_no_script_elements():
    """Test 7.3.1 should return NOT_APPLICABLE when no script elements are present."""
    test = Test731()

    # HTML without any script event handlers
    html_source = "<html><body><h1>Titre</h1><p>Paragraphe</p></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert "Aucun élément avec gestionnaire d'événement script détecté" in result.summary


@pytest.mark.asyncio
async def test_731_pass_when_element_is_keyboard_accessible():
    """Test 7.3.1 should PASS when element is keyboard accessible."""
    test = Test731()

    # HTML with a button (naturally keyboard accessible)
    html_source = "<html><body><button onclick='alert(\"click\")'>Cliquez-moi</button></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.PASS
    assert "1 élément(s) avec gestionnaire d'événement script" in result.summary
    assert "1 conforme(s)" in result.summary
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_731_fail_when_element_not_keyboard_accessible_and_no_equivalent():
    """Test 7.3.1 should FAIL when element is not keyboard accessible and no equivalent exists."""
    test = Test731()

    # HTML with a div that has onclick but is not keyboard accessible
    html_source = "<html><body><div onclick='alert(\"click\")'>Cliquez-moi</div></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.FAIL
    assert "1 élément(s) avec gestionnaire d'événement script" in result.summary
    assert "1 non conforme(s)" in result.summary
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "n'est pas accessible au clavier" in result.findings[0].message


@pytest.mark.asyncio
async def test_731_pass_when_element_has_accessible_equivalent():
    """Test 7.3.1 should PASS when element has an accessible equivalent."""
    test = Test731()

    # HTML with a non-accessible div but an accessible button nearby that does the same thing
    html_source = """
    <html>
        <body>
            <div onclick='alert("click")'>Action 1</div>
            <button>Action 1</button>  <!-- Accessible equivalent -->
        </body>
    </html>
    """
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    # Should pass because we found an accessible equivalent (the button)
    assert result.status == TestStatus.PASS
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_732_not_applicable_when_no_focusable_elements():
    """Test 7.3.2 should return NOT_APPLICABLE when no focusable elements are present."""
    test = Test732()

    # HTML without any focusable elements
    html_source = "<html><body><h1>Titre</h1><p>Paragraphe</p></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.NOT_APPLICABLE
    assert "Aucun élément focusable détecté" in result.summary


@pytest.mark.asyncio
async def test_732_pass_when_no_focus_removal():
    """Test 7.3.2 should PASS when no script removes focus."""
    test = Test732()

    # HTML with a button that doesn't remove focus
    html_source = "<html><body><button onclick='alert(\"click\")'>Cliquez-moi</button></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.PASS
    assert "1 élément(s) focusable" in result.summary
    assert "1 conforme(s)" in result.summary
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_732_fail_when_potential_focus_removal():
    """Test 7.3.2 should FAIL when potential focus removal is detected."""
    test = Test732()

    # HTML with inline blur() call in onblur attribute
    html_source = "<html><body><input onblur='this.blur()' type='text' value='test'></body></html>"
    soup = BeautifulSoup(html_source, "html.parser")

    # Create a mock context
    context = AsyncMock()
    context.dom = soup

    result = await test.run(context)

    assert result.status == TestStatus.FAIL
    assert "1 élément(s) focusable" in result.summary
    assert "1 non conforme(s)" in result.summary
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "supprime le focus" in result.findings[0].message
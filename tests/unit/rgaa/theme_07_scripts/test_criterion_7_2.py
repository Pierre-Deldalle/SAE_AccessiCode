from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_2 import (
    Test721,
    Test722,
)
from accessi_code.service.audit_services import AuditServices



def test_721_script_with_noscript_alternative_passes(context_factory, run_rgaa):
    """Test that a script with noscript alternative passes 7.2.1."""
    html = '''
    <script>
        // Some JavaScript functionality
        function showMessage() {
            alert("Hello");
        }
    </script>
    <noscript>
        <p>JavaScript is disabled. Please enable it to see the full content.</p>
    </noscript>
    '''
    context = context_factory(html)
    result = run_rgaa(Test721(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 1


def test_721_script_without_alternative_not_counted(context_factory, run_rgaa):
    """Test that a script without alternative is not counted in 7.2.1."""
    html = '''
    <script>
        // Some JavaScript functionality
        console.log("Script running");
    </script>
    <p>Some content</p>
    '''
    context = context_factory(html)
    result = run_rgaa(Test721(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


def test_721_multiple_scripts_mixed(context_factory, run_rgaa):
    """Test multiple scripts with mixed alternative presence."""
    html = '''
    <!-- Script with noscript alternative -->
    <script>
        function updateClock() {
            document.getElementById('clock').textContent = new Date().toLocaleTimeString();
        }
    </script>
    <noscript>
        <div id="clock">12:00:00</div>
    </noscript>

    <!-- Script without alternative -->
    <script>
        function trackAnalytics() {
            // Analytics tracking code
        }
    </script>

    <!-- Another script with noscript alternative -->
    <script>
        function validateForm() {
            // Form validation
            return true;
        }
    </script>
    <noscript>
        <p>Please enable JavaScript for form validation.</p>
    </noscript>
    '''
    context = context_factory(html)
    result = run_rgaa(Test721(), context, AuditServices())

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 2


def test_721_script_with_empty_noscript_fails(context_factory, run_rgaa):
    """Test that a script with empty noscript fails 7.2.1."""
    html = '''
    <script>
        function importantFunction() {
            // Critical functionality
        }
    </script>
    <noscript>
        <!-- Empty noscript -->
    </noscript>
    '''
    context = context_factory(html)
    result = run_rgaa(Test721(), context, AuditServices())

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert result.tested_elements == 1
    assert "L'alternative du script ne permet pas d'accéder" in result.findings[0].message


def test_721_no_scripts_is_not_applicable(context_factory, run_rgaa):
    """Test that absence of scripts results in NOT_APPLICABLE."""
    context = context_factory('<h1>Title</h1><p>Just HTML content</p>')
    result = run_rgaa(Test721(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


# ---------------------------------------------------------------------------
# 7.2.2
# ---------------------------------------------------------------------------


def test_722_not_implemented_yet(context_factory, run_rgaa):
    """Test that 7.2.2 returns NOT_APPLICABLE as it's not yet fully implemented."""
    html = '''
    <img id="dynamic-image" src="default.jpg" alt="Default image">
    <script>
        // Script that updates the image source
        function changeImage() {
            document.getElementById('dynamic-image').src = 'new.jpg';
            document.getElementById('dynamic-image').alt = 'New image';
        }
        // Call the function after a delay
        setTimeout(changeImage, 1000);
    </script>
    '''
    context = context_factory(html)
    result = run_rgaa(Test722(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "nécessite un suivi des changements DOM en temps réel" in result.summary





def test_721_missing_html_source_raises_error(context_factory):
    """Test that missing HTML source raises ValueError."""
    context = context_factory("<html><body></body></html>")
    context.html_source = None

    with pytest.raises(ValueError, match="Le test 7.2.1 nécessite la source HTML"):
        import asyncio
        asyncio.run(Test721().run(context, AuditServices()))


def test_722_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.2.2 nécessite un DOM"):
        import asyncio
        asyncio.run(Test722().run(context, AuditServices()))
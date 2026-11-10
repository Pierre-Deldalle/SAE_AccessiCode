from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_2 import (
    Test1021,
    Test1022,
    Test1023,
)


class TestTest1021:
    """Tests for Test1021 - CSS-generated content inspection."""

    @pytest.mark.asyncio
    async def test_no_html_source(self):
        """Test when HTML source is not available."""
        context = Mock(spec=AuditContext)
        context.html_source = None

        test = Test1021()
        result = await test.run(context)

        assert result.status == TestStatus.NOT_TESTED
        assert "code source HTML n'est pas disponible" in result.summary

    @pytest.mark.asyncio
    async def test_no_css_generated_content(self):
        """Test when no CSS-generated content is detected."""
        html_source = """
        <html>
        <head>
            <style>
                .color-red { color: red; }
                .margin-large { margin: 20px; }
            </style>
        </head>
        <body>
            <h1>Title</h1>
            <p class="color-red">Some text</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1021()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "Aucun usage détecté" in result.summary

    @pytest.mark.asyncio
    async def test_pseudo_element_with_content(self):
        """Test detection of pseudo-elements with content property."""
        html_source = """
        <html>
        <head>
            <style>
                .warning::before {
                    content: "Warning: ";
                    color: red;
                }
                .note::after {
                    content: " (see details below)";
                    font-size: 0.8em;
                }
            </style>
        </head>
        <body>
            <h1>Title</h1>
            <p class="warning">This is important</p>
            <p class="note">More information here</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1021()
        result = await test.run(context)

        # Should return NEEDS_REVIEW since we can't automatically determine if the content is essential
        assert result.status == TestStatus.NEEDS_REVIEW
        assert len(result.findings) > 0
        # Check that at least one finding is about pseudo-elements
        pseudo_element_findings = [f for f in result.findings if "pseudo-element" in f.message.lower()]
        assert len(pseudo_element_findings) > 0

    @pytest.mark.asyncio
    async def test_informative_background_image(self):
        """Test detection of potentially informative background images."""
        html_source = """
        <html>
        <head>
            <style>
                .chart-container {
                    background-image: url('sales-chart.png');
                    width: 400px;
                    height: 300px;
                }
                .decorative-bullet {
                    background-image: url('bullet.png');
                    width: 10px;
                    height: 10px;
                }
            </style>
        </head>
        <body>
            <h1>Sales Report</h1>
            <div class="chart-container"></div>
            <ul>
                <li class="decorative-bullet">Item 1</li>
                <li class="decorative-bullet">Item 2</li>
            </ul>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1021()
        result = await test.run(context)

        # Should return NEEDS_REVIEW for the chart image (potentially informative)
        # The bullet might be considered decorative, but our logic flags it as needing review
        assert result.status == TestStatus.NEEDS_REVIEW
        assert "background-image" in str(result.findings).lower()
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_empty_content_pseudo_elements(self):
        """Test that empty content pseudo-elements are handled correctly."""
        html_source = """
        <html>
        <head>
            <style>
                .clearfix::after {
                    content: "";
                    display: table;
                    clear: both;
                }
                .tooltip::before {
                    content: "";
                    position: absolute;
                    border-width: 5px;
                    border-style: solid;
                }
            </style>
        </head>
        <body>
            <div class="clearfix"></div>
            <div class="tooltip">Hover me</div>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1021()
        result = await test.run(context)

        # Empty content should be considered decorative and not flagged
        assert result.status == TestStatus.PASS
        assert "Aucun usage détecté" in result.summary


class TestTest1022:
    """Tests for Test1022 - Information structure and relations."""

    @pytest.mark.asyncio
    async def test_no_dom(self):
        """Test when DOM is not available."""
        context = Mock(spec=AuditContext)
        context.dom = None

        test = Test1022()
        with pytest.raises(ValueError, match="nécessite un DOM"):
            await test.run(context)

    @pytest.mark.asyncio
    async def test_proper_heading_structure(self):
        """Test with proper heading hierarchy."""
        html_source = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Section Title</h2>
            <h3>Subsection Title</h3>
            <p>Some content here.</p>
            <h2>Another Section</h2>
            <p>More content.</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        # We'll need to create a real BeautifulSoup object for this test
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "Aucun problème" in result.summary

    @pytest.mark.asyncio
    async def test_skipped_heading_levels(self):
        """Test detection of skipped heading levels."""
        html_source = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h3>Skipped a level</h3>
            <p>This should be an h2.</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        assert len(result.findings) > 0
        # Check that at least one finding is about heading levels
        heading_findings = [f for f in result.findings if "heading" in f.element.lower() or "titre" in f.message.lower()]
        assert len(heading_findings) > 0

    @pytest.mark.asyncio
    async def test_proper_lists(self):
        """Test with properly used lists."""
        html_source = """
        <html>
        <body>
            <h1>Ingredients</h1>
            <ul>
                <li>2 eggs</li>
                <li>1 cup flour</li>
                <li>1/2 cup sugar</li>
            </ul>
            <h1>Instructions</h1>
            <ol>
                <li>Mix dry ingredients.</li>
                <li>Add eggs and mix well.</li>
                <li>Bake at 350°F for 25 minutes.</li>
            </ol>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "Aucun problème" in result.summary

    @pytest.mark.asyncio
    async def test_empty_list_items(self):
        """Test detection of lists with mostly empty items."""
        html_source = """
        <html>
        <body>
            <ul>
                <li></li>
                <li>   </li>
                <li>&nbsp;</li>
                <li>Real item</li>
                <li></li>
            </ul>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        # With 3 out of 5 items being empty/whitespace, this should trigger the finding
        assert result.status == TestStatus.FAIL
        assert "liste" in str(result.findings).lower()
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_proper_table(self):
        """Test with properly used table for data."""
        html_source = """
        <html>
        <body>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Quantity</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Apple</td>
                        <td>$1.00</td>
                        <td>5</td>
                    </tr>
                    <tr>
                        <td>Banana</td>
                        <td>$0.50</td>
                        <td>10</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "Aucun problème" in result.summary

    @pytest.mark.asyncio
    async def test_layout_table(self):
        """Test detection of table used for layout."""
        html_source = """
        <html>
        <body>
            <table>
                <tr>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td><img src="banner.jpg" alt="Banner"></td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td>Menu</td>
                    <td>&nbsp;</td>
                    <td>Content</td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td colspan="5">&nbsp;</td>
                </tr>
            </table>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1022()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        assert "tableau" in str(result.findings).lower() or "table" in str(result.findings).lower()
        assert len(result.findings) > 0


class TestTest1023:
    """Tests for Test1023 - CSS content hiding inspection."""

    @pytest.mark.asyncio
    async def test_no_html_source(self):
        """Test when HTML source is not available."""
        context = Mock(spec=AuditContext)
        context.html_source = None

        test = Test1023()
        result = await test.run(context)

        assert result.status == TestStatus.NOT_TESTED
        assert "code source HTML n'est pas disponible" in result.summary

    @pytest.mark.asyncio
    async def test_hiding_styles_present(self):
        """Test when content hiding styles are present in CSS (even if not used)."""
        html_source = """
        <html>
        <head>
            <style>
                .visible-box {
                    width: 200px;
                    height: 100px;
                    background-color: blue;
                }
                .hidden-for-accessibility {
                    /* This would be problematic if used, but it's not */
                    position: absolute;
                    left: -9999px;
                }
            </style>
        </head>
        <body>
            <h1>Title</h1>
            <div class="visible-box"></div>
            <!-- The hidden-for-accessibility class is not actually applied -->
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1023()
        result = await test.run(context)

        # Should return NEEDS_REVIEW since hiding CSS rules are present
        # Even if not used, we flag for review as a potential issue
        assert result.status == TestStatus.NEEDS_REVIEW
        findings_str = str(result.findings).lower()
        # Search for lowercase versions since we lowercased the findings string
        has_css_rule = "règle css" in findings_str or "r�gle css" in findings_str
        has_inline_style = "style en ligne" in findings_str
        assert has_css_rule or has_inline_style, f"Expected to find 'règle css' or 'style en ligne' in findings. Findings lowercase: {repr(findings_str)}"
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_inline_display_none(self):
        """Test detection of inline display:none style."""
        html_source = """
        <html>
        <body>
            <h1>Title</h1>
            <p style="display: none;">This text is hidden</p>
            <p>This text is visible</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1023()
        result = await test.run(context)

        # Should return NEEDS_REVIEW since we can't determine if the hidden content is essential
        assert result.status == TestStatus.NEEDS_REVIEW
        assert "style en ligne" in str(result.findings).lower()
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_css_block_hiding(self):
        """Test detection of CSS rules that hide content."""
        html_source = """
        <html>
        <head>
            <style>
                .skip-link {
                    position: absolute;
                    left: -9999px;
                    top: auto;
                    width: 1px;
                    height: 1px;
                    overflow: hidden;
                }
                .hidden-message {
                    visibility: hidden;
                }
                .zero-size {
                    width: 0;
                    height: 0;
                    overflow: hidden;
                }
            </style>
        </head>
        <body>
            <h1>Title</h1>
            <a href="#main-content" class="skip-link">Skip to main content</a>
            <p class="hidden-message">This message is hidden</p>
            <div class="zero-size"></div>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1023()
        result = await test.run(context)

        # Should return NEEDS_REVIEW since we can't determine if the hidden content is essential
        # Note: Current implementation only reports one finding per style block due to breaking after first match
        assert result.status == TestStatus.NEEDS_REVIEW
        findings_str_lower = str(result.findings).lower()
        assert "règle css" in findings_str_lower, f"Expected to find 'règle css' in findings. Findings lowercase: {repr(findings_str_lower)}"
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_text_indent_hiding(self):
        """Test detection of text-indent hiding technique."""
        html_source = """
        <html>
        <head>
            <style>
                .hidden-header {
                    text-indent: -9999px;
                }
            </style>
        </head>
        <body>
            <h1 class="hidden-header">Hidden Header</h1>
            <p>Visible paragraph</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1023()
        result = await test.run(context)

        assert result.status == TestStatus.NEEDS_REVIEW
        assert "text-indent" in str(result.findings).lower()
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_transparent_text(self):
        """Test detection of transparent text (color: transparent)."""
        html_source = """
        <html>
        <head>
            <style>
                .transparent-text {
                    color: transparent;
                    background-color: yellow;
                }
            </style>
        </head>
        <body>
            <h1>Title</h1>
            <p class="transparent-text">This text is invisible</p>
            <p>This text is visible</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        context.html_source = html_source

        test = Test1023()
        result = await test.run(context)

        assert result.status == TestStatus.NEEDS_REVIEW
        assert "transparent" in str(result.findings).lower()
        assert len(result.findings) > 0
from __future__ import annotations

from unittest.mock import Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_2 import (
    Test1021,
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

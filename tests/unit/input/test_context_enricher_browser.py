"""Branchement des preuves navigateur (RGAA 11.4 et 12) dans l'enrichissement."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from accessi_code.input.context_enricher import ContextEnricher
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability

MODULE = "accessi_code.input.context_enricher"


def make_context(tmp_path: Path) -> AuditContext:
    html_path = tmp_path / "index.html"
    html_path.write_text("<!DOCTYPE html><html><body><p>Test</p></body></html>", encoding="utf-8")
    return AuditContext(audit_id="browser", workspace_path=tmp_path, html_path=html_path)


def patched_styles():
    return (
        patch(f"{MODULE}.extract_text_styles", new=AsyncMock(return_value=[])),
        patch(f"{MODULE}.extract_non_text_styles", new=AsyncMock(return_value=[])),
    )


@pytest.mark.asyncio
async def test_collectors_are_called_and_capability_is_available(tmp_path: Path) -> None:
    context = make_context(tmp_path)

    async def navigation(ctx: AuditContext) -> None:
        ctx.navigation_evidence["12.9.1"] = {"no_keyboard_trap": True}

    text_styles, non_text_styles = patched_styles()
    with (
        text_styles,
        non_text_styles,
        patch(f"{MODULE}.collect_navigation_evidence", new=AsyncMock(side_effect=navigation)) as nav,
        patch(f"{MODULE}.collect_form_label_layout", new=AsyncMock()) as layout,
    ):
        report = await ContextEnricher().enrich(context)

    nav.assert_awaited_once_with(context)
    layout.assert_awaited_once_with(context)
    assert report.browser_evidence_error is None
    assert context.browser_evidence_collected is True
    assert context.navigation_evidence == {"12.9.1": {"no_keyboard_trap": True}}
    assert Capability.BROWSER_INTERACTION in context.get_capabilities()


@pytest.mark.asyncio
async def test_collector_failure_is_reported_without_capability(tmp_path: Path) -> None:
    context = make_context(tmp_path)

    async def failing(ctx: AuditContext) -> None:
        ctx.visual_evidence_error = "Navigation Chromium : RuntimeError: aucun navigateur"

    text_styles, non_text_styles = patched_styles()
    with (
        text_styles,
        non_text_styles,
        patch(f"{MODULE}.collect_navigation_evidence", new=AsyncMock(side_effect=failing)),
        patch(f"{MODULE}.collect_form_label_layout", new=AsyncMock()),
    ):
        report = await ContextEnricher().enrich(context)

    assert "aucun navigateur" in report.browser_evidence_error
    assert context.browser_evidence_collected is False
    assert Capability.BROWSER_INTERACTION not in context.get_capabilities()


@pytest.mark.asyncio
async def test_unexpected_collector_exception_is_reported(tmp_path: Path) -> None:
    context = make_context(tmp_path)

    text_styles, non_text_styles = patched_styles()
    with (
        text_styles,
        non_text_styles,
        patch(f"{MODULE}.collect_navigation_evidence", new=AsyncMock(side_effect=OSError("disque"))),
        patch(f"{MODULE}.collect_form_label_layout", new=AsyncMock()),
    ):
        report = await ContextEnricher().enrich(context)

    assert "OSError" in report.browser_evidence_error
    assert context.browser_evidence_collected is False


@pytest.mark.asyncio
async def test_previous_evidence_is_reset(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    context.navigation_evidence = {"12.7.1": {"visible_on_focus": True}}
    context.form_label_layout = {"input[index=0]": {"verified": True}}

    text_styles, non_text_styles = patched_styles()
    with (
        text_styles,
        non_text_styles,
        patch(f"{MODULE}.collect_navigation_evidence", new=AsyncMock()),
        patch(f"{MODULE}.collect_form_label_layout", new=AsyncMock()),
    ):
        await ContextEnricher().enrich(context)

    assert context.navigation_evidence == {}
    assert context.form_label_layout == {}

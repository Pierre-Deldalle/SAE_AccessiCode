from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_1 import Test211 as RGAA211
from accessi_code.service.audit_services import AuditServices


def make_context(html: str) -> SimpleNamespace:
    return SimpleNamespace(dom=BeautifulSoup(html, "html.parser"), html_path=None)


@pytest.mark.asyncio
async def test_211_no_iframe_or_frame_is_not_applicable() -> None:
    result = await RGAA211().run(make_context("<p>Pas de cadre</p>"))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


@pytest.mark.asyncio
async def test_211_all_iframe_with_title_passes() -> None:
    html = """
    <iframe src="video.html" title="Vidéo explicative"></iframe>
    <frame src="menu.html" title="Menu de navigation"></frame>
    """
    result = await RGAA211().run(make_context(html))
    assert result.status == Status.PASS
    assert result.tested_elements == 2
    assert result.findings == []


@pytest.mark.asyncio
async def test_211_iframe_without_title_fails() -> None:
    html = '<iframe src="video.html"></iframe>'
    result = await RGAA211().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "Le cadre ne possède pas d'attribut title." in result.findings[0].message
    assert "iframe" in result.findings[0].element


@pytest.mark.asyncio
async def test_211_frame_without_title_fails() -> None:
    html = '<frame src="menu.html"></frame>'
    result = await RGAA211().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "Le cadre ne possède pas d'attribut title." in result.findings[0].message
    assert "frame" in result.findings[0].element


@pytest.mark.asyncio
async def test_211_mixed_compliant_and_non_compliant_fails() -> None:
    html = """
    <iframe src="video.html" title="Vidéo"></iframe>
    <iframe src="pub.html"></iframe>
    <frame src="nav.html" title="Navigation"></frame>
    """
    result = await RGAA211().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert len(result.findings) == 1  # only one missing title
    assert "pub.html" in result.findings[0].element or "iframe[index=1]" in result.findings[0].element


@pytest.mark.asyncio
async def test_211_without_dom_raises_value_error() -> None:
    # context.dom is not a BeautifulSoup instance
    context = SimpleNamespace(dom=None, html_path=None)
    with pytest.raises(ValueError, match="Le test 2.1.1 nécessite un DOM"):
        await RGAA211().run(context)
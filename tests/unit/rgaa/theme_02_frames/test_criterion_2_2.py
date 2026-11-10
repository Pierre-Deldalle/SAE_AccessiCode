from types import SimpleNamespace
import pytest
from bs4 import BeautifulSoup
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_02_frames.criterion_2_2 import Test221 as RGAA221


def make_context(html: str) -> SimpleNamespace:
    return SimpleNamespace(dom=BeautifulSoup(html, "html.parser"), html_path=None)


@pytest.mark.asyncio
async def test_221_no_frame_with_title_is_not_applicable() -> None:
    html = """
    <iframe src="video.html"></iframe>
    <frame src="menu.html"></frame>
    """
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.findings == []


@pytest.mark.asyncio
async def test_221_all_pertinent_titles_passes() -> None:
    html = """
    <iframe src="video.html" title="Vidéo explicative du produit"></iframe>
    <frame src="menu.html" title="Menu de navigation principal"></frame>
    <iframe src="pub.html" title="Publicité partenaire"></iframe>
    """
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.PASS
    assert result.tested_elements == 3
    assert result.findings == []


@pytest.mark.asyncio
async def test_221_empty_title_fails() -> None:
    html = '<iframe src="video.html" title=""></iframe>'
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "Le titre du cadre «» n'est pas pertinent." in result.findings[0].message
    assert "iframe" in result.findings[0].element


@pytest.mark.asyncio
async def test_221_generic_title_fails() -> None:
    html = '<iframe src="video.html" title="iframe"></iframe>'
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "Le titre du cadre «iframe» n'est pas pertinent." in result.findings[0].message


@pytest.mark.asyncio
async def test_221_whitespace_title_fails() -> None:
    html = '<iframe src="video.html" title="   "></iframe>'
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "Le titre du cadre «   » n'est pas pertinent." in result.findings[0].message


@pytest.mark.asyncio
async def test_221_mixed_pertinent_and_non_pertinent_fails() -> None:
    html = """
    <iframe src="video.html" title="Vidéo du produit"></iframe>
    <iframe src="tracker.html" title="pub"></iframe>
    <frame src="nav.html" title="Menu principal"></frame>
    """
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert len(result.findings) == 1  # only the non-pertinent one
    assert "tracker.html" in result.findings[0].element or "iframe[index=1]" in result.findings[0].element


@pytest.mark.asyncio
async def test_221_frames_without_title_are_ignored() -> None:
    html = """
    <iframe src="video.html" title="Vidéo"></iframe>
    <iframe src="silent.html"></iframe>
    <frame src="menu.html" title="Menu"></frame>
    <frame src="blank"></frame>
    """
    result = await RGAA221().run(make_context(html))
    # Only two frames have title attribute
    assert result.tested_elements == 2
    assert result.status == Status.PASS  # both titles are pertinent
    assert result.findings == []


@pytest.mark.asyncio
async def test_221_case_insensitive_generic_title() -> None:
    html = '<iframe src="video.html" title="IFRAME"></iframe>'
    result = await RGAA221().run(make_context(html))
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert "iframe" in result.findings[0].message.lower()


@pytest.mark.asyncio
async def test_221_without_dom_raises_value_error() -> None:
    context = SimpleNamespace(dom=None, html_path=None)
    with pytest.raises(ValueError, match="Le test 2.2.1 nécessite un DOM"):
        await RGAA221().run(context)
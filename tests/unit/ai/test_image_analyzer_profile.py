import pytest

from accessi_code.ai.analyzers.image_analyzer import OllamaImageAnalyzer
from accessi_code.analysis.images import ImageInfo
from tests.unit.ai.fakes import FakeModel

VISUAL = {"summary": "Graphique des ventes 2025", "important_information": ["hausse de 10 %"], "uncertainties": []}

PROFILE = {
    "information_bearing": True,
    "is_captcha": False,
    "contains_text": True,
    "text_content": "Ventes   2025",
    "needs_detailed_description": True,
    "explanation": "Graphique porteur d'information.",
    "uncertainties": [],
    "confidence": "high",
}


def make_image(**overrides) -> ImageInfo:
    values = {
        "src": "ventes.png",
        "alt": "Ventes",
        "element_html": '<img src="ventes.png" alt="Ventes">',
        "context_text": "Résultats annuels",
        "image_data": b"fake-png",
    }
    values.update(overrides)
    return ImageInfo(**values)


@pytest.mark.asyncio
async def test_profile_reads_every_field() -> None:
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(VISUAL), llm=FakeModel(PROFILE))

    profile = await analyzer.profile(make_image())

    assert profile.information_bearing is True
    assert profile.is_captcha is False
    assert profile.contains_text is True
    assert profile.text_content == "Ventes 2025"
    assert profile.needs_detailed_description is True
    assert profile.confidence == "high"


@pytest.mark.asyncio
async def test_profile_is_computed_once_per_image() -> None:
    vlm, llm = FakeModel(VISUAL), FakeModel(PROFILE)
    analyzer = OllamaImageAnalyzer(vlm=vlm, llm=llm)
    image = make_image()

    first = await analyzer.profile(image)
    second = await analyzer.profile(image)

    assert first == second
    assert vlm.call_count == 1
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_visual_observation_is_shared_between_profile_and_alternative() -> None:
    vlm = FakeModel(VISUAL)
    llm = FakeModel(PROFILE, {"relevant": True, "concise": True, "explanation": "ok", "confidence": "high"})
    analyzer = OllamaImageAnalyzer(vlm=vlm, llm=llm)
    image = make_image()

    await analyzer.profile(image)
    await analyzer.analyze_alternative(
        element_html=image.element_html, alternative="Ventes", context=image.context_text, image=image
    )

    assert vlm.call_count == 1
    assert llm.call_count == 2


@pytest.mark.asyncio
async def test_invalid_flag_raises() -> None:
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(VISUAL), llm=FakeModel({**PROFILE, "is_captcha": "peut-être"}))

    with pytest.raises(ValueError):
        await analyzer.profile(make_image())


@pytest.mark.asyncio
async def test_corrupted_profile_has_no_conclusion() -> None:
    corrupted = {**PROFILE, "explanation": "image image image image image"}
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(VISUAL), llm=FakeModel(corrupted))

    profile = await analyzer.profile(make_image())

    assert profile.information_bearing is None
    assert profile.needs_detailed_description is None
    assert profile.confidence == "low"


@pytest.mark.asyncio
async def test_profile_element_does_not_call_the_vlm() -> None:
    vlm, llm = FakeModel(), FakeModel(PROFILE)
    analyzer = OllamaImageAnalyzer(vlm=vlm, llm=llm)

    profile = await analyzer.profile_element('<svg role="img"><title>Logo</title></svg>', "En-tête")

    assert profile.information_bearing is True
    assert vlm.call_count == 0
    assert '"available": false' in llm.prompts[0]


@pytest.mark.asyncio
async def test_analyze_alternative_without_image_uses_html_only() -> None:
    vlm = FakeModel()
    llm = FakeModel(
        {
            "relevant": False,
            "concise": True,
            "explanation": "Nom de fichier.",
            "missing_information": ["contenu du graphique"],
            "confidence": "medium",
        }
    )
    analyzer = OllamaImageAnalyzer(vlm=vlm, llm=llm)

    analysis = await analyzer.analyze_alternative(
        element_html='<svg role="img" aria-label="graph.svg"></svg>', alternative="graph.svg", context=""
    )

    assert analysis.relevant is False
    assert analysis.concise is True
    assert analysis.missing_information == ["contenu du graphique"]
    assert vlm.call_count == 0
    assert "RGAA 1.3" in llm.prompts[0]


@pytest.mark.asyncio
async def test_analyze_alternative_captcha_mode_uses_rule_1_4() -> None:
    llm = FakeModel({"relevant": True, "concise": True, "explanation": "ok", "confidence": "high"})
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(), llm=llm)

    await analyzer.analyze_alternative(element_html="<img>", alternative="Code de sécurité", context="", mode="captcha")

    assert "RGAA 1.4" in llm.prompts[0]


@pytest.mark.asyncio
async def test_analyze_alternative_is_cached() -> None:
    llm = FakeModel({"relevant": True, "concise": True, "explanation": "ok", "confidence": "high"})
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(), llm=llm)

    for _ in range(2):
        await analyzer.analyze_alternative(element_html="<img>", alternative="Logo", context="")

    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_analyze_alternative_rejects_unknown_mode() -> None:
    analyzer = OllamaImageAnalyzer(vlm=FakeModel(), llm=FakeModel())

    with pytest.raises(ValueError):
        await analyzer.analyze_alternative(element_html="<img>", alternative="x", context="", mode="autre")

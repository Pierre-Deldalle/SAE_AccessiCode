import pytest
from tests.unit.ai.fakes import FakeModel, batch

from accessi_code.ai.analyzers.structure_analyzer import OllamaStructureAnalyzer
from accessi_code.ai.schemas import StructureCandidate


@pytest.mark.asyncio
async def test_classify_candidates() -> None:
    llm = FakeModel(
        batch(
            {"should_be_marked": True, "explanation": "Titre de section.", "confidence": "high"},
            {"should_be_marked": False, "explanation": "Mise en valeur.", "confidence": "medium"},
        )
    )
    analyzer = OllamaStructureAnalyzer(llm)

    results = await analyzer.classify_candidates(
        "heading",
        [StructureCandidate("Nos services"), StructureCandidate("important")],
    )

    assert [result.should_be_marked for result in results] == [True, False]
    assert "RGAA 9.1" in llm.prompts[0]


@pytest.mark.asyncio
async def test_list_and_quote_use_their_own_rules() -> None:
    llm = FakeModel(
        batch({"should_be_marked": None, "explanation": "?", "confidence": "low"}),
        batch({"should_be_marked": None, "explanation": "?", "confidence": "low"}),
    )
    analyzer = OllamaStructureAnalyzer(llm)

    await analyzer.classify_candidates("list", [StructureCandidate("- un\n- deux")])
    await analyzer.classify_candidates("quote", [StructureCandidate("« Je viendrai », a-t-il dit.")])

    assert "RGAA 9.3" in llm.prompts[0]
    assert "RGAA 9.4" in llm.prompts[1]


@pytest.mark.asyncio
async def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        await OllamaStructureAnalyzer(FakeModel()).classify_candidates("table", [StructureCandidate("x")])


@pytest.mark.asyncio
async def test_heading_hierarchy_analysis() -> None:
    llm = FakeModel(
        {
            "relevant": False,
            "explanation": "Le h4 n'est rattaché à aucun h3.",
            "problems": ["h4 – Tarifs : saut depuis h2"],
            "confidence": "high",
        }
    )
    analyzer = OllamaStructureAnalyzer(llm)

    analysis = await analyzer.analyze_heading_hierarchy(
        [(1, "Accueil"), (2, "Nos offres"), (4, "Tarifs")],
        ["h2 → h4 : « Tarifs »"],
    )

    assert analysis.relevant is False
    assert analysis.problems == ["h4 – Tarifs : saut depuis h2"]
    assert "h4 – Tarifs" in llm.prompts[0]
    assert "h2 → h4" in llm.prompts[0]


@pytest.mark.asyncio
async def test_heading_hierarchy_is_cached() -> None:
    llm = FakeModel({"relevant": True, "explanation": "Cohérente.", "confidence": "high"})
    analyzer = OllamaStructureAnalyzer(llm)
    outline = [(1, "Accueil"), (2, "Offres")]

    await analyzer.analyze_heading_hierarchy(outline, [])
    await analyzer.analyze_heading_hierarchy(outline, [])

    assert llm.call_count == 1

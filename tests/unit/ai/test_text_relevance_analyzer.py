import aiohttp
import pytest

from accessi_code.ai.analyzers.text_relevance_analyzer import OllamaTextRelevanceAnalyzer
from accessi_code.ai.prompts.relevance import RELEVANCE_KINDS
from accessi_code.ai.schemas import RelevanceItem
from tests.unit.ai.fakes import FakeModel, batch

RELEVANT = {"relevant": True, "explanation": "Titre explicite.", "confidence": "high"}
NOT_RELEVANT = {"relevant": False, "explanation": "Titre générique.", "problems": ["générique"], "confidence": "high"}


@pytest.mark.asyncio
async def test_returns_one_analysis_per_item_in_order() -> None:
    llm = FakeModel(batch(RELEVANT, NOT_RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    results = await analyzer.analyze_relevance(
        "frame_title",
        [RelevanceItem("Carte du magasin"), RelevanceItem("iframe")],
    )

    assert [result.relevant for result in results] == [True, False]
    assert results[1].problems == ["générique"]
    assert results[0].confidence == "high"
    assert llm.call_count == 1
    assert llm.calls[0]["format"] == "json"
    assert llm.calls[0]["temperature"] == 0


@pytest.mark.asyncio
async def test_prompt_contains_rgaa_rule_and_items() -> None:
    llm = FakeModel(batch(RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    await analyzer.analyze_relevance(
        "link",
        [RelevanceItem("En savoir plus", context="Nos horaires d'ouverture", details={"href": "/horaires"})],
    )

    prompt = llm.prompts[0]
    assert "RGAA 6.1" in prompt
    assert "En savoir plus" in prompt
    assert "/horaires" in prompt


@pytest.mark.asyncio
async def test_items_are_sent_in_batches() -> None:
    llm = FakeModel(batch(RELEVANT, RELEVANT), batch(NOT_RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm, batch_size=2)

    results = await analyzer.analyze_relevance("heading", [RelevanceItem(f"Titre {i}") for i in range(3)])

    assert [result.relevant for result in results] == [True, True, False]
    assert llm.call_count == 2


@pytest.mark.asyncio
async def test_cached_items_are_not_sent_again() -> None:
    llm = FakeModel(batch(RELEVANT), batch(NOT_RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    await analyzer.analyze_relevance("button", [RelevanceItem("Envoyer")])
    results = await analyzer.analyze_relevance("button", [RelevanceItem("Envoyer"), RelevanceItem("Bouton")])

    assert [result.relevant for result in results] == [True, False]
    assert llm.call_count == 2
    # Le second appel ne contient que l'élément non encore analysé.
    assert "Envoyer" not in llm.prompts[1].split("Éléments à évaluer")[1]


@pytest.mark.asyncio
async def test_missing_item_in_response_gives_low_confidence() -> None:
    llm = FakeModel({"results": [{"id": 0, **RELEVANT}]})
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    results = await analyzer.analyze_relevance("heading", [RelevanceItem("A"), RelevanceItem("B")])

    assert results[0].relevant is True
    assert results[1].relevant is None
    assert results[1].confidence == "low"


@pytest.mark.asyncio
async def test_missing_item_is_not_cached() -> None:
    llm = FakeModel({"results": []}, batch(RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    first = await analyzer.analyze_relevance("heading", [RelevanceItem("A")])
    second = await analyzer.analyze_relevance("heading", [RelevanceItem("A")])

    assert first[0].relevant is None
    assert second[0].relevant is True


@pytest.mark.asyncio
async def test_invalid_relevant_value_gives_low_confidence_for_that_item() -> None:
    llm = FakeModel(batch({"relevant": "oui", "explanation": "x", "confidence": "high"}, RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    results = await analyzer.analyze_relevance("heading", [RelevanceItem("A"), RelevanceItem("B")])

    assert results[0].relevant is None
    assert results[0].confidence == "low"
    assert results[1].relevant is True


@pytest.mark.asyncio
async def test_unknown_confidence_becomes_low() -> None:
    llm = FakeModel(batch({"relevant": True, "explanation": "ok", "confidence": "certain"}))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    results = await analyzer.analyze_relevance("heading", [RelevanceItem("A")])

    assert results[0].confidence == "low"


@pytest.mark.asyncio
async def test_corrupted_explanation_cancels_the_conclusion() -> None:
    looping = {"relevant": True, "explanation": "ok ok ok ok ok ok", "confidence": "high"}
    llm = FakeModel(batch(looping))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    results = await analyzer.analyze_relevance("heading", [RelevanceItem("A")])

    assert results[0].relevant is None
    assert results[0].confidence == "low"


@pytest.mark.asyncio
async def test_invalid_json_is_retried_then_raises() -> None:
    llm = FakeModel("pas du json", "toujours pas")
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    with pytest.raises(ValueError):
        await analyzer.analyze_relevance("heading", [RelevanceItem("A")])
    assert llm.call_count == 2


@pytest.mark.asyncio
async def test_response_without_results_list_raises() -> None:
    llm = FakeModel({"relevant": True})
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    with pytest.raises(ValueError):
        await analyzer.analyze_relevance("heading", [RelevanceItem("A")])


@pytest.mark.asyncio
async def test_network_error_is_retried_then_raises_runtime_error() -> None:
    llm = FakeModel(aiohttp.ClientError("coupure"), aiohttp.ClientError("coupure"))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    with pytest.raises(RuntimeError):
        await analyzer.analyze_relevance("heading", [RelevanceItem("A")])
    assert llm.call_count == 2


@pytest.mark.asyncio
async def test_unknown_kind_raises() -> None:
    analyzer = OllamaTextRelevanceAnalyzer(FakeModel())

    with pytest.raises(ValueError):
        await analyzer.analyze_relevance("inconnu", [RelevanceItem("A")])


@pytest.mark.asyncio
async def test_empty_list_does_not_call_the_model() -> None:
    llm = FakeModel()
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    assert await analyzer.analyze_relevance("heading", []) == []
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_suggestion_is_requested_only_for_kinds_that_ask_for_it() -> None:
    llm = FakeModel(batch(RELEVANT), batch(RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    await analyzer.analyze_relevance("frame_title", [RelevanceItem("iframe")])
    await analyzer.analyze_relevance("link", [RelevanceItem("En savoir plus")])

    assert '"suggestion": null' in llm.prompts[0]
    assert "propose dans suggestion un titre de cadre" in llm.prompts[0]
    assert "suggestion" not in llm.prompts[1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "requested"),
    [
        ("table_title", "propose dans suggestion un titre de tableau"),
        ("table_summary", "propose dans suggestion un résumé court"),
        ("layout_table_linearized", None),
    ],
)
async def test_table_kinds_suggestion_request(kind, requested) -> None:
    llm = FakeModel(batch(RELEVANT))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    await analyzer.analyze_relevance(kind, [RelevanceItem("Tableau")])

    if requested:
        assert requested in llm.prompts[0]
        assert '"suggestion": null' in llm.prompts[0]
    else:
        assert "suggestion" not in llm.prompts[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "requested"),
    [
        ("cryptic_context", "propose dans suggestion une alternative courte (texte d'un attribut title)"),
        ("cryptic_alternative", "propose dans suggestion une alternative courte qui donne le sens"),
        # La correction d'un geste ou d'un mouvement est un bouton à ajouter, pas un texte à corriger.
        ("gesture_alternative", None),
        ("motion_alternative", None),
        ("motion_disable", None),
    ],
)
async def test_consultation_kinds_suggestion_request(kind, requested) -> None:
    llm = FakeModel(batch({**NOT_RELEVANT, "suggestion": "à plus tard"}))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    [result] = await analyzer.analyze_relevance(kind, [RelevanceItem("@+")])

    if requested:
        assert requested in llm.prompts[0]
        assert '"suggestion": null' in llm.prompts[0]
        assert result.suggestion == "à plus tard"
    else:
        assert "suggestion" not in llm.prompts[0]


@pytest.mark.asyncio
async def test_heading_kind_requests_a_suggestion() -> None:
    llm = FakeModel(batch({**NOT_RELEVANT, "suggestion": "Horaires d'ouverture"}))
    analyzer = OllamaTextRelevanceAnalyzer(llm)

    [result] = await analyzer.analyze_relevance("heading", [RelevanceItem("Titre")])

    assert "propose dans suggestion un titre court qui décrit le contenu de la section" in llm.prompts[0]
    assert '"suggestion": null' in llm.prompts[0]
    assert result.suggestion == "Horaires d'ouverture"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Plan d'accès   à l'agence ", "Plan d'accès à l'agence"),
        (None, None),
        ("", None),
        (42, None),
        (["Carte"], None),
        ("carte carte carte carte carte", None),
    ],
)
async def test_suggestion_is_read_or_ignored(value, expected) -> None:
    entry = {**NOT_RELEVANT, "suggestion": value}
    analyzer = OllamaTextRelevanceAnalyzer(FakeModel(batch(entry)))

    [result] = await analyzer.analyze_relevance("frame_title", [RelevanceItem("iframe")])

    assert result.relevant is False
    assert result.suggestion == expected


@pytest.mark.asyncio
async def test_missing_suggestion_field_does_not_break_analysis() -> None:
    analyzer = OllamaTextRelevanceAnalyzer(FakeModel(batch(NOT_RELEVANT)))

    [result] = await analyzer.analyze_relevance("frame_title", [RelevanceItem("iframe")])

    assert (result.relevant, result.confidence, result.suggestion) == (False, "high", None)


@pytest.mark.parametrize(
    ("kind", "asks"),
    [
        *[
            (kind, True)
            for kind in (
                "form_label",
                "label_consistency",
                "fieldset_legend",
                "optgroup_label",
                "button",
                "error_identification",
                "format_instruction",
                "error_suggestion_format",
                "error_suggestion_example",
                "autocomplete_value",
            )
        ],
        # Décisions oui / non du thème 11 : aucun texte à proposer.
        *[
            (kind, False)
            for kind in (
                "field_grouping",
                "option_grouping",
                "transaction_scope",
                "sensitive_data_modification",
                "user_data_field",
            )
        ],
    ],
)
def test_form_kinds_ask_for_a_suggestion_only_for_texts(kind, asks) -> None:
    assert bool(RELEVANCE_KINDS[kind].suggestion) is asks

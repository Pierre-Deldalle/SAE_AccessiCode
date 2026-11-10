"""Tests unitaires de l'enrichissement du contexte avec Playwright."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from accessi_code.input.context_enricher import ContextEnricher
from accessi_code.input.extractors.computed_styles import TextStyleObservation
from accessi_code.models.audit_context import AuditContext, UnresolvedTextContrast


def make_context(tmp_path: Path, *, with_html: bool = True) -> AuditContext:
    """Construit un contexte minimal pour les tests."""

    html_path = tmp_path / "index.html" if with_html else None

    if html_path is not None:
        html_path.write_text(
            "<!DOCTYPE html><html><body><p>Test</p></body></html>",
            encoding="utf-8",
        )

    return AuditContext(
        audit_id="test-enricher",
        workspace_path=tmp_path,
        html_path=html_path,
    )


def make_observation(
    *,
    text: str = "Texte de test",
    color: str = "rgb(0, 0, 0)",
    background_color: str | None = "rgb(255, 255, 255)",
    font_size_px: float = 16.0,
    font_weight: int = 400,
    review_reason: str | None = None,
) -> TextStyleObservation:
    """Construit une observation de styles calculés."""

    return TextStyleObservation(
        element="html > body > p",
        text=text,
        color=color,
        background_color=background_color,
        font_size_px=font_size_px,
        font_weight=font_weight,
        review_reason=review_reason,
    )


@pytest.mark.asyncio
async def test_enrich_without_html_returns_error(tmp_path: Path) -> None:
    """Un contexte sans document HTML ne doit pas lancer Playwright."""

    context = make_context(tmp_path, with_html=False)
    enricher = ContextEnricher()

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
    ) as mock_extract:
        report = await enricher.enrich(context)

    assert report.error is not None
    assert "Aucun document HTML" in report.error
    assert report.total == 0
    assert report.usable_count == 0
    assert report.review_count == 0
    mock_extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_classifies_usable_observations(tmp_path: Path) -> None:
    """Une observation simple doit être classée comme candidate."""

    context = make_context(tmp_path)
    observation = make_observation()

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[observation],
    ) as mock_extract:
        report = await ContextEnricher().enrich(context)

    mock_extract.assert_awaited_once_with(context.html_path)

    assert report.error is None
    assert report.total == 1
    assert report.usable_count == 1
    assert report.review_count == 0
    assert report.usable_observations == [observation]


@pytest.mark.asyncio
async def test_enrich_classifies_unknown_background_for_review(
    tmp_path: Path,
) -> None:
    """Un arrière-plan inconnu impose une vérification."""

    context = make_context(tmp_path)
    observation = make_observation(
        background_color=None,
        review_reason="Arrière-plan translucide",
    )

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[observation],
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is None
    assert report.total == 1
    assert report.usable_count == 0
    assert report.review_count == 1
    assert report.review_observations == [observation]


@pytest.mark.asyncio
async def test_enrich_handles_playwright_error(tmp_path: Path) -> None:
    """Un échec du navigateur doit produire un rapport d'erreur."""

    context = make_context(tmp_path)

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Chromium indisponible"),
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is not None
    assert "Chromium indisponible" in report.error
    assert report.total == 0
    assert report.usable_count == 0
    assert report.review_count == 0


@pytest.mark.asyncio
async def test_enrich_populates_context_contrast_samples(
    tmp_path: Path,
) -> None:
    """L'enrichissement alimente le contexte sans présumer l'exhaustivité."""

    context = make_context(tmp_path)
    observation = make_observation()

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[observation],
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is None
    assert report.total == 1
    assert report.sample_count == 1
    assert report.rejected_count == 0

    # Les échantillons sont maintenant publiés dans AuditContext.
    assert len(context.text_contrast_samples) == 1
    assert context.text_contrast_samples == report.text_contrast_samples

    sample = context.text_contrast_samples[0]
    assert sample.element == observation.element
    assert sample.text == observation.text
    assert sample.color == observation.color
    assert sample.background_color == observation.background_color

    # Une extraction réussie ne prouve pas une couverture exhaustive.
    assert context.text_contrast_extraction_attempted is True
    assert context.text_contrast_coverage_complete is False
    assert context.text_contrast_is_partial is True
    assert context.text_contrast_unresolved_count == 0
    assert context.unresolved_text_contrasts == []


@pytest.mark.parametrize(
    ("observation", "expected_review"),
    [
        (make_observation(), False),
        (make_observation(background_color=None), True),
        (make_observation(review_reason="Fond complexe"), True),
        (make_observation(text="  "), True),
        (make_observation(color=""), True),
        (make_observation(font_size_px=0), True),
        (make_observation(font_size_px=float("nan")), True),
        (make_observation(font_size_px=float("inf")), True),
        (make_observation(font_weight=0), True),
    ],
)
def test_requires_review(
    observation: TextStyleObservation,
    expected_review: bool,
) -> None:
    """La classification doit rejeter les observations incomplètes."""

    assert ContextEnricher._requires_review(observation) is expected_review


@pytest.mark.asyncio
async def test_enrich_preserves_rejected_observation_details(
    tmp_path: Path,
) -> None:
    """Les observations rejetées restent disponibles pour une revue humaine."""

    context = make_context(tmp_path)

    valid_observation = make_observation()

    rejected_observation = make_observation(
        background_color=None,
        review_reason="Pseudo-élément susceptible de modifier le rendu",
    )

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[valid_observation, rejected_observation],
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is None
    assert report.total == 2
    assert report.sample_count == 1
    assert report.rejected_count == 1

    # Un seul échantillon est transmis au moteur de contraste.
    assert len(context.text_contrast_samples) == 1
    assert context.text_contrast_samples[0].element == valid_observation.element

    # L'observation ambiguë reste accessible pour une revue humaine.
    assert context.text_contrast_unresolved_count == 1
    assert len(context.unresolved_text_contrasts) == 1

    unresolved = context.unresolved_text_contrasts[0]

    assert isinstance(unresolved, UnresolvedTextContrast)
    assert unresolved.element == rejected_observation.element
    assert unresolved.text == rejected_observation.text
    assert unresolved.reason == ("Pseudo-élément susceptible de modifier le rendu")

    # Même avec un échantillon valide, la couverture reste partielle.
    assert context.text_contrast_extraction_attempted is True
    assert context.text_contrast_coverage_complete is False
    assert context.text_contrast_is_partial is True


@pytest.mark.asyncio
async def test_enrich_preserves_valid_typography_for_rejected_observation(
    tmp_path: Path,
) -> None:
    """Une observation rejetée conserve sa typographie exploitable."""

    context = make_context(tmp_path)

    observation = make_observation(
        text="Nom",
        background_color=None,
        font_size_px=16.0,
        font_weight=400,
        review_reason="Pseudo-élément susceptible de modifier le rendu",
    )

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[observation],
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is None
    assert report.total == 1
    assert report.sample_count == 0
    assert report.rejected_count == 1

    assert context.text_contrast_extraction_attempted is True
    assert context.text_contrast_coverage_complete is False
    assert context.text_contrast_unresolved_count == 1
    assert context.text_contrast_samples == []

    assert len(context.unresolved_text_contrasts) == 1

    unresolved = context.unresolved_text_contrasts[0]

    assert unresolved.element == observation.element
    assert unresolved.text == "Nom"
    assert unresolved.reason == observation.review_reason
    assert unresolved.font_size_px == 16.0
    assert unresolved.font_weight == 400
    assert unresolved.has_valid_typography is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "font_size_px",
        "font_weight",
        "expected_size",
        "expected_weight",
        "expected_valid",
    ),
    [
        (float("nan"), 400, None, 400, False),
        (float("inf"), 400, None, 400, False),
        (-10.0, 700, None, 700, False),
        (0.0, 400, None, 400, False),
        (20.0, 0, 20.0, None, False),
        (20.0, 1001, 20.0, None, False),
        (float("nan"), 0, None, None, False),
    ],
)
async def test_enrich_normalizes_invalid_rejected_typography(
    tmp_path: Path,
    font_size_px: float,
    font_weight: int,
    expected_size: float | None,
    expected_weight: int | None,
    expected_valid: bool,
) -> None:
    """Une typographie invalide est conservée comme inconnue."""

    context = make_context(tmp_path)

    observation = make_observation(
        text="Texte à vérifier",
        background_color=None,
        font_size_px=font_size_px,
        font_weight=font_weight,
        review_reason="Arrière-plan indéterminé",
    )

    with patch(
        "accessi_code.input.context_enricher.extract_text_styles",
        new_callable=AsyncMock,
        return_value=[observation],
    ):
        report = await ContextEnricher().enrich(context)

    assert report.error is None
    assert report.rejected_count == 1
    assert report.sample_count == 0

    assert len(context.unresolved_text_contrasts) == 1

    unresolved = context.unresolved_text_contrasts[0]

    assert unresolved.font_size_px == expected_size
    assert unresolved.font_weight == expected_weight
    assert unresolved.has_valid_typography is expected_valid

    assert context.text_contrast_unresolved_count == 1
    assert context.text_contrast_coverage_complete is False
    assert context.text_contrast_samples == []

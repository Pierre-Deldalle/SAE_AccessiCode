from types import SimpleNamespace
from unittest.mock import AsyncMock

from accessi_code.ai.schemas import DescriptionAnalysis, ImageRoleAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import (
    Test171 as RGAA171,
)
from accessi_code.service.audit_services import AuditServices


def role(
    information_bearing: bool | None,
    *,
    confidence: str = "high",
) -> ImageRoleAnalysis:
    return ImageRoleAnalysis(
        information_bearing=information_bearing,
        explanation="Analyse du rôle simulée.",
        uncertainties=[],
        confidence=confidence,
    )


def description(
    *,
    relevant: bool | None,
    detailed: bool | None = True,
    confidence: str = "high",
    missing_information: list[str] | None = None,
) -> DescriptionAnalysis:
    return DescriptionAnalysis(
        relevant=relevant,
        explanation="Analyse de description simulée.",
        is_detailed_description=detailed,
        missing_information=missing_information or [],
        contradictions=[],
        uncertainties=[],
        confidence=confidence,
    )


def services(
    *,
    role_result: ImageRoleAnalysis,
    description_result: DescriptionAnalysis | None = None,
):
    role_method = AsyncMock(return_value=role_result)
    description_method = AsyncMock(return_value=description_result)

    analyzer = SimpleNamespace(
        analyze_information_role=role_method,
        analyze=description_method,
    )
    return (
        AuditServices(image_analyzer=analyzer),
        role_method,
        description_method,
    )


def html_with_description() -> str:
    return (
        '<img src="graph.png" alt="Graphique" aria-describedby="details">'
        '<p id="details">'
        "Le graphique montre une hausse régulière de janvier à mars."
        "</p>"
    )


def test_171_no_description_candidate_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="graph.png" alt="Graphique">')

    result = run_rgaa(RGAA171(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE


def test_171_non_informative_image_is_outside_scope(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, description_method = services(
        role_result=role(False),
        description_result=description(relevant=True),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.NOT_APPLICABLE
    description_method.assert_not_awaited()


def test_171_uncertain_image_role_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, description_method = services(
        role_result=role(True, confidence="low"),
        description_result=description(relevant=True),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.NEEDS_REVIEW
    description_method.assert_not_awaited()


def test_171_without_image_analyzer_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())

    result = run_rgaa(RGAA171(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_171_detailed_relevant_description_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, _ = services(
        role_result=role(True),
        description_result=description(
            relevant=True,
            detailed=True,
            confidence="high",
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.PASS
    assert result.findings == []


def test_171_detailed_irrelevant_description_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, _ = services(
        role_result=role(True),
        description_result=description(
            relevant=False,
            detailed=True,
            confidence="high",
            missing_information=["valeurs importantes"],
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1


def test_171_candidate_that_is_not_a_detailed_description_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, _ = services(
        role_result=role(True),
        description_result=description(
            relevant=None,
            detailed=False,
            confidence="high",
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.NOT_APPLICABLE


def test_171_low_confidence_description_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, _ = services(
        role_result=role(True),
        description_result=description(
            relevant=True,
            detailed=True,
            confidence="low",
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.NEEDS_REVIEW


def test_171_unknown_relevance_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    audit_services, _, _ = services(
        role_result=role(True),
        description_result=description(
            relevant=None,
            detailed=True,
            confidence="medium",
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.NEEDS_REVIEW


def test_171_missing_longdesc_resource_is_never_passed(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="graph.png" alt="Graphique" longdesc="missing.html">')

    result = run_rgaa(RGAA171(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_171_local_longdesc_can_be_analyzed(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<img src="graph.png" alt="Graphique" longdesc="details.html">',
        resources={"details.html": ("<p>Le graphique progresse de 10 à 20 unités entre janvier et mars.</p>")},
    )
    audit_services, _, description_method = services(
        role_result=role(True),
        description_result=description(
            relevant=True,
            detailed=True,
            confidence="high",
        ),
    )

    result = run_rgaa(RGAA171(), context, audit_services)

    assert result.status == Status.PASS
    description_method.assert_awaited()


def test_171_analyzer_error_is_reported(
    context_factory,
    run_rgaa,
):
    context = context_factory(html_with_description())
    analyzer = SimpleNamespace(
        analyze_information_role=AsyncMock(return_value=role(True)),
        analyze=AsyncMock(side_effect=RuntimeError("IA indisponible")),
    )

    result = run_rgaa(
        RGAA171(),
        context,
        AuditServices(image_analyzer=analyzer),
    )

    assert result.status == Status.ERROR

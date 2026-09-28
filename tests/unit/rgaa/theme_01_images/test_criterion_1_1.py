from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.ai.schemas import ImageRoleAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111 as RGAA111,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test112 as RGAA112,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test113 as RGAA113,
)
from accessi_code.service.audit_services import AuditServices


def role(
    information_bearing: bool | None,
    *,
    confidence: str = "high",
) -> ImageRoleAnalysis:
    return ImageRoleAnalysis(
        information_bearing=information_bearing,
        explanation="Analyse simulée.",
        uncertainties=[],
        confidence=confidence,
    )


def image_services_for_native(*results) -> tuple[AuditServices, AsyncMock]:
    method = AsyncMock(side_effect=list(results))
    analyzer = SimpleNamespace(analyze_information_role=method)
    return AuditServices(image_analyzer=analyzer), method


def image_services_for_role_img(*results) -> tuple[AuditServices, AsyncMock]:
    method = AsyncMock(side_effect=list(results))
    analyzer = SimpleNamespace(analyze_element_information_role=method)
    return AuditServices(image_analyzer=analyzer), method


def image_services_for_areas(*results) -> tuple[AuditServices, AsyncMock]:
    method = AsyncMock(side_effect=list(results))
    analyzer = SimpleNamespace(analyze_area_information_role=method)
    return AuditServices(image_analyzer=analyzer), method


# ---------------------------------------------------------------------------
# 1.1.1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alternative",
    [
        'alt="Logo AccessiCode"',
        'title="Logo AccessiCode"',
        'aria-label="Logo AccessiCode"',
    ],
)
def test_111_informative_img_with_allowed_alternative_passes(
    context_factory,
    run_rgaa,
    alternative,
):
    context = context_factory(f'<img src="logo.png" {alternative}>')
    services, analyzer = image_services_for_native(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.PASS
    assert result.findings == []
    analyzer.assert_awaited_once()


def test_111_informative_img_with_valid_aria_labelledby_passes(
    context_factory,
    run_rgaa,
):
    html = '<span id="logo-label">Logo AccessiCode</span><img src="logo.png" aria-labelledby="logo-label">'
    context = context_factory(html)
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.PASS
    assert result.findings == []


def test_111_informative_img_without_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png">')
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_111_empty_img_alternatives_do_not_count(
    context_factory,
    run_rgaa,
):
    html = '<img src="logo.png" alt="" aria-label="   " title="">'
    context = context_factory(html)
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_111_invalid_aria_labelledby_reference_does_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png" aria-labelledby="missing-label">')
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.FAIL


def test_111_non_informative_img_is_outside_scope(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png">')
    services, _ = image_services_for_native(role(False))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.NOT_APPLICABLE


def test_111_low_confidence_role_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png" alt="Logo">')
    services, _ = image_services_for_native(role(True, confidence="low"))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_111_unknown_role_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png" alt="Logo">')
    services, _ = image_services_for_native(role(None, confidence="medium"))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_111_without_image_analyzer_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png" alt="Logo">')

    result = run_rgaa(RGAA111(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_111_image_analyzer_error_is_reported(
    context_factory,
    run_rgaa,
):
    context = context_factory('<img src="logo.png" alt="Logo">')
    method = AsyncMock(side_effect=RuntimeError("IA indisponible"))
    services = AuditServices(image_analyzer=SimpleNamespace(analyze_information_role=method))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.ERROR


def test_111_role_img_accepts_aria_label(
    context_factory,
    run_rgaa,
):
    context = context_factory('<div role="img" aria-label="Illustration"></div>')
    services, _ = image_services_for_role_img(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.PASS


def test_111_role_img_accepts_aria_labelledby(
    context_factory,
    run_rgaa,
):
    html = '<span id="description">Illustration</span><div role="img" aria-labelledby="description"></div>'
    context = context_factory(html)
    services, _ = image_services_for_role_img(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.PASS


def test_111_role_img_does_not_accept_alt_or_title(
    context_factory,
    run_rgaa,
):
    context = context_factory('<div role="img" alt="Illustration" title="Illustration"></div>')
    services, _ = image_services_for_role_img(role(True))

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.FAIL


def test_111_no_candidate_images_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Aucune image.</p></main>")

    result = run_rgaa(RGAA111(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_111_failure_has_priority_over_review(
    context_factory,
    run_rgaa,
):
    html = """
    <img src="first.png" alt="Première image">
    <img src="second.png">
    <img src="third.png" alt="Troisième image">
    """
    context = context_factory(html)
    services, _ = image_services_for_native(
        role(True),
        role(True),
        role(True, confidence="low"),
    )

    result = run_rgaa(RGAA111(), context, services)

    assert result.status == Status.FAIL


# ---------------------------------------------------------------------------
# 1.1.2
# ---------------------------------------------------------------------------


def image_map(*areas: str) -> str:
    return (
        '<img src="map.png" alt="Plan de navigation" usemap="#navigation">'
        '<map name="navigation">' + "".join(areas) + "</map>"
    )


@pytest.mark.parametrize(
    "alternative",
    [
        'alt="Accueil"',
        'aria-label="Accueil"',
    ],
)
def test_112_informative_area_with_allowed_alternative_passes(
    context_factory,
    run_rgaa,
    alternative,
):
    context = context_factory(image_map(f'<area href="/home" {alternative}>'))
    services, _ = image_services_for_areas(role(True))

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.PASS
    assert result.findings == []


def test_112_informative_area_without_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(image_map('<area href="/home">'))
    services, _ = image_services_for_areas(role(True))

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_112_empty_area_alternatives_do_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory(image_map('<area href="/home" alt="" aria-label=" ">'))
    services, _ = image_services_for_areas(role(True))

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.FAIL


def test_112_non_informative_area_is_outside_scope(
    context_factory,
    run_rgaa,
):
    context = context_factory(image_map('<area href="/home">'))
    services, _ = image_services_for_areas(role(False))

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.NOT_APPLICABLE


def test_112_low_confidence_area_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(image_map('<area href="/home" alt="Accueil">'))
    services, _ = image_services_for_areas(role(True, confidence="low"))

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.NEEDS_REVIEW


def test_112_without_analyzer_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(image_map('<area href="/home" alt="Accueil">'))

    result = run_rgaa(RGAA112(), context, AuditServices())

    assert result.status == Status.NEEDS_REVIEW


def test_112_multiple_areas_failure_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        image_map(
            '<area href="/home" alt="Accueil">',
            '<area href="/contact">',
            '<area href="/help" aria-label="Aide">',
        )
    )
    services, _ = image_services_for_areas(
        role(True),
        role(True),
        role(True, confidence="low"),
    )

    result = run_rgaa(RGAA112(), context, services)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1


def test_112_no_areas_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Aucune zone réactive.</p></main>")

    result = run_rgaa(RGAA112(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 1.1.3
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alternative",
    [
        'alt="Envoyer"',
        'aria-label="Envoyer"',
        'title="Envoyer"',
    ],
)
def test_113_input_image_with_allowed_alternative_passes(
    context_factory,
    run_rgaa,
    alternative,
):
    context = context_factory(f'<input type="image" src="send.png" {alternative}>')

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_113_input_image_with_aria_labelledby_passes(
    context_factory,
    run_rgaa,
):
    html = (
        '<span id="send-label">Envoyer le formulaire</span>'
        '<input type="image" src="send.png" aria-labelledby="send-label">'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.PASS


def test_113_invalid_aria_labelledby_reference_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png" aria-labelledby="missing">')

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.FAIL


def test_113_input_image_without_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png">')

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_113_empty_alternatives_do_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png" alt="" aria-label=" " title="">')

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.FAIL


def test_113_only_input_image_elements_are_checked(
    context_factory,
    run_rgaa,
):
    html = """
    <input type="text" aria-label="Nom">
    <img src="logo.png">
    <input type="image" src="send.png" alt="Envoyer">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_113_multiple_buttons_one_invalid_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <input type="image" src="first.png" alt="Premier">
    <input type="image" src="second.png">
    """
    context = context_factory(html)

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1


def test_113_no_input_image_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<main><input type="submit" value="Envoyer"></main>')

    result = run_rgaa(RGAA113(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bs4 import BeautifulSoup

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
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test114 as RGAA114,
)
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test115 as RGAA115,
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
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

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
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

    assert result.status == Status.PASS


def test_113_invalid_aria_labelledby_reference_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png" aria-labelledby="missing">')
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

    assert result.status == Status.FAIL


def test_113_input_image_without_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png">')
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_113_empty_alternatives_do_not_count(
    context_factory,
    run_rgaa,
):
    context = context_factory('<input type="image" src="send.png" alt="" aria-label=" " title="">')
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

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
    services, _ = image_services_for_native(role(True))

    result = run_rgaa(RGAA113(), context, services)

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
    services, _ = image_services_for_native(role(True), role(True))

    result = run_rgaa(RGAA113(), context, services)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1


def test_113_no_input_image_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<main><input type="submit" value="Envoyer"></main>')
    services = AuditServices()  # No analyzer needed for this case

    result = run_rgaa(RGAA113(), context, services)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


# ---------------------------------------------------------------------------
# 1.1.4
# ---------------------------------------------------------------------------


def test_114_no_server_side_image_map_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
    <img src="logo.png" alt="Logo">
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_114_server_side_image_map_without_alternative_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map.png"
        alt="Carte"
        ismap
    >
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_114_server_side_image_map_with_link_requires_review(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map.png"
        alt="Carte"
        ismap
    >

    <a href="/paris">
        Paris
    </a>
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.findings[0].evidence["alternative_mechanisms"]


def test_114_server_side_image_map_with_select_requires_review(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map.png"
        alt="Carte"
        ismap
    >

    <select>
        <option value="/paris">Paris</option>
        <option value="/lille">Lille</option>
    </select>
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_114_server_side_image_map_with_button_requires_review(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map.png"
        alt="Carte"
        ismap
    >

    <button type="button">
        Paris
    </button>
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_114_empty_link_href_does_not_count(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map.png"
        alt="Carte"
        ismap
    >

    <a href="">
        Paris
    </a>
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.FAIL


def test_114_multiple_maps_one_without_mechanism_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map1.png"
        alt="Première carte"
        ismap
    >

    <a href="/paris">
        Paris
    </a>

    <img
        src="map2.png"
        alt="Deuxième carte"
        ismap
    >
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 2


def test_114_failure_has_priority_over_review(
    context_factory,
    run_rgaa,
):
    html = """
    <img
        src="map1.png"
        alt="Première carte"
        ismap
    >

    <a href="/paris">
        Paris
    </a>

    <img
        src="map2.png"
        alt="Deuxième carte"
        ismap
    >
    """

    context = context_factory(html)

    result = run_rgaa(
        RGAA114(),
        context,
    )

    assert result.status == Status.FAIL
    assert len(result.findings) == 2


def make_context(html: str) -> SimpleNamespace:
    return SimpleNamespace(dom=BeautifulSoup(html, "html.parser"), html_path=None)


def make_analysis(
    information_bearing: bool | None = True,
    confidence: str = "high",
) -> ImageRoleAnalysis:
    return ImageRoleAnalysis(
        information_bearing=information_bearing,
        explanation="Analyse de test",
        confidence=confidence,
        uncertainties=[],
    )


def make_services(analysis: ImageRoleAnalysis | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        image_analyzer=SimpleNamespace(
            analyze_element_information_role=AsyncMock(
                return_value=analysis or make_analysis()
            )
        )
    )


@pytest.mark.asyncio
async def test_1_1_5_without_svg_is_not_applicable() -> None:
    result = await RGAA115().run(make_context("<p>Pas de SVG</p>"))
    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "svg_markup",
    [
        '<svg role="img"><title>Graphique des ventes</title></svg>',
        '<svg role="img" aria-label="Graphique des ventes"></svg>',
        '<span id="svg-label">Graphique des ventes</span>'
        '<svg role="img" aria-labelledby="svg-label"></svg>',
    ],
)
async def test_1_1_5_informative_svg_with_role_and_alternative_passes(
    svg_markup: str,
) -> None:
    services = make_services(make_analysis(information_bearing=True))
    result = await RGAA115().run(make_context(svg_markup), services)

    assert result.status == Status.PASS
    assert result.metadata["compliant_svgs"] == 1
    services.image_analyzer.analyze_element_information_role.assert_awaited_once()


@pytest.mark.asyncio
async def test_1_1_5_informative_svg_without_role_img_fails() -> None:
    services = make_services(make_analysis(information_bearing=True))
    result = await RGAA115().run(
        make_context("<svg><title>Graphique des ventes</title></svg>"), services
    )

    assert result.status == Status.FAIL
    assert result.metadata["failed_svgs"] == 1
    assert 'role="img"' in result.findings[0].message


@pytest.mark.asyncio
async def test_1_1_5_svg_with_role_but_without_alternative_fails() -> None:
    services = make_services(make_analysis(information_bearing=True))
    result = await RGAA115().run(make_context('<svg role="img"><path d="M0 0" /></svg>'), services)

    assert result.status == Status.FAIL
    assert result.metadata["failed_svgs"] == 1
    assert "alternative textuelle" in result.findings[0].message


@pytest.mark.asyncio
async def test_1_1_5_non_informative_svg_is_not_applicable() -> None:
    services = make_services(make_analysis(information_bearing=False))
    result = await RGAA115().run(make_context("<svg><path d='M0 0'/></svg>"), services)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["non_informative_svgs"] == 1


@pytest.mark.asyncio
async def test_1_1_5_low_confidence_requires_manual_review() -> None:
    services = make_services(
        make_analysis(information_bearing=True, confidence="low")
    )
    result = await RGAA115().run(make_context('<svg role="img"><title>Carte</title></svg>'), services)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["needs_review"] == 1


@pytest.mark.asyncio
async def test_1_1_5_without_ai_service_requires_manual_review() -> None:
    result = await RGAA115().run(make_context('<svg role="img"><title>Carte</title></svg>'))

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["needs_review"] == 1


@pytest.mark.asyncio
async def test_1_1_5_ai_exception_is_reported_as_error() -> None:
    analyzer = SimpleNamespace(
        analyze_element_information_role=AsyncMock(side_effect=RuntimeError("IA indisponible"))
    )
    services = SimpleNamespace(image_analyzer=analyzer)
    result = await RGAA115().run(make_context("<svg role='img'><title>Carte</title></svg>"), services)

    assert result.status == Status.ERROR
    assert result.metadata["errors"] == 1
    assert result.findings[0].evidence["error"] == "IA indisponible"


@pytest.mark.asyncio
async def test_1_1_5_visible_svg_text_is_pass_without_ai() -> None:
    html = """
    <div aria-label="Indicateur de conformité de l'audit">
      <svg role="img" aria-labelledby="audit-status-title">
        <title id="audit-status-title">Audit conforme</title>
        <circle cx="42" cy="40" r="18" />
        <text x="75" y="47">Conforme</text>
      </svg>
    </div>
    """
    result = await RGAA115().run(make_context(html))
    assert result.status == Status.PASS
    assert result.metadata["informative_svgs"] == 1
    assert result.metadata["compliant_svgs"] == 1
    assert result.metadata["needs_review"] == 0


@pytest.mark.asyncio
async def test_1_1_5_visible_text_without_role_fails_without_ai() -> None:
    result = await RGAA115().run(
        make_context('<svg><title>Audit conforme</title><text>Conforme</text></svg>')
    )
    assert result.status == Status.FAIL
    assert result.metadata["failed_svgs"] == 1


@pytest.mark.asyncio
async def test_1_1_5_visible_text_without_alternative_fails_without_ai() -> None:
    result = await RGAA115().run(
        make_context('<svg role="img"><text>Conforme</text></svg>')
    )
    assert result.status == Status.FAIL
    assert result.metadata["failed_svgs"] == 1


@pytest.mark.asyncio
async def test_1_1_5_hidden_svg_text_does_not_bypass_ai() -> None:
    result = await RGAA115().run(
        make_context('<svg role="img"><text style="display:none">Secret</text></svg>')
    )
    assert result.status == Status.NEEDS_REVIEW


@pytest.mark.asyncio
async def test_1_1_5_garbled_low_confidence_message_is_not_exposed() -> None:
    analysis = ImageRoleAnalysis(
        information_bearing=True,
        explanation="de-la-de-la-de-la-de-la",
        confidence="low",
        uncertainties=[],
    )
    result = await RGAA115().run(
        make_context('<svg role="img"><title>Graphique</title><path d="M0 0"/></svg>'),
        make_services(analysis),
    )
    assert result.status == Status.NEEDS_REVIEW
    assert "de-la-de-la" not in result.findings[0].message
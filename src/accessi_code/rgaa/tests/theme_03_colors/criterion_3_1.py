"""Contrôles RGAA 3.1 — Information donnée uniquement par la couleur."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


# ---------------------------------------------------------------------------
# Constantes et fonctions communes
# ---------------------------------------------------------------------------

_COLOR_PROPERTIES = frozenset(
    {
        "color",
        "background",
        "background-color",
        "border",
        "border-color",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
        "outline",
        "outline-color",
        "text-decoration-color",
        "fill",
        "stroke",
        "caret-color",
        "accent-color",
        "column-rule-color",
    }
)

_CSS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)

_CSS_DECLARATION_PATTERN = re.compile(
    r"(?:^|;)\s*([a-zA-Z-]+)\s*:",
    re.IGNORECASE,
)

_IMAGE_SELECTOR = "img, svg, canvas, [role='img']"
_TEMPORAL_MEDIA_SELECTOR = "video, audio"
_NON_TEMPORAL_MEDIA_SELECTOR = "object, embed, canvas, svg"


def _element_label(element: Tag) -> str:
    """Construit un identifiant lisible pour un élément HTML."""

    identifier = element.get("id")

    if isinstance(identifier, str) and identifier:
        return f"{element.name}#{identifier}"

    classes = element.get("class")

    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(cls) for cls in classes)}"

    return element.name


def _get_dom(context: AuditContext, test_id: str) -> BeautifulSoup:
    """Récupère le DOM ou signale une incohérence du contexte."""

    if not isinstance(context.dom, BeautifulSoup):
        raise ValueError(f"Le test {test_id} nécessite un DOM.")

    return context.dom


def _has_color_declaration(style: str) -> bool:
    """
    Détecte une propriété CSS liée à la couleur dans un attribut style.

    Cette fonction ne calcule pas la cascade CSS et ne détermine pas
    si la propriété véhicule réellement une information.
    """

    without_comments = _CSS_COMMENT_PATTERN.sub("", style)

    for match in _CSS_DECLARATION_PATTERN.finditer(without_comments):
        property_name = match.group(1).lower()

        if property_name in _COLOR_PROPERTIES:
            return True

    return False


def _elements_with_explicit_color(soup: BeautifulSoup) -> list[Tag]:
    """Retourne les éléments avec une propriété de couleur inline."""

    return [
        element
        for element in soup.find_all(True)
        if isinstance(element.get("style"), str) and _has_color_declaration(element["style"])
    ]


def _select_candidates(soup: BeautifulSoup, selector: str) -> list[Tag]:
    """Sélectionne les éléments candidats correspondant au sélecteur."""

    return list(soup.select(selector))


def _css_metadata(context: AuditContext) -> dict[str, Any]:
    """Décrit les ressources CSS disponibles dans le contexte."""

    return {
        "css_sources_available": bool(context.css_sources),
        "css_files_count": len(context.css_files),
        "computed_styles_available": context.has_capability(Capability.COMPUTED_STYLES),
    }


def _not_applicable(
    test: RGAATest,
    summary: str,
) -> TestResult:
    """Construit un résultat non applicable."""

    return TestResult(
        test_id=test.test_id,
        criterion_id=test.criterion_id,
        status=TestStatus.NOT_APPLICABLE,
        summary=summary,
        tested_elements=0,
    )


def _review_result(
    test: RGAATest,
    *,
    summary: str,
    candidates: list[Tag],
    message: str,
    recommendation: str,
    metadata: dict[str, Any] | None = None,
) -> TestResult:
    """Construit un résultat nécessitant une vérification humaine."""

    findings = [
        Finding(
            element=_element_label(element),
            message=message,
            recommendation=recommendation,
        )
        for element in candidates
    ]

    result_metadata: dict[str, Any] = {
        "candidate_elements": len(candidates),
    }

    if metadata:
        result_metadata.update(metadata)

    return TestResult(
        test_id=test.test_id,
        criterion_id=test.criterion_id,
        status=TestStatus.NEEDS_REVIEW,
        summary=summary,
        findings=findings,
        tested_elements=len(candidates),
        metadata=result_metadata,
    )


def _review_color_test(
    test: RGAATest,
    context: AuditContext,
    *,
    empty_summary: str,
    detected_summary: str,
    message: str,
    recommendation: str,
) -> TestResult:
    """
    Exécute la détection commune des propriétés de couleur inline.

    Le CSS externe est signalé dans les métadonnées mais n'est pas
    considéré comme un ensemble de styles calculés.
    """

    dom = _get_dom(context, test.test_id)
    candidates = _elements_with_explicit_color(dom)

    metadata = {
        "candidate_elements": len(candidates),
        **_css_metadata(context),
    }

    if not candidates:
        return TestResult(
            test_id=test.test_id,
            criterion_id=test.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=empty_summary,
            tested_elements=0,
            metadata=metadata,
        )

    return _review_result(
        test,
        summary=detected_summary,
        candidates=candidates,
        message=message,
        recommendation=recommendation,
        metadata=metadata,
    )


def _review_media_test(
    test: RGAATest,
    context: AuditContext,
    *,
    selector: str,
    empty_summary: str,
    detected_summary: str,
    message: str,
    recommendation: str,
) -> TestResult:
    """Exécute une analyse commune des médias concernés par le RGAA 3.1."""

    dom = _get_dom(context, test.test_id)
    candidates = _select_candidates(dom, selector)

    if not candidates:
        return _not_applicable(test, empty_summary)

    return _review_result(
        test,
        summary=detected_summary,
        candidates=candidates,
        message=message,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Test 3.1.1
# Information par la couleur dans les mots ou ensembles de mots
# ---------------------------------------------------------------------------


class Test311(RGAATest):
    """RGAA 3.1.1 — Information portée par la couleur du texte."""

    test_id = "3.1.1"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    optional_capabilities = frozenset(
        {
            Capability.CSS_SOURCE,
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _review_color_test(
            self,
            context,
            empty_summary=(
                "Aucune mise en couleur inline n'a été détectée. "
                "Les styles appliqués et le rôle informationnel "
                "des couleurs restent à vérifier."
            ),
            detected_summary=(
                "Des éléments possédant des propriétés de couleur "
                "ont été détectés. Il faut vérifier si la couleur "
                "porte une information."
            ),
            message=("Cet élément possède une propriété de couleur inline. Son rôle informationnel doit être vérifié."),
            recommendation=(
                "Si la couleur transmet une information, fournir "
                "également un moyen non fondé uniquement sur la couleur."
            ),
        )


# ---------------------------------------------------------------------------
# Test 3.1.2
# Information par une indication de couleur donnée dans un texte
# ---------------------------------------------------------------------------


class Test312(RGAATest):
    """RGAA 3.1.2 — Indication de couleur dans un texte."""

    test_id = "3.1.2"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        dom = _get_dom(context, self.test_id)

        text = dom.get_text(" ", strip=True)

        if not text:
            return _not_applicable(
                self,
                "Aucun contenu textuel n'est présent dans la page.",
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=(
                "Le contenu textuel doit être analysé pour déterminer "
                "si certaines indications reposent uniquement sur la couleur."
            ),
            findings=[
                Finding(
                    element="document",
                    message=(
                        "Le contenu doit être vérifié afin d'identifier "
                        "les éventuelles indications reposant uniquement "
                        "sur une couleur."
                    ),
                    recommendation=(
                        "Lorsqu'une couleur est utilisée comme indication, "
                        "prévoir également du texte, une forme, une position "
                        "ou un autre moyen de récupérer l'information."
                    ),
                )
            ],
            tested_elements=1,
            metadata={
                "text_present": True,
                "semantic_analysis_required": True,
            },
        )


# ---------------------------------------------------------------------------
# Test 3.1.3
# Information par la couleur dans les images
# ---------------------------------------------------------------------------


class Test313(RGAATest):
    """RGAA 3.1.3 — Information transmise par la couleur d'une image."""

    test_id = "3.1.3"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _review_media_test(
            self,
            context,
            selector=_IMAGE_SELECTOR,
            empty_summary=("Aucune image susceptible de véhiculer une information n'a été détectée."),
            detected_summary=(
                "Des images sont présentes. Une analyse visuelle "
                "est nécessaire pour déterminer si une information "
                "est donnée uniquement par la couleur."
            ),
            message=(
                "La dépendance éventuelle de cette image à la couleur ne peut pas être déterminée à partir du DOM seul."
            ),
            recommendation=(
                "Vérifier que toute information représentée par une couleur reste accessible par un autre moyen."
            ),
        )


# ---------------------------------------------------------------------------
# Test 3.1.4
# Information par la couleur dans les propriétés CSS
# ---------------------------------------------------------------------------


class Test314(RGAATest):
    """RGAA 3.1.4 — Information transmise par une propriété CSS de couleur."""

    test_id = "3.1.4"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    optional_capabilities = frozenset(
        {
            Capability.CSS_SOURCE,
            Capability.COMPUTED_STYLES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _review_color_test(
            self,
            context,
            empty_summary=(
                "Aucune propriété de couleur inline n'a été détectée. "
                "L'analyse des feuilles CSS et des styles effectivement "
                "appliqués reste nécessaire."
            ),
            detected_summary=(
                "Des propriétés CSS liées à la couleur ont été détectées. "
                "Leur éventuel rôle informationnel doit être vérifié."
            ),
            message=("Cet élément possède une déclaration CSS inline liée à la couleur."),
            recommendation=(
                "Si la propriété CSS transmet une information, vérifier qu'un autre moyen permet de la récupérer."
            ),
        )


# ---------------------------------------------------------------------------
# Test 3.1.5
# Information par la couleur dans les médias temporels
# ---------------------------------------------------------------------------


class Test315(RGAATest):
    """RGAA 3.1.5 — Information transmise par la couleur d'un média temporel."""

    test_id = "3.1.5"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _review_media_test(
            self,
            context,
            selector=_TEMPORAL_MEDIA_SELECTOR,
            empty_summary=("Aucun média temporel n'est présent dans la page."),
            detected_summary=("Des médias temporels sont présents. Leur utilisation de la couleur doit être vérifiée."),
            message=(
                "Le média doit être examiné afin de déterminer si une information repose uniquement sur la couleur."
            ),
            recommendation=(
                "Prévoir un autre moyen de transmettre toute information présentée uniquement par la couleur."
            ),
        )


# ---------------------------------------------------------------------------
# Test 3.1.6
# Information par la couleur dans les médias non temporels
# ---------------------------------------------------------------------------


class Test316(RGAATest):
    """RGAA 3.1.6 — Information transmise par un média non temporel."""

    test_id = "3.1.6"
    criterion_id = "3.1"

    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        return _review_media_test(
            self,
            context,
            selector=_NON_TEMPORAL_MEDIA_SELECTOR,
            empty_summary=("Aucun média non temporel concerné n'est présent dans la page."),
            detected_summary=(
                "Des médias non temporels sont présents. Leur utilisation de la couleur doit être vérifiée."
            ),
            message=(
                "Le média doit être examiné afin de déterminer si une information repose uniquement sur la couleur."
            ),
            recommendation=(
                "Prévoir un autre moyen de transmettre toute information présentée uniquement par la couleur."
            ),
        )

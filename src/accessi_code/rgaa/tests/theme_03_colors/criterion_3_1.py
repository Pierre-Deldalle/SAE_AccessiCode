from __future__ import annotations

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


def _element_label(element: Tag) -> str:
    """
    Construit un identifiant lisible pour un élément HTML.
    """
    identifier = element.get("id")

    if identifier:
        return f"{element.name}#{identifier}"

    classes = element.get("class")

    if classes:
        return f"{element.name}.{'.'.join(classes)}"

    return element.name


def _elements_with_explicit_color(soup: BeautifulSoup) -> list[Tag]:
    """
    Retourne les éléments possédant une déclaration de couleur inline.

    Cette détection ne couvre volontairement pas les feuilles de styles
    externes ou les styles calculés par le navigateur.
    """
    elements: list[Tag] = []

    for element in soup.find_all(True):
        style = element.get("style")

        if not isinstance(style, str):
            continue

        declarations = style.lower()

        if (
            "color:" in declarations
            or "background-color:" in declarations
            or "background:" in declarations
            or "border-color:" in declarations
        ):
            elements.append(element)

    return elements


def _image_candidates(soup: BeautifulSoup) -> list[Tag]:
    """
    Retourne les éléments susceptibles de véhiculer une information visuelle.
    """
    return list(
        soup.select(
            "img, svg, canvas, [role='img']",
        )
    )


def _temporal_media_candidates(soup: BeautifulSoup) -> list[Tag]:
    """
    Retourne les médias temporels présents dans le document.
    """
    return list(
        soup.select(
            "video, audio",
        )
    )


def _non_temporal_media_candidates(soup: BeautifulSoup) -> list[Tag]:
    """
    Retourne les médias non temporels autres que les images HTML classiques.
    """
    return list(
        soup.select(
            "object, embed, canvas, svg",
        )
    )


def _review_result(
    test: RGAATest,
    *,
    summary: str,
    candidates: list[Tag],
    message: str,
    recommendation: str,
) -> TestResult:
    """
    Produit un résultat NEEDS_REVIEW commun aux contrôles du critère 3.1.
    """
    findings = [
        Finding(
            element=_element_label(element),
            message=message,
            recommendation=recommendation,
        )
        for element in candidates
    ]

    return TestResult(
        test.test_id,
        test.criterion_id,
        TestStatus.NEEDS_REVIEW,
        summary,
        findings=findings,
        tested_elements=len(candidates),
        metadata={
            "candidate_elements": len(candidates),
        },
    )


class Test311(RGAATest):
    test_id = "3.1.1"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.1 nécessite un DOM.")

        candidates = _elements_with_explicit_color(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                ("Aucune mise en couleur inline n'a été détectée, mais les styles calculés ne sont pas disponibles."),
                tested_elements=0,
                metadata={
                    "candidate_elements": 0,
                    "computed_styles_available": False,
                },
            )

        return _review_result(
            self,
            summary=(
                "Des mots ou ensembles de mots mis en couleur ont été détectés ; "
                "leur rôle informationnel doit être vérifié."
            ),
            candidates=candidates,
            message=(
                "Cet élément utilise explicitement une couleur. "
                "Il faut vérifier si cette couleur véhicule une information."
            ),
            recommendation=(
                "Si la couleur est porteuse d'information, fournir également "
                "un autre moyen de récupérer cette information."
            ),
        )


class Test312(RGAATest):
    test_id = "3.1.2"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.2 nécessite un DOM.")

        text = context.dom.get_text(
            " ",
            strip=True,
        )

        if not text:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun contenu textuel n'est présent dans la page.",
                tested_elements=0,
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (
                "La présence d'une indication reposant uniquement sur une "
                "couleur nécessite une analyse sémantique du contenu."
            ),
            findings=[
                Finding(
                    element="document",
                    message=(
                        "Le contenu textuel doit être vérifié afin d'identifier "
                        "les éventuelles indications reposant uniquement sur "
                        "une couleur."
                    ),
                    recommendation=(
                        "Lorsqu'une couleur est indiquée dans une consigne, "
                        "prévoir également un texte, une forme, une position "
                        "ou un autre moyen permettant de récupérer "
                        "l'information."
                    ),
                )
            ],
            tested_elements=1,
        )


class Test313(RGAATest):
    test_id = "3.1.3"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.3 nécessite un DOM.")

        candidates = _image_candidates(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune image susceptible de véhiculer une information n'a été détectée.",
                tested_elements=0,
            )

        return _review_result(
            self,
            summary=(
                "Des images sont présentes ; une vérification visuelle est "
                "nécessaire pour déterminer si une information est donnée "
                "uniquement par la couleur."
            ),
            candidates=candidates,
            message=(
                "La dépendance éventuelle de cette image à la couleur "
                "ne peut pas être déterminée de manière fiable à partir "
                "du DOM seul."
            ),
            recommendation=(
                "Vérifier qu'une information transmise par la couleur est également disponible par un autre moyen."
            ),
        )


class Test314(RGAATest):
    test_id = "3.1.4"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.4 nécessite un DOM.")

        candidates = _elements_with_explicit_color(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                (
                    "Aucune propriété de couleur inline n'a été détectée, "
                    "mais les styles calculés ne sont pas disponibles."
                ),
                tested_elements=0,
                metadata={
                    "candidate_elements": 0,
                    "computed_styles_available": False,
                },
            )

        return _review_result(
            self,
            summary=(
                "Des propriétés CSS de couleur ont été détectées ; leur éventuel rôle informationnel doit être vérifié."
            ),
            candidates=candidates,
            message=("Cet élément possède une propriété CSS liée à la couleur."),
            recommendation=(
                "Si cette propriété CSS transmet une information, vérifier "
                "qu'un autre moyen permet également de récupérer cette information."
            ),
        )


class Test315(RGAATest):
    test_id = "3.1.5"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.5 nécessite un DOM.")

        candidates = _temporal_media_candidates(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média temporel n'est présent dans la page.",
                tested_elements=0,
            )

        return _review_result(
            self,
            summary=("Des médias temporels sont présents ; leur utilisation de la couleur doit être vérifiée."),
            candidates=candidates,
            message=(
                "Le média doit être examiné afin de déterminer si une information repose uniquement sur la couleur."
            ),
            recommendation=("Prévoir un autre moyen de transmettre toute information présentée par la couleur."),
        )


class Test316(RGAATest):
    test_id = "3.1.6"
    criterion_id = "3.1"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 3.1.6 nécessite un DOM.")

        candidates = _non_temporal_media_candidates(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel concerné n'est présent dans la page.",
                tested_elements=0,
            )

        return _review_result(
            self,
            summary=("Des médias non temporels sont présents ; leur utilisation de la couleur doit être vérifiée."),
            candidates=candidates,
            message=(
                "Le média doit être examiné afin de déterminer si une information repose uniquement sur la couleur."
            ),
            recommendation=("Prévoir un autre moyen de transmettre toute information présentée par la couleur."),
        )

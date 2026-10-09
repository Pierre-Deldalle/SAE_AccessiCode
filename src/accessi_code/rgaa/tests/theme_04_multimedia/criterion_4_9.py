from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.analysis.media import is_media_exempt, media_identifier


class Test491(RGAATest):
    """
    Test 4.9.1

    Pour chaque média non temporel ayant une alternative,
    cette alternative permet-elle d'accéder au même contenu
    et à des fonctionnalités similaires ?

    La pertinence de l'alternative est une vérification sémantique.
    Le test automatique identifie les médias associés à une
    alternative et indique qu'une vérification humaine est nécessaire.
    """

    test_id = "4.9.1"
    criterion_id = "4.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media = [
            tag
            for tag in _find_non_temporal_media(context.dom)
            if not is_media_exempt(tag)
        ]

        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel concerné détecté.",
            )

        findings: list[Finding] = []
        media_with_alternative = 0

        for index, tag in enumerate(media):
            element_id = media_identifier(tag, index)

            controls = _find_adjacent_links_or_buttons(tag)

            identifiable_controls = [
                control
                for control in controls
                if _is_clearly_identifiable(control)
            ]

            alternative_controls = [
                control
                for control in identifiable_controls
                if _has_alternative_destination(control)
            ]

            if not alternative_controls:
                continue

            media_with_alternative += 1

            for control in alternative_controls:
                finding_element = (
                    f"{element_id} -> {_control_identifier(control)}"
                )

                findings.append(
                    Finding(
                        element=finding_element,
                        message=(
                            "Une alternative associée au média "
                            "non temporel a été détectée."
                        ),
                        recommendation=(
                            "Vérifier que l'alternative permet d'accéder "
                            "au même contenu et à des fonctionnalités "
                            "similaires à celles du média."
                        ),
                        evidence={
                            "media_type": tag.name,
                            "media_id": element_id,
                            "alternative_type": control.name,
                            "alternative": _control_information(control),
                            "alternative_detected": True,
                            "relevance_requires_manual_review": True,
                        },
                    )
                )

        if media_with_alternative == 0:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                (
                    f"{len(media)} média(s) non temporel(s) détecté(s), "
                    "mais aucun n'est associé à une alternative."
                ),
                tested_elements=len(media),
                metadata={
                    "candidate_media": len(media),
                    "media_with_alternative": 0,
                    "media_without_alternative": len(media),
                },
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (
                f"{media_with_alternative} média(s) non temporel(s) "
                "avec alternative nécessitent une vérification "
                "de la pertinence de leur alternative."
            ),
            findings=findings,
            tested_elements=media_with_alternative,
            metadata={
                "candidate_media": len(media),
                "media_with_alternative": media_with_alternative,
                "media_without_alternative": (
                    len(media) - media_with_alternative
                ),
                "relevance_requires_manual_review": True,
            },
        )


def _find_non_temporal_media(dom: BeautifulSoup) -> list[Tag]:
    """
    Recherche les médias non temporels concernés par le critère 4.9.

    Les éléments <audio> et <video> sont exclus car ils correspondent
    aux médias temporels.

    Les éléments principalement concernés ici sont :
    - <object>
    - <embed>
    """

    return list(dom.find_all(["object", "embed"]))


def _find_adjacent_links_or_buttons(tag: Tag) -> list[Tag]:
    """
    Recherche les liens et boutons immédiatement adjacents au média.

    Les espaces et retours à la ligne entre les éléments sont ignorés.
    """

    controls: list[Tag] = []

    previous = tag.previous_sibling

    while previous is not None:
        if isinstance(previous, Tag):
            if previous.name in {"a", "button"}:
                controls.append(previous)
            break

        previous = previous.previous_sibling

    following = tag.next_sibling

    while following is not None:
        if isinstance(following, Tag):
            if following.name in {"a", "button"}:
                controls.append(following)
            break

        following = following.next_sibling

    return controls


def _is_clearly_identifiable(tag: Tag) -> bool:
    """
    Vérifie que le lien ou bouton possède un intitulé identifiable.
    """

    text = tag.get_text(" ", strip=True)

    if text:
        return True

    aria_label = tag.get("aria-label")

    if isinstance(aria_label, str) and aria_label.strip():
        return True

    aria_labelledby = tag.get("aria-labelledby")

    if isinstance(aria_labelledby, str) and aria_labelledby.strip():
        return True

    title = tag.get("title")

    if isinstance(title, str) and title.strip():
        return True

    return False


def _has_alternative_destination(tag: Tag) -> bool:
    """
    Vérifie qu'un lien ou bouton possède une destination
    correspondant à une alternative.

    Cette fonction ne vérifie pas la pertinence de l'alternative.
    Cette vérification constitue précisément l'objet du test 4.9.1.
    """

    if tag.name == "a":
        href = tag.get("href")

        return (
            isinstance(href, str)
            and bool(href.strip())
            and href.strip() != "#"
        )

    if tag.name == "button":
        for attribute in (
            "aria-controls",
            "data-target",
            "data-bs-target",
            "data-target-id",
        ):
            value = tag.get(attribute)

            if isinstance(value, str) and value.strip():
                return True

        data_href = tag.get("data-href")

        if isinstance(data_href, str) and data_href.strip():
            return True

        return False

    return False


def _control_information(tag: Tag) -> dict[str, Any]:
    """
    Extrait les informations utiles concernant l'alternative.
    """

    information: dict[str, Any] = {
        "tag": tag.name,
        "text": tag.get_text(" ", strip=True),
    }

    for attribute in (
        "href",
        "aria-label",
        "aria-labelledby",
        "title",
        "aria-controls",
        "data-target",
        "data-bs-target",
        "data-target-id",
        "data-href",
    ):
        value = tag.get(attribute)

        if value is not None:
            information[attribute] = str(value)

    return information


def _control_identifier(tag: Tag) -> str:
    """
    Génère un identifiant lisible pour le contrôle associé.
    """

    tag_id = tag.get("id")

    if isinstance(tag_id, str) and tag_id.strip():
        return f"{tag.name}#{tag_id}"

    return tag.name



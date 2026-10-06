from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test481(RGAATest):
    """
    Test 4.8.1

    Chaque média non temporel possède-t-il un lien ou bouton
    adjacent clairement identifiable permettant d'accéder
    à une alternative ?
    """

    test_id = "4.8.1"
    criterion_id = "4.8"
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
            if not _is_exempt_or_decorative(tag)
        ]

        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel concerné détecté.",
            )

        findings: list[Finding] = []
        all_valid = True

        for index, tag in enumerate(media):
            element_id = _media_identifier(tag, index)

            controls = _find_adjacent_links_or_buttons(tag)

            identifiable_controls = [
                control
                for control in controls
                if _is_clearly_identifiable(control)
            ]

            valid_controls = [
                control
                for control in identifiable_controls
                if _has_alternative_destination(control)
            ]

            has_alternative = bool(valid_controls)

            if not has_alternative:
                all_valid = False

            findings.append(
                Finding(
                    element=element_id,
                    message=(
                        "Un lien ou bouton adjacent clairement identifiable "
                        "permettant d'accéder à une alternative a été détecté."
                        if has_alternative
                        else
                        "Aucun lien ou bouton adjacent clairement "
                        "identifiable permettant d'accéder à une "
                        "alternative n'a été détecté."
                    ),
                    recommendation=(
                        "Vérifier que le lien ou bouton permet bien "
                        "d'accéder à l'alternative du média."
                        if has_alternative
                        else
                        "Ajouter immédiatement avant ou après le média "
                        "un lien ou un bouton clairement identifiable "
                        "permettant d'accéder à une alternative."
                    ),
                    evidence={
                        "media_type": tag.name,
                        "adjacent_controls": len(controls),
                        "identifiable_controls": len(
                            identifiable_controls
                        ),
                        "valid_controls": len(valid_controls),
                        "has_alternative": has_alternative,
                        "controls": [
                            _control_information(control)
                            for control in identifiable_controls
                        ],
                    },
                )
            )

        if all_valid:
            status = TestStatus.PASS
            message = (
                f"{len(media)} média(s) non temporel(s) possèdent "
                "un lien ou bouton adjacent clairement identifiable "
                "permettant d'accéder à une alternative."
            )
        else:
            status = TestStatus.FAIL
            message = (
                f"{len(media)} média(s) non temporel(s) ne possèdent "
                "pas tous un lien ou bouton adjacent permettant "
                "d'accéder à une alternative."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            message,
            findings=findings,
            tested_elements=len(media),
            metadata={
                "candidate_media": len(media),
                "media_with_alternative": sum(
                    1
                    for finding in findings
                    if finding.evidence.get("has_alternative") is True
                ),
                "media_without_alternative": sum(
                    1
                    for finding in findings
                    if finding.evidence.get("has_alternative") is False
                ),
            },
        )


class Test482(RGAATest):
    """
    Test 4.8.2

    Chaque média non temporel associé à une alternative
    possède-t-il une destination permettant d'accéder
    à cette alternative ?
    """

    test_id = "4.8.2"
    criterion_id = "4.8"
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
            if not _is_exempt_or_decorative(tag)
        ]

        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel concerné détecté.",
            )

        findings: list[Finding] = []
        all_valid = True

        for index, tag in enumerate(media):
            element_id = _media_identifier(tag, index)

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

            has_destination = bool(alternative_controls)

            if not has_destination:
                all_valid = False

            findings.append(
                Finding(
                    element=element_id,
                    message=(
                        "Une destination d'alternative exploitable "
                        "a été identifiée."
                        if has_destination
                        else
                        "Aucune destination d'alternative exploitable "
                        "n'a été identifiée."
                    ),
                    recommendation=(
                        "Vérifier que la destination permet réellement "
                        "d'accéder à l'alternative du média."
                    ),
                    evidence={
                        "media_type": tag.name,
                        "adjacent_controls": len(controls),
                        "identifiable_controls": len(
                            identifiable_controls
                        ),
                        "alternative_controls": len(
                            alternative_controls
                        ),
                        "has_alternative_destination": has_destination,
                        "controls": [
                            _control_information(control)
                            for control in identifiable_controls
                        ],
                    },
                )
            )

        if all_valid:
            status = TestStatus.PASS
            message = (
                f"{len(media)} média(s) non temporel(s) associé(s) "
                "à une destination d'alternative exploitable."
            )
        else:
            status = TestStatus.FAIL
            message = (
                f"{len(media)} média(s) non temporel(s) ne disposent "
                "pas tous d'une destination d'alternative exploitable."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            message,
            findings=findings,
            tested_elements=len(media),
            metadata={
                "candidate_media": len(media),
                "media_with_destination": sum(
                    1
                    for finding in findings
                    if finding.evidence.get(
                        "has_alternative_destination"
                    ) is True
                ),
                "media_without_destination": sum(
                    1
                    for finding in findings
                    if finding.evidence.get(
                        "has_alternative_destination"
                    ) is False
                ),
            },
        )


def _find_non_temporal_media(dom: BeautifulSoup) -> list[Tag]:
    """
    Recherche les médias non temporels concernés par le RGAA 4.8.

    Les éléments <audio> et <video> sont exclus car ils correspondent
    aux médias temporels traités par les autres tests du thème 4.

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
    Vérifie qu'un lien ou bouton possède une destination exploitable.
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
    Extrait les informations utiles concernant un lien ou bouton.
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


def _is_exempt_or_decorative(tag: Tag) -> bool:
    """
    Exclut les médias explicitement décoratifs ou masqués.
    """

    if tag.get("aria-hidden") == "true":
        return True

    if tag.get("role") in {"presentation", "none"}:
        return True

    decorative = tag.get("data-decorative")

    if isinstance(decorative, str):
        return decorative.strip().lower() in {
            "true",
            "1",
            "yes",
        }

    return False


def _media_identifier(tag: Tag, index: int) -> str:
    """
    Génère un identifiant stable pour le finding.
    """

    media_id = tag.get("id")

    if isinstance(media_id, str) and media_id.strip():
        return f"{tag.name}#{media_id}"

    return f"{tag.name}[index={index}]"
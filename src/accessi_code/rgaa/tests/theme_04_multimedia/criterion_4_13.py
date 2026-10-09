from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.media import find_adjacent_media_alternatives, is_media_exempt, media_identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

_MEDIA_TAGS = frozenset({"audio", "video", "svg", "canvas", "object", "embed"})
_ACCESSIBLE_MEDIA_ROLES = frozenset({"application", "document", "graphics-document", "group", "img"})


def _find_media(soup: BeautifulSoup) -> list[Tag]:
    return [tag for tag in soup.find_all(list(_MEDIA_TAGS)) if isinstance(tag, Tag) and not is_media_exempt(tag)]


def _has_accessible_name(tag: Tag, soup: BeautifulSoup) -> bool:
    aria_label = tag.get("aria-label")
    if isinstance(aria_label, str) and aria_label.strip():
        return True

    labelledby = tag.get("aria-labelledby")
    if isinstance(labelledby, str):
        for reference in labelledby.split():
            target = soup.find(id=reference)
            if target and target.get_text(" ", strip=True):
                return True

    title = tag.find("title") if tag.name == "svg" else None
    return bool(
        (isinstance(tag.get("title"), str) and tag.get("title", "").strip())
        or (title and title.get_text(" ", strip=True))
    )


def _has_accessible_interface(tag: Tag, soup: BeautifulSoup) -> bool:
    if tag.name in {"audio", "video"} and tag.has_attr("controls"):
        return True

    role = str(tag.get("role", "")).lower()
    if role in _ACCESSIBLE_MEDIA_ROLES and _has_accessible_name(tag, soup):
        return True

    return tag.name in {"canvas", "object", "embed"} and bool(tag.get_text(" ", strip=True))




def _referenced_alternative(tag: Tag, soup: BeautifulSoup) -> bool:
    for attribute in ("aria-describedby", "aria-details"):
        references = tag.get(attribute)
        if not isinstance(references, str):
            continue
        for reference in references.split():
            target = soup.find(id=reference)
            if target and target.get_text(" ", strip=True):
                return True
    return False


def _alternative_is_adjacent(tag: Tag, soup: BeautifulSoup) -> bool:
    adjacent = find_adjacent_media_alternatives(tag)
    if adjacent.links_or_buttons or adjacent.text_candidates:
        return True

    if tag.name in {"canvas", "object", "embed"} and tag.get_text(" ", strip=True):
        return True

    media_id = tag.get("id")
    if not isinstance(media_id, str) or not media_id:
        return False

    for button in soup.find_all(["a", "button"]):
        references = button.get("aria-controls")
        if isinstance(references, str) and media_id in references.split() and button.get_text(" ", strip=True):
            return True

    return False


class Test4131(RGAATest):
    test_id = "4.13.1"
    criterion_id = "4.13"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media = _find_media(context.dom)
        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média temporel ou non temporel détecté.",
            )

        findings: list[Finding] = []
        accessible_count = 0

        for index, tag in enumerate(media):
            accessible_interface = _has_accessible_interface(tag, context.dom)
            accessible_alternative = _referenced_alternative(tag, context.dom) or _alternative_is_adjacent(
                tag, context.dom
            )
            accessible = accessible_interface or accessible_alternative
            accessible_count += int(accessible)
            findings.append(
                Finding(
                    element=media_identifier(tag, index),
                    message=(
                        "Une interface ou une alternative avec des marqueurs d'accessibilité a été détectée."
                        if accessible
                        else "Aucun marqueur d'interface accessible ou d'alternative n'a été détecté."
                    ),
                    recommendation=(
                        None
                        if accessible
                        else (
                            "Exposer l'interface du média aux technologies d'assistance "
                            "ou fournir une alternative compatible."
                        )
                    ),
                    evidence={
                        "tag": tag.name,
                        "native_controls": tag.name in {"audio", "video"} and tag.has_attr("controls"),
                        "role": tag.get("role"),
                        "accessible_name": _has_accessible_name(tag, context.dom),
                        "accessible_alternative": accessible_alternative,
                    },
                )
            )

        status = TestStatus.PASS if accessible_count == len(media) else TestStatus.FAIL
        # Determine explicit descriptive message
        if status == TestStatus.PASS:
            status_message = (
                f"Conforme : Tous les {len(media)} média(s) présentent des marqueurs d'accessibilité."
            )
        else:  # TestStatus.FAIL
            inaccessible_count = len(media) - accessible_count
            status_message = (
                f"Non conforme : {inaccessible_count} média(s) sur {len(media)} "
                "n présentent pas de marqueurs d'accessibilité suffisants."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            status_message,
            findings=findings,
            tested_elements=len(media),
            metadata={
                "candidate_media": len(media),
                "accessible_media": accessible_count,
            },
        )


class Test4132(RGAATest):
    test_id = "4.13.2"
    criterion_id = "4.13"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media = _find_media(context.dom)
        with_alternatives = [
            (index, tag)
            for index, tag in enumerate(media)
            if _referenced_alternative(tag, context.dom) or _alternative_is_adjacent(tag, context.dom)
        ]

        if not with_alternatives:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média avec une alternative détectable.",
            )

        findings: list[Finding] = []
        adjacent_count = 0

        for index, tag in with_alternatives:
            adjacent = _alternative_is_adjacent(tag, context.dom)
            adjacent_count += int(adjacent)
            findings.append(
                Finding(
                    element=media_identifier(tag, index),
                    message=(
                        "Une alternative adjacente ou un mécanisme de remplacement a été détecté."
                        if adjacent
                        else "Une alternative référencée existe, mais elle n'est pas adjacente au média."
                    ),
                    recommendation=(
                        None
                        if adjacent
                        else (
                            "Rendre l'alternative adjacente, accessible via un lien "
                            "ou bouton adjacent, ou prévoir un mécanisme de remplacement."
                        )
                    ),
                    evidence={
                        "referenced_alternative": _referenced_alternative(tag, context.dom),
                        "alternative_adjacent": adjacent,
                    },
                )
            )

        status = TestStatus.PASS if adjacent_count == len(with_alternatives) else TestStatus.FAIL
        # Determine explicit status message
        if status == TestStatus.PASS:
            status_message = (
                f"Conforme : {adjacent_count}/{len(with_alternatives)} alternative(s) sont "
                "adjacentes ou accessibles par un mécanisme détecté."
            )
        else:  # TestStatus.FAIL
            status_message = (
                f"Non conforme : {len(with_alternatives) - adjacent_count}/{len(with_alternatives)} alternative(s) "
                "ne sont pas adjacentes ou accessibles par un mécanisme détecté."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            status_message,
            findings=findings,
            tested_elements=len(with_alternatives),
            metadata={
                "candidate_media": len(media),
                "media_with_alternatives": len(with_alternatives),
                "adjacent_alternatives": adjacent_count,
            },
        )

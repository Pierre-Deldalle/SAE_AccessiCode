from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.media import (
    find_temporal_media,
    is_media_exempt,
    media_identifier,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test471(RGAATest):
    test_id = "4.7.1"
    criterion_id = "4.7"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        # Recherche de tous les médias temporels :
        # - audio
        # - vidéo
        # - autres médias identifiés par find_temporal_media
        #
        # Les médias décoratifs sont exclus du test.
        media = [
            item
            for item in find_temporal_media(context.dom)
            if not is_media_exempt(item.tag)
        ]

        # Aucun média temporel :
        # le critère ne s'applique pas.
        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média temporel détecté.",
            )

        findings: list[Finding] = []
        all_identified = True

        for item in media:
            tag = item.tag
            element_id = media_identifier(tag, item.index)

            # Recherche du contenu textuel immédiatement avant
            # ou immédiatement après le média.
            preceding_text = _find_adjacent_text_before(tag)
            following_text = _find_adjacent_text_after(tag)

            has_preceding_text = bool(preceding_text)
            has_following_text = bool(following_text)

            has_identifying_text = (
                has_preceding_text or has_following_text
            )

            if not has_identifying_text:
                all_identified = False

            findings.append(
                Finding(
                    element=element_id,
                    message=(
                        "Un contenu textuel adjacent a été détecté."
                        if has_identifying_text
                        else
                        "Aucun contenu textuel adjacent permettant "
                        "d'identifier le média temporel n'a été détecté."
                    ),
                    recommendation=(
                        "Vérifier que le contenu textuel adjacent "
                        "identifie clairement le média temporel."
                        if has_identifying_text
                        else
                        "Ajouter un contenu textuel, par exemple "
                        "un titre ou un paragraphe, immédiatement "
                        "avant ou après le média afin de permettre "
                        "son identification."
                    ),
                    evidence={
                        "media_type": item.kind,
                        "preceding_text": preceding_text,
                        "following_text": following_text,
                        "has_preceding_text": has_preceding_text,
                        "has_following_text": has_following_text,
                        "media_identified": has_identifying_text,
                    },
                )
            )

        # Niveau 1 :
        # le test doit uniquement déterminer si le critère est
        # conforme ou non conforme.
        if all_identified:
            status = TestStatus.PASS
            message = (
                f"{len(media)} média(s) temporel(s) possèdent "
                "un contenu textuel adjacent permettant "
                "leur identification."
            )
        else:
            status = TestStatus.FAIL
            message = (
                f"{len(media)} média(s) temporel(s) ont été détectés, "
                "mais au moins un média ne possède pas de contenu "
                "textuel adjacent permettant son identification."
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
                "identified_media": sum(
                    1
                    for finding in findings
                    if finding.evidence.get("media_identified") is True
                ),
                "unidentified_media": sum(
                    1
                    for finding in findings
                    if finding.evidence.get("media_identified") is False
                ),
            },
        )


def _find_adjacent_text_before(tag: Tag) -> str:
    """
    Recherche un contenu textuel immédiatement avant le média.

    Les espaces et retours à la ligne sont ignorés.
    """

    previous = tag.previous_sibling

    while previous is not None:
        # Texte directement présent entre deux éléments HTML.
        if isinstance(previous, NavigableString):
            text = str(previous).strip()

            if text:
                return text

        # Élément HTML adjacent.
        elif isinstance(previous, Tag):
            text = _extract_identifying_text(previous)

            if text:
                return text

            # Un élément HTML vide ou sans contenu textuel
            # arrête la recherche.
            return ""

        previous = previous.previous_sibling

    return ""


def _find_adjacent_text_after(tag: Tag) -> str:
    """
    Recherche un contenu textuel immédiatement après le média.

    Les espaces et retours à la ligne sont ignorés.
    """

    following = tag.next_sibling

    while following is not None:
        # Texte directement présent entre deux éléments HTML.
        if isinstance(following, NavigableString):
            text = str(following).strip()

            if text:
                return text

        # Élément HTML adjacent.
        elif isinstance(following, Tag):
            text = _extract_identifying_text(following)

            if text:
                return text

            # Un élément HTML vide ou sans contenu textuel
            # arrête la recherche.
            return ""

        following = following.next_sibling

    return ""


def _extract_identifying_text(tag: Tag) -> str:
    """
    Extrait le contenu textuel d'un élément HTML.
    """

    # Ces éléments ne constituent pas du contenu textuel
    # pertinent pour identifier le média.
    if tag.name in {"script", "style", "template"}:
        return ""

    return tag.get_text(" ", strip=True)



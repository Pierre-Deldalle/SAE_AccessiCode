from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.media import (
    find_adjacent_media_alternatives,
    find_temporal_media,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class _Criterion45Test(RGAATest):
    required_capabilities = frozenset({Capability.DOM})
    media_description: str

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        videos = [
            item
            for item in find_temporal_media(context.dom)
            if item.kind == "video" and not _is_exempt_or_decorative(item.tag)
        ]

        if not videos:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                f"Aucun média vidéo {self.media_description} détecté.",
            )

        findings: list[Finding] = []

        for item in videos:
            tracks = _description_tracks(item.tag)

            alternatives = find_adjacent_media_alternatives(item.tag)

            description_links = [
                element
                for element in alternatives.links_or_buttons
                if _is_audio_description_alternative(element)
            ]

            element_id = _media_identifier(item.tag, item.index)

            has_candidate = bool(tracks or description_links)

            if has_candidate:
                message = (
                    "Une piste ou une version alternative candidate avec "
                    "audiodescription a été détectée. Son contenu et sa "
                    "synchronisation doivent être vérifiés."
                )

                recommendation = (
                    "Vérifier que l'audiodescription restitue les "
                    "informations visuelles nécessaires et qu'elle est "
                    "synchronisée avec le média."
                )

            else:
                message = (
                    "Aucune piste ni version alternative avec "
                    "audiodescription clairement identifiable n'a été "
                    "détectée. La nécessité d'une audiodescription reste "
                    "à évaluer."
                )

                recommendation = (
                    "Vérifier si le média nécessite une audiodescription. "
                    "Si oui, fournir une audiodescription synchronisée ou "
                    "une version alternative avec audiodescription "
                    "accessible par un lien ou un bouton adjacent."
                )

            findings.append(
                Finding(
                    element=element_id,
                    message=message,
                    recommendation=recommendation,
                    evidence={
                        "test_scope": self.media_description,
                        "media_type_requires_review": True,
                        "description_tracks_count": len(tracks),
                        "track_sources": [
                            str(track.get("src", ""))
                            for track in tracks
                        ],
                        "adjacent_audio_description_alternatives": len(
                            description_links
                        ),
                    },
                )
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            (
                f"{len(videos)} média(s) vidéo à classifier comme "
                f"{self.media_description} et à vérifier pour la nécessité "
                "et la présence d'une audiodescription."
            ),
            findings=findings,
            tested_elements=len(videos),
            metadata={
                "candidate_media": len(videos),
                "media_type_requires_review": True,
            },
        )


class Test451(_Criterion45Test):
    test_id = "4.5.1"
    criterion_id = "4.5"
    media_description = "seulement vidéo"


class Test452(_Criterion45Test):
    test_id = "4.5.2"
    criterion_id = "4.5"
    media_description = "vidéo synchronisée"


def _description_tracks(tag: Tag) -> list[Tag]:
    """
    Recherche les pistes de description associées directement à la vidéo.

    Une piste est considérée comme candidate lorsqu'elle :
    - est une balise <track> ;
    - possède kind="descriptions" ;
    - possède une source src non vide.
    """
    return [
        track
        for track in tag.find_all("track", recursive=False)
        if str(track.get("kind", "")).strip().lower() == "descriptions"
        and str(track.get("src", "")).strip()
    ]


def _is_audio_description_alternative(element: Tag) -> bool:
    """
    Détermine si un lien ou bouton adjacent semble proposer
    une version avec audiodescription.
    """

    values = [
        element.get_text(" ", strip=True),
        str(element.get("href", "")),
        str(element.get("aria-label", "")),
        str(element.get("title", "")),
    ]

    text = " ".join(values).casefold()

    text = (
        text
        .replace("-", " ")
        .replace("_", " ")
    )

    return any(
        phrase in text
        for phrase in (
            "audiodescription",
            "audio description",
            "description audio",
            "version audio",
        )
    )


def _is_exempt_or_decorative(tag: Tag) -> bool:
    """
    Ignore les vidéos explicitement masquées ou décoratives.
    """

    return (
        tag.get("aria-hidden") == "true"
        or tag.get("role") == "presentation"
    )


def _media_identifier(tag: Tag, index: int) -> str:
    """
    Retourne un identifiant stable et lisible pour le média.
    """

    media_id = tag.get("id")

    if isinstance(media_id, str) and media_id.strip():
        return f"{tag.name}#{media_id}"

    return f"{tag.name}[index={index}]"
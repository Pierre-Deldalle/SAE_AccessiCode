from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.media import (
    TemporalMedia,
    find_adjacent_media_alternatives,
    find_temporal_media,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test441(RGAATest):
    test_id = "4.4.1"
    criterion_id = "4.4"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        # On recherche tous les médias vidéo non exemptés/décoratifs
        media_items = [
            item for item in find_temporal_media(context.dom)
            if item.kind == "video" and not _is_exempt_or_decorative(item.tag)
        ]

        # On ne retient pour le 4.4.1 que les médias possédant des sous-titres (track ou alternative)
        checked_items: list[tuple[TemporalMedia, list[Tag]]] = []
        for item in media_items:
            tracks = _caption_tracks(item.tag)
            alternatives = find_adjacent_media_alternatives(item.tag)
            if tracks or alternatives.links_or_buttons:
                checked_items.append((item, tracks))

        if not checked_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média vidéo synchronisé avec sous-titres n'a été détecté.",
            )

        findings: list[Finding] = []
        for item, tracks in checked_items:
            element_id = _media_identifier(item.tag, item.index)
            alternatives = find_adjacent_media_alternatives(item.tag)
            
            findings.append(
                Finding(
                    element=element_id,
                    message=(
                        "Des sous-titres ou une alternative ont été détectés. "
                        "La pertinence du contenu et la synchronisation des sous-titres "
                        "nécessitent une vérification manuelle."
                    ),
                    recommendation=(
                        "S'assurer que les sous-titres retranscrivent toutes les informations "
                        "sonores importantes (dialogues, bruits significatifs, identité des locuteurs) "
                        "et qu'ils sont correctement synchronisés avec l'image et le son."
                    ),
                    evidence={
                        "captions_tracks_count": len(tracks),
                        "track_sources": [str(t.get("src", "")) for t in tracks if t.get("src")],
                        "adjacent_links_or_buttons": len(alternatives.links_or_buttons),
                    },
                )
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            f"{len(checked_items)} média(s) vidéo avec sous-titres à vérifier pour la pertinence et la synchronisation.",
            findings=findings,
            tested_elements=len(checked_items),
            metadata={"candidate_media": len(checked_items)},
        )


def _caption_tracks(tag: Tag) -> list[Tag]:
    return [
        track for track in tag.find_all("track", recursive=False)
        if str(track.get("kind", "")).strip().lower() in {"captions", "subtitles"}
        and str(track.get("src", "")).strip()
    ]


def _is_exempt_or_decorative(tag: Tag) -> bool:
    return tag.get("aria-hidden") == "true" or tag.get("role") == "presentation"


def _media_identifier(tag: Tag, index: int) -> str:
    media_id = tag.get("id")
    if isinstance(media_id, str) and media_id.strip():
        return f"{tag.name}#{media_id}"
    return f"{tag.name}[index={index}]"
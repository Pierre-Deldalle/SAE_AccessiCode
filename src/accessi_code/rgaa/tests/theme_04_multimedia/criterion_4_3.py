from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.media import (
    TemporalMedia,
    find_adjacent_media_alternatives,
    find_temporal_media,
    is_media_exempt,
    media_identifier,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test431(RGAATest):
    test_id = "4.3.1"
    criterion_id = "4.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media_items = [
            item for item in find_temporal_media(context.dom)
            if item.kind == "video" and not is_media_exempt(item.tag)
        ]

        if not media_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média vidéo synchronisé détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for item in media_items:
            has_captions = _has_caption_candidate(item)
            element_id = media_identifier(item.tag, item.index)
            evidence = _caption_evidence(item)

            if has_captions:
                statuses.append(TestStatus.PASS)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Une piste ou une alternative de sous-titres candidats a été détectée.",
                        evidence=evidence,
                    )
                )
            else:
                statuses.append(TestStatus.FAIL)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Aucun sous-titre ni aucune alternative associée n'a été détecté pour cette vidéo.",
                        recommendation=(
                            "Fournir une piste de sous-titres synchronisés avec kind=\"captions\" "
                            "ou une version alternative sous-titrée accessible via un lien/bouton adjacent."
                        ),
                        evidence=evidence,
                    )
                )

        final_status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            final_status,
            f"Analyse effectuée sur {len(media_items)} média(s) vidéo.",
            findings=findings,
            tested_elements=len(media_items),
            metadata={
                "candidate_media": len(media_items),
                "passed_count": statuses.count(TestStatus.PASS),
                "failed_count": statuses.count(TestStatus.FAIL),
            },
        )


class Test432(RGAATest):
    test_id = "4.3.2"
    criterion_id = "4.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        # On recherche toutes les balises track de sous-titres dans le DOM
        media_items = [
            item for item in find_temporal_media(context.dom)
            if item.kind == "video" and not is_media_exempt(item.tag)
        ]

        track_elements: list[tuple[TemporalMedia, Tag]] = []
        for item in media_items:
            for track in item.tag.find_all("track", recursive=False):
                kind = str(track.get("kind", "")).strip().lower()
                if kind in {"captions", "subtitles"}:
                    track_elements.append((item, track))

        if not track_elements:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune piste de sous-titres détectée dans le DOM.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for item, track in track_elements:
            kind_val = str(track.get("kind", "")).strip().lower()
            element_id = media_identifier(item.tag, item.index)

            if kind_val == "captions":
                statuses.append(TestStatus.PASS)
                findings.append(
                    Finding(
                        element=element_id,
                        message='La piste de sous-titres utilise bien l\'attribut kind="captions".',
                        evidence={"track_kind": kind_val, "src": track.get("src")},
                    )
                )
            else:
                statuses.append(TestStatus.FAIL)
                findings.append(
                    Finding(
                        element=element_id,
                        message=f'La piste de sous-titres utilise kind="{kind_val}" au lieu de kind="captions".',
                        recommendation='Remplacer l\'attribut kind de la piste par kind="captions".',
                        evidence={"track_kind": kind_val, "src": track.get("src")},
                    )
                )

        final_status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            final_status,
            f"{len(track_elements)} piste(s) de sous-titres vérifiée(s).",
            findings=findings,
            tested_elements=len(track_elements),
            metadata={
                "candidate_tracks": len(track_elements),
                "passed_count": statuses.count(TestStatus.PASS),
                "failed_count": statuses.count(TestStatus.FAIL),
            },
        )


def _has_caption_candidate(item: TemporalMedia) -> bool:
    caption_tracks = _tracks_with_kind(item.tag, "captions")
    alternatives = find_adjacent_media_alternatives(item.tag)
    return bool(caption_tracks or alternatives.links_or_buttons)


def _caption_evidence(item: TemporalMedia) -> dict[str, Any]:
    caption_tracks = _tracks_with_kind(item.tag, "captions")
    alternatives = find_adjacent_media_alternatives(item.tag)
    return {
        "captions_track_candidates": len(caption_tracks),
        "adjacent_link_or_button_candidates": len(alternatives.links_or_buttons),
    }


def _tracks_with_kind(tag: Tag, kind: str) -> list[Tag]:
    return [
        track for track in tag.find_all("track", recursive=False)
        if str(track.get("kind", "")).strip().lower() == kind
    ]


def _aggregate_statuses(statuses: list[TestStatus]) -> TestStatus:
    if TestStatus.FAIL in statuses:
        return TestStatus.FAIL
    if TestStatus.NEEDS_REVIEW in statuses:
        return TestStatus.NEEDS_REVIEW
    if TestStatus.PASS in statuses:
        return TestStatus.PASS
    return TestStatus.NOT_APPLICABLE
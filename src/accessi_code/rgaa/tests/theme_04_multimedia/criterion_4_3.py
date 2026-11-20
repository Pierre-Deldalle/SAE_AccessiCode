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
            item for item in find_temporal_media(context.dom) if item.kind == "video" and not is_media_exempt(item.tag)
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

            # Une vidéo peut être exemptée, sans piste sonore ou avoir des sous-titres
            # incrustés : la présence de sous-titres doit être confirmée par un humain.
            statuses.append(TestStatus.NEEDS_REVIEW)

            if has_captions:
                findings.append(
                    Finding(
                        element=element_id,
                        message="Une piste ou une alternative de sous-titres candidats a été détectée.",
                        evidence=evidence,
                    )
                )
            else:
                findings.append(
                    Finding(
                        element=element_id,
                        message="Aucun sous-titre ni aucune alternative associée n'a été détecté pour cette vidéo.",
                        recommendation=(
                            'Fournir une piste de sous-titres synchronisés avec kind="captions" '
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

        media_items = [
            item for item in find_temporal_media(context.dom) if item.kind == "video" and not is_media_exempt(item.tag)
        ]

        # Vidéos possédant au moins une piste <track> de sous-titres candidate.
        media_with_tracks: list[tuple[TemporalMedia, list[Tag]]] = []
        for item in media_items:
            tracks = _subtitle_track_candidates(item.tag)
            if tracks:
                media_with_tracks.append((item, tracks))

        if not media_with_tracks:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune piste de sous-titres détectée dans le DOM.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for item, tracks in media_with_tracks:
            element_id = media_identifier(item.tag, item.index)
            kinds = [_track_kind(track) for track in tracks]
            wrong_kinds = [kind for kind in kinds if kind != "captions"]
            evidence = {
                "track_kinds": kinds,
                "track_sources": [track.get("src") for track in tracks],
            }

            if not wrong_kinds:
                statuses.append(TestStatus.PASS)
                findings.append(
                    Finding(
                        element=element_id,
                        message='Les pistes de sous-titres utilisent bien l\'attribut kind="captions".',
                        evidence=evidence,
                    )
                )
            else:
                statuses.append(TestStatus.FAIL)
                shown = ", ".join(f'kind="{kind}"' if kind else "sans attribut kind" for kind in wrong_kinds)
                findings.append(
                    Finding(
                        element=element_id,
                        message=f'Piste(s) de sous-titres non conforme(s) : {shown} au lieu de kind="captions".',
                        recommendation=(
                            'Utiliser l\'attribut kind="captions" sur les pistes de sous-titres synchronisés.'
                        ),
                        evidence=evidence,
                    )
                )

        final_status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            final_status,
            f"{len(media_with_tracks)} vidéo(s) avec piste(s) de sous-titres vérifiée(s).",
            findings=findings,
            tested_elements=len(media_with_tracks),
            metadata={
                "candidate_tracks": sum(len(tracks) for _, tracks in media_with_tracks),
                "passed_count": statuses.count(TestStatus.PASS),
                "failed_count": statuses.count(TestStatus.FAIL),
            },
        )


# Valeurs de kind qui ne correspondent pas à des sous-titres.
_NON_SUBTITLE_TRACK_KINDS = {"descriptions", "chapters", "metadata"}


def _track_kind(track: Tag) -> str:
    return str(track.get("kind", "")).strip().lower()


def _subtitle_track_candidates(tag: Tag) -> list[Tag]:
    """Pistes <track> pointant vers un fichier et pouvant servir de sous-titres."""
    candidates = []
    for track in tag.find_all("track", recursive=False):
        src = track.get("src")
        if not (isinstance(src, str) and src.strip()):
            continue
        if _track_kind(track) in _NON_SUBTITLE_TRACK_KINDS:
            continue
        candidates.append(track)
    return candidates


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
        track for track in tag.find_all("track", recursive=False) if str(track.get("kind", "")).strip().lower() == kind
    ]


def _aggregate_statuses(statuses: list[TestStatus]) -> TestStatus:
    if TestStatus.FAIL in statuses:
        return TestStatus.FAIL
    if TestStatus.NEEDS_REVIEW in statuses:
        return TestStatus.NEEDS_REVIEW
    if TestStatus.PASS in statuses:
        return TestStatus.PASS
    return TestStatus.NOT_APPLICABLE

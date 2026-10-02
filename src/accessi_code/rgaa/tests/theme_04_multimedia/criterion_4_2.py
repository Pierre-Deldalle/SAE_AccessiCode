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


class _Criterion42Test(RGAATest):
    required_capabilities = frozenset({Capability.DOM})
    media_kind: str
    media_description: str

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media_items = [item for item in find_temporal_media(context.dom) if item.kind == self.media_kind]
        
        # Le périmètre d'applicabilité exclut uniquement les éléments explicitements exemptés/décoratifs
        applicable_items = [item for item in media_items if not _is_exempt_or_decorative(item.tag)]

        if not applicable_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                f"Aucun média {self.media_description} détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for item in applicable_items:
            has_alt = _has_alternative_candidate(item)
            element_id = _media_identifier(item)
            evidence = _alternative_evidence(item)

            if has_alt:
                statuses.append(TestStatus.PASS)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Une alternative textuelle ou une piste de description candidate a été identifiée.",
                        evidence=evidence,
                    )
                )
            else:
                statuses.append(TestStatus.FAIL)
                findings.append(
                    Finding(
                        element=element_id,
                        message=(
                            "Aucune alternative pertinente (transcription, audiodescription, "
                            "lien ou bouton adjacent) n'a été trouvée pour ce média."
                        ),
                        recommendation=(
                            "Associer une alternative textuelle ou une audiodescription pertinente "
                            "au média (ou fournir un bouton/lien d'accès adjacent)."
                        ),
                        evidence=evidence,
                    )
                )

        final_status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            final_status,
            f"Analyse effectuée sur {len(applicable_items)} média(s) {self.media_description}.",
            findings=findings,
            tested_elements=len(applicable_items),
            metadata={
                "candidate_media": len(applicable_items),
                "passed_count": statuses.count(TestStatus.PASS),
                "failed_count": statuses.count(TestStatus.FAIL),
            },
        )


class Test421(_Criterion42Test):
    test_id = "4.2.1"
    criterion_id = "4.2"
    media_kind = "audio"
    media_description = "seulement audio"


class Test422(_Criterion42Test):
    test_id = "4.2.2"
    criterion_id = "4.2"
    media_kind = "video"
    media_description = "seulement vidéo"


class Test423(_Criterion42Test):
    test_id = "4.2.3"
    criterion_id = "4.2"
    media_kind = "video"
    media_description = "vidéo synchronisée"


def _has_alternative_candidate(item: TemporalMedia) -> bool:
    alternatives = find_adjacent_media_alternatives(item.tag)
    has_track = bool(
        item.tag.find(
            "track",
            attrs={"kind": lambda k: k and str(k).lower() in {"descriptions", "subtitles"}},
        )
    )
    return bool(
        alternatives.links_or_buttons
        or alternatives.text_candidates
        or item.aria_describedby_text
        or has_track
    )


def _alternative_evidence(item: TemporalMedia) -> dict[str, Any]:
    alternatives = find_adjacent_media_alternatives(item.tag)
    has_track = bool(
        item.tag.find(
            "track",
            attrs={"kind": lambda k: k and str(k).lower() in {"descriptions", "subtitles"}},
        )
    )
    return {
        "adjacent_links_or_buttons": len(alternatives.links_or_buttons),
        "adjacent_text_candidates": len(alternatives.text_candidates),
        "has_aria_describedby": bool(item.aria_describedby_text),
        "has_description_track": has_track,
    }


def _is_exempt_or_decorative(tag: Tag) -> bool:
    if tag.get("aria-hidden") == "true":
        return True
    return tag.get("role") == "presentation"


def _media_identifier(item: TemporalMedia) -> str:
    media_id = item.tag.get("id")
    if isinstance(media_id, str) and media_id.strip():
        return f"{item.tag.name}#{media_id}"
    return f"{item.tag.name}[index={item.index}]"


def _aggregate_statuses(statuses: list[TestStatus]) -> TestStatus:
    """Priorité des résultats RGAA : FAIL > NEEDS_REVIEW > PASS."""
    if TestStatus.FAIL in statuses:
        return TestStatus.FAIL
    if TestStatus.NEEDS_REVIEW in statuses:
        return TestStatus.NEEDS_REVIEW
    if TestStatus.PASS in statuses:
        return TestStatus.PASS
    return TestStatus.NOT_APPLICABLE
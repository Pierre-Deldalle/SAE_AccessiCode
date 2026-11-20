from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

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

        # Le critère 4.2 porte sur la pertinence d'une alternative existante :
        # seuls les médias non exemptés possédant une alternative candidate sont concernés.
        non_exempt_items = [item for item in media_items if not is_media_exempt(item.tag)]
        applicable_items = [item for item in non_exempt_items if _has_alternative_candidate(item)]

        if not applicable_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                f"Aucun média {self.media_description} possédant une alternative détecté.",
                metadata={"media_without_alternative": len(non_exempt_items)},
            )

        findings: list[Finding] = []

        for item in applicable_items:
            findings.append(
                Finding(
                    element=media_identifier(item.tag, item.index),
                    message="Une alternative candidate a été identifiée : sa pertinence doit être vérifiée.",
                    recommendation=(
                        "Vérifier manuellement que l'alternative (transcription, audiodescription "
                        "ou contenu accessible via le lien ou bouton adjacent) restitue fidèlement "
                        "l'information du média."
                    ),
                    evidence=_alternative_evidence(item),
                )
            )

        # La pertinence d'une alternative ne peut pas être évaluée automatiquement.
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            f"{len(applicable_items)} média(s) {self.media_description} avec une alternative à vérifier.",
            findings=findings,
            tested_elements=len(applicable_items),
            metadata={
                "candidate_media": len(applicable_items),
                "media_without_alternative": len(non_exempt_items) - len(applicable_items),
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
        alternatives.links_or_buttons or alternatives.text_candidates or item.aria_describedby_text or has_track
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

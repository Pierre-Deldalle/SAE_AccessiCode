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
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class _Criterion41Test(RGAATest):
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

        applicable_items = [item for item in media_items if not is_media_exempt(item.tag)]

        if not applicable_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                f"Aucun média {self.media_description} applicable détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for item in applicable_items:
            alternatives = find_adjacent_media_alternatives(item.tag)
            
            has_alternative = bool(
                alternatives.links_or_buttons
                or alternatives.text_candidates
                or item.has_track_description
                or item.aria_describedby_text
            )

            element_id = media_identifier(item.tag, item.index)

            if has_alternative:
                statuses.append(TestStatus.PASS)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Une alternative potentielle ou une piste de description a été détectée.",
                        evidence={
                            "has_track": item.has_track_description,
                            "has_aria_describedby": bool(item.aria_describedby_text),
                            "adjacent_links_or_buttons": len(alternatives.links_or_buttons),
                            "adjacent_text_candidates": len(alternatives.text_candidates),
                        },
                    )
                )
            else:
                statuses.append(TestStatus.FAIL)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Aucune alternative textuelle, audiodescription ou lien/bouton adjacent n'a été trouvé.",
                        recommendation=(
                            "Fournir une transcription textuelle ou une audiodescription "
                            "accessible via un lien, un bouton ou un texte adjacent."
                        ),
                        evidence={
                            "has_track": item.has_track_description,
                            "adjacent_links_or_buttons": 0,
                            "adjacent_text_candidates": 0,
                        },
                    )
                )

        final_status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            final_status,
            f"Analyse terminée pour {len(applicable_items)} média(s) {self.media_description}.",
            findings=findings,
            tested_elements=len(applicable_items),
        )


class Test411(_Criterion41Test):
    test_id = "4.1.1"
    criterion_id = "4.1"
    media_kind = "audio"
    media_description = "seulement audio"


class Test412(_Criterion41Test):
    test_id = "4.1.2"
    criterion_id = "4.1"
    media_kind = "video"
    media_description = "seulement vidéo"


class Test413(_Criterion41Test):
    test_id = "4.1.3"
    criterion_id = "4.1"
    media_kind = "video"
    media_description = "vidéo synchronisée"


def _aggregate_statuses(statuses: list[TestStatus]) -> TestStatus:
    if TestStatus.FAIL in statuses:
        return TestStatus.FAIL
    if TestStatus.NEEDS_REVIEW in statuses:
        return TestStatus.NEEDS_REVIEW
    if TestStatus.PASS in statuses:
        return TestStatus.PASS
    return TestStatus.NOT_APPLICABLE
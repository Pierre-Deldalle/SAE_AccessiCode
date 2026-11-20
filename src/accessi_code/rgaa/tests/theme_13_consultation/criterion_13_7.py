"""
RGAA 4.1.2 — critère 13.7 : dans chaque page web, les changements brusques de
luminosité ou les effets de flash sont-ils correctement utilisés ?

Un effet de flash est conforme si sa fréquence est inférieure à 3 par seconde
ou si sa surface totale cumulée est inférieure ou égale à 21 824 pixels.

- 13.7.1 (images et médias) : vidéos, images animées (GIF, PNG ou WebP lus dans
  les fichiers fournis) et SVG animés. Surface connue ≤ 21 824 px → PASS ; sinon
  le contenu doit être regardé → NEEDS_REVIEW ;
- 13.7.2 (scripts) : minuteurs qui modifient la luminosité d'un élément
  (opacité, visibilité, couleurs…). Intervalle d'au moins 167 ms (moins de
  3 flashs par seconde) → PASS ; sinon NEEDS_REVIEW ;
- 13.7.3 (CSS) : animations répétées des propriétés de luminosité. Fréquence
  calculée inférieure à 3 par seconde ou surface ≤ 21 824 px → PASS ; sinon
  NEEDS_REVIEW.

Aucun FAIL automatique : l'amplitude du changement de luminosité ne se mesure
pas dans le code.
"""

from __future__ import annotations

import math
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.animations import (
    FLASH_AREA_LIMIT,
    LIGHT_PROPERTIES,
    css_animations,
    element_area,
    is_animated_image_file,
    local_file,
)
from accessi_code.analysis.components import component_identifier
from accessi_code.analysis.scripts import page_scripts, timer_calls
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

FLASH_FREQUENCY_LIMIT = 3.0
# Intervalle minimal entre deux changements pour rester sous 3 flashs par seconde
# (un flash = deux changements opposés).
MIN_TOGGLE_INTERVAL_MS = 1000 / (2 * FLASH_FREQUENCY_LIMIT)

LIGHT_SCRIPT = re.compile(
    r"\.style\s*\.\s*(?:opacity|visibility|display|color|background\w*|filter)\s*=|\.style\s*\.\s*setProperty\s*\("
    r"|classList\s*\.\s*toggle\s*\(|\.hidden\s*=|setAttribute\s*\(\s*['\"](?:style|fill|opacity)",
    re.IGNORECASE,
)
RECOMMENDATION = (
    "Vérifier que l'effet ne produit pas plus de 3 flashs par seconde, ou que sa surface ne dépasse pas "
    "21 824 pixels ; sinon ralentir l'effet, réduire sa taille ou le supprimer."
)


def _area_ok(element: Tag) -> bool:
    area = element_area(element)
    return area is not None and area <= FLASH_AREA_LIMIT


class FlashTest(RGAATest):
    criterion_id = "13.7"
    required_capabilities = frozenset({Capability.DOM})

    def _soup(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom


class Test1371(FlashTest):
    """13.7.1 : images et éléments multimédias."""

    test_id = "13.7.1"
    empty = "Aucune vidéo, image animée ou animation SVG dans la page."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        candidates: list[tuple[Tag, str]] = []
        for video in soup.find_all("video"):
            candidates.append((video, "vidéo"))
        for image in soup.find_all(["img", "input"]):
            path = local_file(context, str(image.get("src") or ""))
            if path is not None and is_animated_image_file(path):
                candidates.append((image, "image animée"))
        for svg in soup.find_all("svg"):
            if svg.find(
                ["animate", "set"], attrs={"attributename": re.compile(r"opacity|fill|visibility|color", re.IGNORECASE)}
            ):
                candidates.append((svg, "animation SVG"))

        outcomes: list[Outcome] = []
        for index, (element, kind) in enumerate(candidates):
            if _area_ok(element):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    component_identifier(element, index),
                    f"Cette {kind} peut provoquer des flashs : leur fréquence et leur surface restent à vérifier.",
                    RECOMMENDATION,
                    kind=kind,
                    area=element_area(element),
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty, noun="média(s)")


class Test1372(FlashTest):
    """13.7.2 : scripts qui changent brusquement la luminosité."""

    test_id = "13.7.2"
    empty = "Aucun script ne modifie de façon répétée la luminosité d'un élément."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        self._soup(context)
        outcomes: list[Outcome] = []
        for call in timer_calls(page_scripts(context)):
            if call.kind != "setInterval" and "setTimeout" not in call.callback:
                continue  # un setTimeout simple ne produit qu'un seul changement
            if not LIGHT_SCRIPT.search(call.callback):
                continue
            if call.delay_ms is not None and call.delay_ms >= MIN_TOGGLE_INTERVAL_MS:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            interval = f"toutes les {call.delay_ms:g} ms" if call.delay_ms is not None else "à un rythme calculé"
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    f"{call.source.label} ({call.kind})",
                    f"Un script modifie la luminosité d'un élément {interval} : risque de flash à vérifier.",
                    RECOMMENDATION,
                    delay_ms=call.delay_ms,
                    code=call.source.snippet(call.position),
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty, noun="script(s)")


class Test1373(FlashTest):
    """13.7.3 : mises en forme CSS qui changent brusquement la luminosité."""

    test_id = "13.7.3"
    empty = "Aucune animation CSS répétée de la luminosité."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        self._soup(context)
        outcomes: list[Outcome] = []
        for animation in css_animations(context):
            changes = animation.keyframes.changes(LIGHT_PROPERTIES, cyclic=animation.cyclic)
            if not changes or animation.duration_s <= 0:
                continue
            flashes_per_cycle = changes / 2
            if animation.iterations <= 1 and flashes_per_cycle < 1:
                continue  # simple apparition ou disparition, sans flash
            frequency = flashes_per_cycle / animation.duration_s
            small = animation.area is not None and animation.area <= FLASH_AREA_LIMIT
            if frequency < FLASH_FREQUENCY_LIMIT or small:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            repetitions = "à l'infini" if math.isinf(animation.iterations) else f"{animation.iterations:g} fois"
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    animation.selector,
                    f"L'animation « {animation.keyframes.name} » change la luminosité environ {frequency:.1f} "
                    f"fois par seconde ({repetitions}) : risque de flash à vérifier.",
                    RECOMMENDATION,
                    keyframes=animation.keyframes.name,
                    duration_s=animation.duration_s,
                    frequency=round(frequency, 2),
                    area=animation.area,
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty, noun="animation(s) CSS")

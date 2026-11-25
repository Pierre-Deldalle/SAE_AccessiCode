"""
RGAA 4.1.2 — critère 13.12 : dans chaque page web, les fonctionnalités qui
impliquent un mouvement de l'appareil ou vers l'appareil peuvent-elles être
satisfaites de manière alternative ?

Fonctionnalités repérées dans les scripts :
- mouvement de l'appareil (13.12.1) : événements devicemotion et
  deviceorientation, capteurs Accelerometer, Gyroscope… ;
- mouvement vers l'appareil (13.12.2) : capteurs de proximité ou de lumière,
  reconnaissance de gestes par la caméra.
La rotation de l'écran (orientationchange, screen.orientation) relève de 13.9.

Questions de sens, jugées par l'IA à partir de l'extrait de code et des
contrôles de la page :
- 13.12.1 / 13.12.2 : un composant d'interface permet-il la même action, ou le
  mouvement est-il essentiel ? (``motion_alternative``) ;
- 13.12.3 : l'utilisateur peut-il désactiver la détection du mouvement ?
  (``motion_disable``, avec l'indication que le code retire ou non l'écoute).
PASS / FAIL selon l'IA, NEEDS_REVIEW si elle est incertaine ou absente ;
aucune fonctionnalité concernée → NOT_APPLICABLE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import interface_controls
from accessi_code.analysis.scripts import ScriptSource, page_scripts
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome

DEVICE_MOTION = re.compile(
    r"['\"`]device(?:motion|orientation(?:absolute)?)['\"`]|\.ondevice(?:motion|orientation)\b"
    r"|new\s+(?:Accelerometer|Gyroscope|LinearAccelerationSensor|GravitySensor|AbsoluteOrientationSensor"
    r"|RelativeOrientationSensor|Magnetometer)\s*\(|DeviceMotionEvent\s*\.\s*requestPermission",
)
TOWARDS_DEVICE = re.compile(
    r"['\"`](?:deviceproximity|userproximity|devicelight)['\"`]|\.on(?:deviceproximity|userproximity)\b"
    r"|new\s+(?:ProximitySensor|AmbientLightSensor)\s*\("
    r"|getUserMedia[\s\S]{0,2000}?(?:handpose|hand-pose|handtrack|fingerpose|gesture|mediapipe)",
    re.IGNORECASE,
)
DISABLE_CODE = re.compile(
    r"removeEventListener\s*\(\s*['\"`](?:device\w+|userproximity)['\"`]|\.ondevice\w+\s*=\s*null"
    r"|\.\s*stop\s*\(\s*\)",
    re.IGNORECASE,
)
MOTION = "un mouvement de l'appareil"
TOWARDS = "un mouvement vers l'appareil"


@dataclass
class MotionFeature:
    source: ScriptSource
    position: int
    motion: str


def motion_features(sources: list[ScriptSource]) -> list[MotionFeature]:
    """Première fonctionnalité de chaque type par script."""
    features: list[MotionFeature] = []
    for source in sources:
        for pattern, motion in ((DEVICE_MOTION, MOTION), (TOWARDS_DEVICE, TOWARDS)):
            match = pattern.search(source.masked)
            if match:
                features.append(MotionFeature(source, match.start(), motion))
    return features


class MotionSensorTest(RGAATest):
    criterion_id = "13.12"
    required_capabilities = frozenset({Capability.DOM})
    ai_kind = "motion_alternative"
    motions: tuple[str, ...] = (MOTION, TOWARDS)

    def _messages(self, motion: str) -> tuple[str, str, str]:
        return (
            f"La fonctionnalité déclenchée par {motion} ne peut pas être accomplie avec un composant d'interface.",
            f"L'existence d'un composant d'interface qui remplace {motion} reste à vérifier.",
            "Proposer un composant d'interface (bouton…) qui permet la même action, sauf si le mouvement est "
            "essentiel.",
        )

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        sources = page_scripts(context)
        features = [feature for feature in motion_features(sources) if feature.motion in self.motions]
        disable_code = any(DISABLE_CODE.search(source.masked) for source in sources)
        controls = interface_controls(soup)
        context_text = "Contrôles de la page : " + ("; ".join(controls) if controls else "aucun")
        items = [
            RelevanceItem(
                text=feature.source.snippet(feature.position, before=200, after=400),
                context=context_text,
                details={"motion": feature.motion, "script": feature.source.label, "disable_code": disable_code},
            )
            for feature in features
        ]
        verdicts = await judge_relevance(services, self.ai_kind, items)

        outcomes = []
        for feature, item, verdict in zip(features, items, verdicts, strict=True):
            fail, uncertain, recommendation = self._messages(feature.motion)
            outcomes.append(
                make_outcome(
                    verdict.status,
                    feature.source.label,
                    verdict.message(fail, uncertain),
                    recommendation,
                    **feature.source.location(feature.position),
                    motion=feature.motion,
                    code=item.text,
                    disable_code=disable_code,
                    controls=controls,
                    **verdict.evidence,
                )
            )
        empty = "Aucune fonctionnalité déclenchée par " + " ou ".join(self.motions) + "."
        return build_result(self, outcomes, empty_summary=empty, noun="fonctionnalité(s)")


class Test13121(MotionSensorTest):
    """13.12.1 : mouvement de l'appareil."""

    test_id = "13.12.1"
    motions = (MOTION,)


class Test13122(MotionSensorTest):
    """13.12.2 : mouvement vers l'appareil."""

    test_id = "13.12.2"
    motions = (TOWARDS,)


class Test13123(MotionSensorTest):
    """13.12.3 : désactivation de la détection du mouvement."""

    test_id = "13.12.3"
    ai_kind = "motion_disable"

    def _messages(self, motion: str) -> tuple[str, str, str]:
        return (
            f"La détection du mouvement ({motion}) ne peut pas être désactivée par l'utilisateur.",
            f"La possibilité de désactiver la détection du mouvement ({motion}) reste à vérifier.",
            "Proposer un réglage (case à cocher, interrupteur) qui désactive la détection du mouvement, "
            "sauf si le mouvement est essentiel.",
        )

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.analysis.media import is_media_exempt, media_identifier


class Test4101(RGAATest):
    """
    Test 4.10.1

    Chaque séquence sonore déclenchée automatiquement vérifie-t-elle
    au moins une des conditions suivantes ?

    - durée inférieure ou égale à 3 secondes ;
    - possibilité d'arrêter la séquence par une action utilisateur ;
    - possibilité de contrôler son volume indépendamment du volume système.

    L'analyse automatique identifie les séquences susceptibles de
    déclencher automatiquement un son et vérifie les contrôles
    explicitement présents dans le DOM.

    Lorsque la durée ou le comportement JavaScript ne peuvent pas être
    déterminés statiquement, une vérification manuelle est demandée.
    """

    test_id = "4.10.1"
    criterion_id = "4.10"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        candidates = _find_automatic_sound_candidates(context.dom)

        if not candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune séquence sonore déclenchée automatiquement détectée.",
            )

        findings: list[Finding] = []

        for candidate in candidates:
            tag = candidate["tag"]
            element_id = candidate["element"]

            if candidate["kind"] == "javascript":
                findings.append(
                    Finding(
                        element=element_id,
                        message=(
                            "Un code JavaScript susceptible de déclencher "
                            "automatiquement un son a été détecté."
                        ),
                        recommendation=(
                            "Vérifier au chargement de la page que la "
                            "séquence sonore dure au maximum 3 secondes, "
                            "peut être stoppée par l'utilisateur ou que "
                            "son volume peut être contrôlé indépendamment "
                            "du volume système."
                        ),
                        evidence={
                            "source_type": "javascript",
                            "automatic_sound": True,
                            "duration_verified": False,
                            "stop_control_detected": False,
                            "independent_volume_control_detected": False,
                            "manual_review_required": True,
                        },
                    )
                )
                continue

            autoplay = candidate["autoplay"]
            muted = candidate["muted"]
            controls = candidate["controls"]
            stop_control = candidate["stop_control"]
            volume_control = candidate["volume_control"]

            if muted:
                findings.append(
                    Finding(
                        element=element_id,
                        message=(
                            "Un média avec lecture automatique a été détecté, "
                            "mais il est explicitement muet."
                        ),
                        recommendation=(
                            "Vérifier que le média ne déclenche effectivement "
                            "aucun son au chargement de la page."
                        ),
                        evidence={
                            "source_type": tag.name,
                            "automatic_sound": False,
                            "autoplay": autoplay,
                            "muted": True,
                            "controls": controls,
                            "stop_control_detected": stop_control,
                            "independent_volume_control_detected": volume_control,
                            "duration_verified": False,
                            "manual_review_required": False,
                        },
                    )
                )
                continue

            if stop_control or volume_control:
                findings.append(
                    Finding(
                        element=element_id,
                        message=(
                            "Une séquence sonore déclenchée automatiquement "
                            "dispose d'un contrôle utilisateur détecté."
                        ),
                        recommendation=(
                            "Vérifier manuellement que ce contrôle permet "
                            "bien d'arrêter la séquence ou d'en contrôler "
                            "le volume indépendamment du volume système."
                        ),
                        evidence={
                            "source_type": tag.name,
                            "automatic_sound": True,
                            "autoplay": autoplay,
                            "muted": muted,
                            "controls": controls,
                            "stop_control_detected": stop_control,
                            "independent_volume_control_detected": volume_control,
                            "duration_verified": False,
                            "manual_review_required": True,
                        },
                    )
                )
                continue

            findings.append(
                Finding(
                    element=element_id,
                    message=(
                        "Une séquence sonore susceptible d'être déclenchée "
                        "automatiquement a été détectée sans contrôle "
                        "utilisateur identifiable."
                    ),
                    recommendation=(
                        "Vérifier que la séquence dure au maximum "
                        "3 secondes ou ajouter un dispositif permettant "
                        "de l'arrêter ou d'en contrôler le volume "
                        "indépendamment du volume système."
                    ),
                    evidence={
                        "source_type": tag.name,
                        "automatic_sound": True,
                        "autoplay": autoplay,
                        "muted": muted,
                        "controls": controls,
                        "stop_control_detected": stop_control,
                        "independent_volume_control_detected": volume_control,
                        "duration_verified": False,
                        "manual_review_required": True,
                    },
                )
            )

        audible_candidates = [
            finding
            for finding in findings
            if finding.evidence.get("automatic_sound") is True
        ]

        if not audible_candidates:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                (
                    "Aucun son effectivement déclenché automatiquement "
                    "n'a été identifié."
                ),
                findings=findings,
                tested_elements=len(candidates),
                metadata={
                    "candidate_sequences": len(candidates),
                    "audible_sequences": 0,
                    "muted_sequences": len(candidates),
                    "manual_review_required": False,
                },
            )

        requires_review = any(
            finding.evidence.get("manual_review_required") is True
            for finding in audible_candidates
        )

        if requires_review:
            status = TestStatus.NEEDS_REVIEW
            message = (
                f"{len(audible_candidates)} séquence(s) sonore(s) "
                "déclenchée(s) automatiquement nécessitent une "
                "vérification de leur contrôlabilité."
            )
        else:
            status = TestStatus.PASS
            message = (
                f"{len(audible_candidates)} séquence(s) sonore(s) "
                "déclenchée(s) automatiquement disposent d'un "
                "contrôle utilisateur détecté."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            message,
            findings=findings,
            tested_elements=len(candidates),
            metadata={
                "candidate_sequences": len(candidates),
                "audible_sequences": len(audible_candidates),
                "muted_sequences": sum(
                    1
                    for candidate in candidates
                    if candidate.get("muted") is True
                ),
                "sequences_with_stop_control": sum(
                    1
                    for finding in findings
                    if finding.evidence.get("stop_control_detected") is True
                ),
                "sequences_with_volume_control": sum(
                    1
                    for finding in findings
                    if finding.evidence.get(
                        "independent_volume_control_detected"
                    )
                    is True
                ),
                "manual_review_required": requires_review,
            },
        )


def _find_automatic_sound_candidates(
    dom: BeautifulSoup,
) -> list[dict[str, Any]]:
    """
    Recherche les éléments susceptibles de déclencher automatiquement
    une séquence sonore au chargement de la page.

    Éléments pris en compte par le RGAA :
    - <audio>
    - <video>
    - <object>
    - <embed>
    - <bgsound>
    - JavaScript susceptible d'utiliser la lecture audio automatique.
    """

    candidates: list[dict[str, Any]] = []

    for index, tag in enumerate(
        dom.find_all(["audio", "video", "object", "embed", "bgsound"])
    ):
        if is_media_exempt(tag):
            continue

        if not _has_automatic_playback(tag):
            continue

        muted = _is_muted(tag)

        controls = _has_native_controls(tag)
        stop_control = _has_stop_control(tag)
        volume_control = _has_volume_control(tag)

        candidates.append(
            {
                "kind": "element",
                "tag": tag,
                "element": media_identifier(tag, index),
                "autoplay": True,
                "muted": muted,
                "controls": controls,
                "stop_control": stop_control,
                "volume_control": volume_control,
            }
        )

    candidates.extend(_find_javascript_sound_candidates(dom))

    return candidates


def _has_automatic_playback(tag: Tag) -> bool:
    """
    Détecte les attributs HTML susceptibles de déclencher
    automatiquement la lecture.
    """

    if tag.name in {"audio", "video"}:
        return tag.has_attr("autoplay")

    if tag.name in {"object", "embed"}:
        for attribute in (
            "autoplay",
            "auto-start",
            "autostart",
            "data-autoplay",
        ):
            if tag.has_attr(attribute):
                return True

        for attribute in ("data", "src"):
            value = tag.get(attribute)

            if isinstance(value, str):
                lowered = value.lower()

                if (
                    "autoplay=true" in lowered
                    or "autostart=true" in lowered
                    or "auto_start=true" in lowered
                ):
                    return True

        return False

    if tag.name == "bgsound":
        return (
            tag.has_attr("autostart")
            or tag.has_attr("autoplay")
        )

    return False


def _is_muted(tag: Tag) -> bool:
    """
    Détecte les médias explicitement muets.
    """

    if tag.has_attr("muted"):
        return True

    muted = tag.get("muted")

    if isinstance(muted, str):
        return muted.strip().lower() in {
            "true",
            "1",
            "yes",
        }

    return False


def _has_native_controls(tag: Tag) -> bool:
    """
    Détecte la présence des contrôles natifs HTML.
    """

    return tag.has_attr("controls")


def _has_stop_control(tag: Tag) -> bool:
    """
    Recherche un dispositif adjacent ou associé permettant
    potentiellement d'arrêter la séquence.
    """

    parent = tag.parent

    if not isinstance(parent, Tag):
        return False

    controls = parent.find_all(
        ["button", "a"],
        recursive=False,
    )

    for control in controls:
        if _is_stop_control(control):
            return True

    return False


def _has_volume_control(tag: Tag) -> bool:
    """
    Recherche un contrôle de volume explicite associé au média.
    """

    if tag.has_attr("controls"):
        return True

    parent = tag.parent

    if not isinstance(parent, Tag):
        return False

    for control in parent.find_all(
        ["input", "button", "select"],
        recursive=False,
    ):
        if _is_volume_control(control):
            return True

    return False


def _is_stop_control(tag: Tag) -> bool:
    """
    Détermine si un contrôle est explicitement identifié comme
    permettant d'arrêter un son.
    """

    values = [
        tag.get_text(" ", strip=True),
        tag.get("aria-label"),
        tag.get("title"),
        tag.get("name"),
        tag.get("id"),
    ]

    text = " ".join(
        str(value).lower()
        for value in values
        if value
    )

    stop_keywords = (
        "stop",
        "arrêter",
        "arreter",
        "arrêt",
        "arret",
        "pause",
        "couper",
        "coupe",
    )

    return any(keyword in text for keyword in stop_keywords)


def _is_volume_control(tag: Tag) -> bool:
    """
    Détermine si un contrôle semble permettre de régler le volume.
    """

    values = [
        tag.get("aria-label"),
        tag.get("title"),
        tag.get("name"),
        tag.get("id"),
    ]

    text = " ".join(
        str(value).lower()
        for value in values
        if value
    )

    if any(
        keyword in text
        for keyword in (
            "volume",
            "son",
            "audio",
        )
    ):
        return True

    if tag.name == "input":
        input_type = tag.get("type")

        if isinstance(input_type, str):
            return input_type.lower() == "range"

    return False


def _find_javascript_sound_candidates(
    dom: BeautifulSoup,
) -> list[dict[str, Any]]:
    """
    Recherche des scripts contenant des appels courants pouvant
    déclencher automatiquement un son.

    Cette détection reste volontairement prudente : elle indique
    qu'une vérification manuelle est nécessaire et ne conclut
    pas automatiquement à une non-conformité.
    """

    candidates: list[dict[str, Any]] = []

    for index, script in enumerate(dom.find_all("script")):
        if script.string is None:
            script_text = script.get_text()
        else:
            script_text = script.string

        if not script_text:
            continue

        if _contains_automatic_audio_code(script_text):
            candidates.append(
                {
                    "kind": "javascript",
                    "tag": script,
                    "element": f"script[index={index}]",
                    "autoplay": True,
                    "muted": False,
                    "controls": False,
                    "stop_control": False,
                    "volume_control": False,
                }
            )

    return candidates


def _contains_automatic_audio_code(script: str) -> bool:
    """
    Détecte quelques formes courantes de lecture automatique
    via JavaScript / Web Audio API.
    """

    patterns = (
        r"\.play\s*\(",
        r"\.start\s*\(",
        r"AudioContext",
        r"webkitAudioContext",
        r"createBufferSource",
        r"createMediaElementSource",
    )

    return any(
        re.search(pattern, script, flags=re.IGNORECASE)
        for pattern in patterns
    )



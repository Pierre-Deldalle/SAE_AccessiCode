from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.analysis.media import TemporalMedia, find_temporal_media
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


_ACTION_PATTERNS = {
    "playback": re.compile(
        r"\blecture\b|pause|stop|arr[êe]t|reprendre|play",
        re.I,
    ),
    "sound": re.compile(
        r"\bmuet\b|mute|unmute|silence",
        re.I,
    ),
    "volume": re.compile(
        r"\bvolume\b",
        re.I,
    ),
    "subtitles": re.compile(
        r"sous.?tit|caption|subtitle",
        re.I,
    ),
    "description": re.compile(
        r"audiodescription|audio.?description",
        re.I,
    ),
}


class _Criterion411Test(RGAATest):
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        media_items = find_temporal_media(context.dom)

        if not media_items:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média temporel détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for media in media_items:
            status, finding = self._evaluate(media, context.dom)
            statuses.append(status)
            findings.append(finding)

        status = _aggregate_statuses(statuses)

        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            f"Analyse terminée pour {len(media_items)} média(s) temporel(s).",
            findings=findings,
            tested_elements=len(media_items),
            metadata={
                "media_count": len(media_items),
                "native_control_count": sum(
                    1
                    for item in media_items
                    if item.tag.has_attr("controls")
                ),
            },
        )

    def _evaluate(
        self,
        media: TemporalMedia,
        dom: BeautifulSoup,
    ) -> tuple[TestStatus, Finding]:
        raise NotImplementedError


class Test4111(_Criterion411Test):
    """Vérifie la présence des fonctionnalités nécessaires au contrôle."""

    test_id = "4.11.1"
    criterion_id = "4.11"

    def _evaluate(
        self,
        media: TemporalMedia,
        dom: BeautifulSoup,
    ) -> tuple[TestStatus, Finding]:
        element = _media_identifier(media)
        controls = _associated_controls(media, dom)

        native_controls = (
            media.tag.has_attr("controls")
            and media.tag.name in {"audio", "video"}
        )

        action_names = _recognized_actions(controls)
        tracks = _track_kinds(media.tag)

        required_actions = {"playback"}

        if media.kind == "audio":
            required_actions.add("sound")

        if tracks.intersection({"captions", "subtitles"}):
            required_actions.add("subtitles")

        if "descriptions" in tracks:
            required_actions.add("description")

        missing_actions: set[str]

        if native_controls:
            missing_actions = set()

            if "descriptions" in tracks:
                status = TestStatus.NEEDS_REVIEW
                message = (
                    "Les commandes natives sont présentes, mais le contrôle "
                    "de la piste d'audiodescription dépend du lecteur utilisé."
                )
            else:
                status = TestStatus.PASS
                message = (
                    "Les commandes natives du média sont présentes. Vérifier "
                    "les fonctionnalités conditionnelles dans le lecteur."
                )

        elif media.tag.name == "object":
            missing_actions = required_actions - action_names
            status = TestStatus.NEEDS_REVIEW
            message = (
                "Le lecteur intégré ne peut pas être évalué "
                "complètement depuis le DOM seul."
            )

        else:
            missing_actions = required_actions - action_names

            if "playback" in missing_actions:
                status = TestStatus.FAIL
                message = (
                    "Aucune commande de lecture, pause ou arrêt identifiable."
                )

            elif missing_actions:
                status = TestStatus.FAIL
                message = "Une ou plusieurs commandes requises sont absentes."

            else:
                status = TestStatus.NEEDS_REVIEW
                message = (
                    "Des commandes personnalisées sont détectées, mais leur "
                    "fonctionnement ou les besoins liés au média restent "
                    "à vérifier."
                )

        return status, Finding(
            element=element,
            message=message,
            recommendation=(
                "Vérifier la présence des commandes de lecture/pause/arrêt "
                "et, selon le média, du son, des sous-titres et "
                "de l'audiodescription."
                if status != TestStatus.PASS
                else None
            ),
            evidence={
                "native_controls": native_controls,
                "required_actions": sorted(required_actions),
                "recognized_custom_actions": sorted(action_names),
                "missing_actions": sorted(missing_actions),
                "track_kinds": sorted(tracks),
            },
        )


class Test4112(_Criterion411Test):
    """Vérifie l'accessibilité des fonctionnalités au clavier et au pointage."""

    test_id = "4.11.2"
    criterion_id = "4.11"

    def _evaluate(
        self,
        media: TemporalMedia,
        dom: BeautifulSoup,
    ) -> tuple[TestStatus, Finding]:
        controls = _associated_controls(media, dom)

        native_controls = (
            media.tag.has_attr("controls")
            and media.tag.name in {"audio", "video"}
        )

        element = _media_identifier(media)

        if native_controls:
            status = TestStatus.PASS
            message = "Le média utilise les commandes natives du navigateur."

        elif not controls:
            status = TestStatus.NOT_APPLICABLE
            message = "Aucune fonctionnalité de contrôle détectée pour ce média."

        elif any(
            not _is_keyboard_reachable(control)
            for control in controls
        ):
            status = TestStatus.FAIL
            message = (
                "Au moins une commande personnalisée "
                "n'est pas atteignable au clavier."
            )

        else:
            status = TestStatus.NEEDS_REVIEW
            message = (
                "Les commandes personnalisées semblent atteignables, "
                "mais leur accessibilité au clavier et au pointage "
                "doit être vérifiée en situation."
            )

        return status, Finding(
            element=element,
            message=message,
            recommendation=(
                "Vérifier que chaque fonctionnalité de contrôle est "
                "atteignable au clavier et avec un dispositif de pointage."
                if status in {
                    TestStatus.FAIL,
                    TestStatus.NEEDS_REVIEW,
                }
                else None
            ),
            evidence={
                "native_controls": native_controls,
                "custom_control_count": len(controls),
                "keyboard_reachable": all(
                    _is_keyboard_reachable(control)
                    for control in controls
                ),
            },
        )


class Test4113(_Criterion411Test):
    """Vérifie l'activation des fonctionnalités au clavier et au pointage."""

    test_id = "4.11.3"
    criterion_id = "4.11"

    def _evaluate(
        self,
        media: TemporalMedia,
        dom: BeautifulSoup,
    ) -> tuple[TestStatus, Finding]:
        controls = _associated_controls(media, dom)

        native_controls = (
            media.tag.has_attr("controls")
            and media.tag.name in {"audio", "video"}
        )

        element = _media_identifier(media)

        if native_controls:
            status = TestStatus.PASS
            message = "Le média utilise les commandes natives du navigateur."

        elif not controls:
            status = TestStatus.NOT_APPLICABLE
            message = "Aucune fonctionnalité de contrôle détectée pour ce média."

        elif any(
            not _is_keyboard_activatable(control)
            for control in controls
        ):
            status = TestStatus.FAIL
            message = (
                "Au moins une commande personnalisée "
                "n'est pas activable au clavier."
            )

        else:
            status = TestStatus.NEEDS_REVIEW
            message = (
                "Les commandes personnalisées ont une structure activable "
                "au clavier, mais leurs actions doivent être testées "
                "en situation."
            )

        return status, Finding(
            element=element,
            message=message,
            recommendation=(
                "Tester l'activation de chaque fonctionnalité au clavier "
                "et avec un dispositif de pointage."
                if status in {
                    TestStatus.FAIL,
                    TestStatus.NEEDS_REVIEW,
                }
                else None
            ),
            evidence={
                "native_controls": native_controls,
                "custom_control_count": len(controls),
                "keyboard_activatable": all(
                    _is_keyboard_activatable(control)
                    for control in controls
                ),
            },
        )


def _associated_controls(
    media: TemporalMedia,
    dom: BeautifulSoup,
) -> list[Tag]:
    """Recherche les contrôles associés à un média temporel."""

    candidates: list[Tag] = []
    tag = media.tag

    # Association explicite avec aria-controls.
    media_id = tag.get("id")

    if isinstance(media_id, str) and media_id.strip():
        for element in dom.find_all(True):
            aria_controls = str(
                element.get("aria-controls", "")
            ).split()

            if media_id in aria_controls and element != tag:
                candidates.append(element)

    # Contrôle juste avant le média.
    previous = tag.previous_sibling

    while isinstance(previous, NavigableString) and not previous.strip():
        previous = previous.previous_sibling

    if isinstance(previous, Tag) and _is_possible_control(previous):
        candidates.append(previous)

    # Contrôle juste après le média.
    following = tag.next_sibling

    while isinstance(following, NavigableString) and not following.strip():
        following = following.next_sibling

    if isinstance(following, Tag) and _is_possible_control(following):
        candidates.append(following)

    # Contrôles directs du parent.
    parent = tag.parent

    if isinstance(parent, Tag):
        for element in parent.find_all(
            ["button", "input", "select"],
            recursive=False,
        ):
            if element != tag:
                candidates.append(element)

        for element in parent.find_all(
            attrs={"role": True},
            recursive=False,
        ):
            if element == tag:
                continue

            role = str(
                element.get("role", "")
            ).lower()

            if role in {"button", "slider", "switch"}:
                candidates.append(element)

    # Suppression des doublons.
    candidates = list(dict.fromkeys(candidates))

    return [
        control
        for control in candidates
        if _is_media_control(control)
    ]


def _is_possible_control(tag: Tag) -> bool:
    """Détermine si un élément peut être un contrôle interactif."""

    if tag.name in {
        "button",
        "input",
        "select",
        "textarea",
    }:
        return True

    if tag.name == "a":
        return tag.has_attr("href")

    role = str(
        tag.get("role", "")
    ).lower()

    return role in {
        "button",
        "slider",
        "switch",
    }


def _is_media_control(tag: Tag) -> bool:
    """Détermine si un contrôle est identifiable comme contrôle média."""

    label = " ".join(
        str(value)
        for value in (
            tag.get("aria-label", ""),
            tag.get("title", ""),
            tag.get("name", ""),
            tag.get("id", ""),
            tag.get("value", ""),
            tag.get_text(" ", strip=True),
        )
        if value
    ).lower()

    # Un input range peut notamment correspondre à un contrôle de volume.
    if tag.name == "input":
        input_type = str(
            tag.get("type", "")
        ).lower()

        if input_type == "range":
            return True

    media_keywords = (
        "play",
        "pause",
        "stop",
        "lecture",
        "arrêt",
        "arret",
        "arrêter",
        "arreter",
        "reprendre",
        "mute",
        "unmute",
        "muet",
        "silence",
        "volume",
        "sous-titre",
        "sous-titres",
        "subtitle",
        "subtitles",
        "caption",
        "captions",
        "audiodescription",
        "audio-description",
    )

    return any(
        keyword in label
        for keyword in media_keywords
    )


def _recognized_actions(controls: list[Tag]) -> set[str]:
    """Identifie les fonctionnalités multimédias présentes."""

    actions: set[str] = set()

    for control in controls:
        label = " ".join(
            str(value)
            for value in (
                control.get("aria-label", ""),
                control.get("title", ""),
                control.get("name", ""),
                control.get("id", ""),
                control.get("value", ""),
                control.get_text(" ", strip=True),
            )
            if value
        )

        for action, pattern in _ACTION_PATTERNS.items():
            if pattern.search(label):
                actions.add(action)

    return actions


def _track_kinds(media_tag: Tag) -> set[str]:
    """Retourne les types de pistes <track> associés au média."""

    return {
        str(track.get("kind", "")).strip().lower()
        for track in media_tag.find_all("track")
    }


def _is_keyboard_reachable(control: Tag) -> bool:
    """Détermine si la structure du contrôle permet une atteinte clavier."""

    if control.has_attr("disabled"):
        return False

    if control.get("aria-disabled") == "true":
        return False

    if control.has_attr("tabindex"):
        try:
            return int(str(control["tabindex"])) >= 0
        except ValueError:
            return False

    if control.name in {
        "button",
        "select",
        "textarea",
    }:
        return True

    if control.name == "a":
        return control.has_attr("href")

    if control.name == "input":
        return str(
            control.get("type", "")
        ).lower() != "hidden"

    role = str(
        control.get("role", "")
    ).lower()

    return role in {
        "button",
        "link",
        "slider",
        "switch",
        "checkbox",
        "menuitem",
    }


def _is_keyboard_activatable(control: Tag) -> bool:
    """
    Détermine si la structure du contrôle semble activable au clavier.

    Cela ne vérifie pas que l'action JavaScript fonctionne réellement.
    """

    if not _is_keyboard_reachable(control):
        return False

    if control.name in {
        "button",
        "a",
        "input",
        "select",
        "textarea",
    }:
        return True

    return str(
        control.get("role", "")
    ).lower() in {
        "button",
        "link",
        "menuitem",
    }


def _media_identifier(media: TemporalMedia) -> str:
    """Construit un identifiant lisible pour le média."""

    media_id = media.tag.get("id")

    if isinstance(media_id, str) and media_id.strip():
        return f"{media.tag.name}#{media_id}"

    return f"{media.tag.name}[index={media.index}]"


def _aggregate_statuses(
    statuses: list[TestStatus],
) -> TestStatus:
    """
    Agrège les statuts des différents médias.

    Priorité :
    FAIL > ERROR > NEEDS_REVIEW > NOT_TESTED
    > PASS > NOT_APPLICABLE
    """

    for status in (
        TestStatus.FAIL,
        TestStatus.ERROR,
        TestStatus.NEEDS_REVIEW,
        TestStatus.NOT_TESTED,
        TestStatus.PASS,
    ):
        if status in statuses:
            return status

    return TestStatus.NOT_APPLICABLE
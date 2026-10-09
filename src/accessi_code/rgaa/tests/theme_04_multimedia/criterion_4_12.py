from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.media import is_media_exempt, media_identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


_NON_TEMPORAL_TAGS = frozenset(
    {
        "svg",
        "canvas",
        "object",
        "embed",
    }
)

_CONTROL_TAGS = frozenset(
    {
        "a",
        "button",
        "input",
        "select",
        "textarea",
        "summary",
    }
)

_CONTROL_ROLES = frozenset(
    {
        "button",
        "link",
        "checkbox",
        "combobox",
        "listbox",
        "menuitem",
        "option",
        "radio",
        "scrollbar",
        "searchbox",
        "slider",
        "spinbutton",
        "switch",
        "tab",
        "textbox",
    }
)

_CONTROL_KEYWORDS = re.compile(
    r"""
    contrôle|control|
    jouer|play|
    lecture|
    pause|
    arrêt|arreter|arrêter|stop|
    ouvrir|fermer|
    suivant|précédent|precedent|
    zoom|
    agrandir|réduire|reduire|
    \+|
    -|
    afficher|masquer|
    activer|désactiver|desactiver|
    sélectionner|selectionner|
    déplacer|deplacer|
    navigation|naviguer
    """,
    re.IGNORECASE | re.VERBOSE,
)




def _find_non_temporal_media(
    soup: BeautifulSoup,
) -> list[Tag]:
    media: list[Tag] = []

    for tag in soup.find_all(list(_NON_TEMPORAL_TAGS)):
        if not isinstance(tag, Tag):
            continue

        if is_media_exempt(tag):
            continue

        media.append(tag)

    return media


def _control_label(tag: Tag) -> str:
    values: list[str] = []

    for attribute in (
        "aria-label",
        "title",
        "name",
        "id",
        "value",
    ):
        value = tag.get(attribute)

        if value:
            values.append(str(value))

    labelledby = tag.get("aria-labelledby")

    if labelledby:
        for reference in str(labelledby).split():
            referenced = tag.find(id=reference)

            if referenced is not None:
                values.append(
                    referenced.get_text(" ", strip=True)
                )

    text = tag.get_text(" ", strip=True)

    if text:
        values.append(text)

    return " ".join(values).strip()


def _is_native_control(tag: Tag) -> bool:
    if tag.name not in _CONTROL_TAGS:
        return False

    if tag.name != "input":
        return True

    input_type = str(tag.get("type", "text")).lower()

    return input_type != "hidden"


def _is_custom_control(tag: Tag) -> bool:
    role = str(tag.get("role", "")).lower()

    if role in _CONTROL_ROLES:
        return True

    if tag.get("tabindex") is not None:
        return any(
            tag.get(attribute) is not None
            for attribute in (
                "onclick",
                "onkeydown",
                "onkeyup",
                "onkeypress",
            )
        )

    return False


def _is_control(tag: Tag) -> bool:
    return _is_native_control(tag) or _is_custom_control(tag)


def _has_control_semantics(tag: Tag) -> bool:
    if not _is_control(tag):
        return False

    role = str(tag.get("role", "")).lower()

    if role in _CONTROL_ROLES:
        return True

    if tag.get("aria-controls"):
        return True

    label = _control_label(tag)

    if _CONTROL_KEYWORDS.search(label):
        return True

    if any(
        tag.get(attribute) is not None
        for attribute in (
            "onclick",
            "onkeydown",
            "onkeyup",
            "onkeypress",
        )
    ):
        return True

    # Les contrôles HTML natifs sont eux-mêmes des fonctionnalités
    # potentielles de contrôle.
    if _is_native_control(tag):
        return True

    return False


def _direct_controls(media: Tag) -> list[Tag]:
    controls: list[Tag] = []

    for descendant in media.find_all(True):
        if not isinstance(descendant, Tag):
            continue

        if _has_control_semantics(descendant):
            controls.append(descendant)

    return controls


def _aria_controlled_controls(
    media: Tag,
    soup: BeautifulSoup,
) -> list[Tag]:
    controls: list[Tag] = []

    media_id = media.get("id")

    if not media_id:
        return controls

    for candidate in soup.find_all(True):
        if not isinstance(candidate, Tag):
            continue

        aria_controls = candidate.get("aria-controls")

        if not aria_controls:
            continue

        references = str(aria_controls).split()

        if media_id in references and _has_control_semantics(candidate):
            controls.append(candidate)

    return controls


def _nearby_controls(media: Tag) -> list[Tag]:
    controls: list[Tag] = []

    previous = media.find_previous_sibling()
    next_sibling = media.find_next_sibling()

    for sibling in (previous, next_sibling):
        if not isinstance(sibling, Tag):
            continue

        if _has_control_semantics(sibling):
            controls.append(sibling)

        for nested in sibling.find_all(True):
            if _has_control_semantics(nested):
                controls.append(nested)

    return controls


def _associated_controls(
    media: Tag,
    soup: BeautifulSoup,
) -> list[Tag]:
    controls: list[Tag] = []

    controls.extend(_direct_controls(media))
    controls.extend(_aria_controlled_controls(media, soup))
    controls.extend(_nearby_controls(media))

    unique: list[Tag] = []
    seen: set[int] = set()

    for control in controls:
        identity = id(control)

        if identity in seen:
            continue

        seen.add(identity)
        unique.append(control)

    return unique


def _is_keyboard_reachable(control: Tag) -> bool:
    if "disabled" in control.attrs:
        return False

    if control.name == "a":
        return bool(control.get("href")) or (
            control.get("tabindex") is not None
        )

    if control.name in {
        "button",
        "input",
        "select",
        "textarea",
        "summary",
    }:
        return True

    role = str(control.get("role", "")).lower()

    if role in _CONTROL_ROLES:
        return control.get("tabindex") is not None

    return control.get("tabindex") is not None


def _is_keyboard_activatable(control: Tag) -> bool:
    if "disabled" in control.attrs:
        return False

    if control.name == "button":
        return True

    if control.name == "summary":
        return True

    if control.name == "a":
        return bool(control.get("href"))

    if control.name == "input":
        input_type = str(control.get("type", "text")).lower()

        return input_type != "hidden"

    if control.name in {
        "select",
        "textarea",
    }:
        return True

    role = str(control.get("role", "")).lower()

    if role in _CONTROL_ROLES:
        return control.get("tabindex") is not None

    return False


def _aggregate_statuses(
    statuses: list[TestStatus],
) -> TestStatus:
    if not statuses:
        return TestStatus.NOT_APPLICABLE

    priority = {
        TestStatus.FAIL: 5,
        TestStatus.ERROR: 4,
        TestStatus.NEEDS_REVIEW: 3,
        TestStatus.NOT_TESTED: 2,
        TestStatus.PASS: 1,
        TestStatus.NOT_APPLICABLE: 0,
    }

    return max(
        statuses,
        key=lambda status: priority[status],
    )


class Test4121(RGAATest):
    test_id = "4.12.1"
    criterion_id = "4.12"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)
        media = _find_non_temporal_media(soup)

        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for index, element in enumerate(media):
            controls = _associated_controls(element, soup)
            identifier = media_identifier(element, index)

            if not controls:
                statuses.append(TestStatus.NOT_APPLICABLE)

                findings.append(
                    Finding(
                        element=identifier,
                        message=(
                            "Aucune fonctionnalité de contrôle "
                            "détectée pour ce média non temporel."
                        ),
                        evidence={
                            "control_count": 0,
                            "keyboard_reachable": None,
                        },
                    )
                )

                continue

            unreachable = [
                control
                for control in controls
                if not _is_keyboard_reachable(control)
            ]

            if unreachable:
                statuses.append(TestStatus.FAIL)

                findings.append(
                    Finding(
                        element=identifier,
                        message=(
                            "Une ou plusieurs fonctionnalités de "
                            "contrôle ne semblent pas accessibles "
                            "au clavier."
                        ),
                        recommendation=(
                            "Rendre chaque fonctionnalité de contrôle "
                            "accessible au clavier et avec tout "
                            "dispositif de pointage."
                        ),
                        evidence={
                            "control_count": len(controls),
                            "keyboard_reachable": False,
                            "unreachable_controls": [
                                _control_label(control)
                                or control.name
                                or "contrôle"
                                for control in unreachable
                            ],
                        },
                    )
                )

                continue

            statuses.append(TestStatus.NEEDS_REVIEW)

            findings.append(
                Finding(
                    element=identifier,
                    message=(
                        "Les fonctionnalités de contrôle semblent "
                        "accessibles au clavier par leur structure "
                        "HTML, mais leur accessibilité réelle doit "
                        "être vérifiée."
                    ),
                    recommendation=(
                        "Vérifier que chaque fonctionnalité est "
                        "atteignable au clavier et avec tout "
                        "dispositif de pointage."
                    ),
                    evidence={
                        "control_count": len(controls),
                        "keyboard_reachable": True,
                        "controls": [
                            _control_label(control)
                            or control.name
                            or "contrôle"
                            for control in controls
                        ],
                    },
                )
            )

        # Determine explicit descriptive message
        fail_count = sum(1 for s in statuses if s == TestStatus.FAIL)
        needs_review_count = sum(1 for s in statuses if s == TestStatus.NEEDS_REVIEW)

        if fail_count == 0 and needs_review_count == 0:
            # All PASS or NOT_APPLICABLE
            pass_count = sum(1 for s in statuses if s == TestStatus.PASS)
            not_applicable_count = sum(1 for s in statuses if s == TestStatus.NOT_APPLICABLE)
            if pass_count > 0:
                status_message = (
                    f"Conforme : {pass_count} média(s) non temporel(s) "
                    "avec des contrôles tous accessibles au clavier."
                )
            else:
                status_message = (
                    f"Non applicable : {len(media)} média(s) non temporel(s) détecté(s), "
                    "mais aucun n'est soumis au test d'accessibilité au clavier."
                )
        elif needs_review_count > 0:
            status_message = (
                f"À vérifier manuellement : {needs_review_count} média(s) non temporel(s) "
                "avec des contrôles nécessitant une vérification manuelle de l'accessibilité au clavier."
            )
            if fail_count > 0:
                status_message += (
                    f" De plus, {fail_count} média(s) ont des contrôles définitivement inaccessibles."
                )
        else:  # fail_count > 0 and needs_review_count == 0
            status_message = (
                f"Non conforme : {fail_count} média(s) non temporel(s) "
                "avec des contrôles inaccessibles au clavier détectés."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            _aggregate_statuses(statuses),
            status_message,
            findings=findings,
            tested_elements=len(media),
            metadata={
                "media_count": len(media),
            },
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(
                "Le test 4.12.1 nécessite un DOM."
            )

        return context.dom


class Test4122(RGAATest):
    test_id = "4.12.2"
    criterion_id = "4.12"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)
        media = _find_non_temporal_media(soup)

        if not media:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucun média non temporel détecté.",
            )

        findings: list[Finding] = []
        statuses: list[TestStatus] = []

        for index, element in enumerate(media):
            controls = _associated_controls(element, soup)
            identifier = media_identifier(element, index)

            if not controls:
                statuses.append(TestStatus.NOT_APPLICABLE)

                findings.append(
                    Finding(
                        element=identifier,
                        message=(
                            "Aucune fonctionnalité de contrôle "
                            "détectée pour ce média non temporel."
                        ),
                        evidence={
                            "control_count": 0,
                            "keyboard_activatable": None,
                        },
                    )
                )

                continue

            non_activatable = [
                control
                for control in controls
                if not _is_keyboard_activatable(control)
            ]

            if non_activatable:
                statuses.append(TestStatus.FAIL)

                findings.append(
                    Finding(
                        element=identifier,
                        message=(
                            "Une ou plusieurs fonctionnalités de "
                            "contrôle ne semblent pas activables "
                            "au clavier."
                        ),
                        recommendation=(
                            "Rendre chaque fonctionnalité activable "
                            "au clavier et avec tout dispositif "
                            "de pointage."
                        ),
                        evidence={
                            "control_count": len(controls),
                            "keyboard_activatable": False,
                            "non_activatable_controls": [
                                _control_label(control)
                                or control.name
                                or "contrôle"
                                for control in non_activatable
                            ],
                        },
                    )
                )

                continue

            statuses.append(TestStatus.NEEDS_REVIEW)

            findings.append(
                Finding(
                    element=identifier,
                    message=(
                        "Les fonctionnalités de contrôle ont une "
                        "structure activable au clavier, mais leur "
                        "action réelle doit être vérifiée."
                    ),
                    recommendation=(
                        "Tester l'activation de chaque fonctionnalité "
                        "au clavier et avec tout dispositif de pointage."
                    ),
                    evidence={
                        "control_count": len(controls),
                        "keyboard_activatable": True,
                        "controls": [
                            _control_label(control)
                            or control.name
                            or "contrôle"
                            for control in controls
                        ],
                    },
                )
            )

        # Determine explicit descriptive message
        fail_count = sum(1 for s in statuses if s == TestStatus.FAIL)
        needs_review_count = sum(1 for s in statuses if s == TestStatus.NEEDS_REVIEW)

        if fail_count == 0 and needs_review_count == 0:
            # All PASS or NOT_APPLICABLE
            pass_count = sum(1 for s in statuses if s == TestStatus.PASS)
            not_applicable_count = sum(1 for s in statuses if s == TestStatus.NOT_APPLICABLE)
            if pass_count > 0:
                status_message = (
                    f"Conforme : {pass_count} média(s) non temporel(s) "
                    "avec des contrôles tous accessibles au clavier."
                )
            else:
                status_message = (
                    f"Non applicable : {len(media)} média(s) non temporel(s) détecté(s), "
                    "mais aucun n'est soumis au test d'accessibilité au clavier."
                )
        elif needs_review_count > 0:
            status_message = (
                f"À vérifier manuellement : {needs_review_count} média(s) non temporel(s) "
                "avec des contrôles nécessitant une vérification manuelle de l'accessibilité au clavier."
            )
            if fail_count > 0:
                status_message += (
                    f" De plus, {fail_count} média(s) ont des contrôles définitivement inaccessibles."
                )
        else:  # fail_count > 0 and needs_review_count == 0
            status_message = (
                f"Non conforme : {fail_count} média(s) non temporel(s) "
                "avec des contrôles inaccessibles au clavier détectés."
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            _aggregate_statuses(statuses),
            status_message,
            findings=findings,
            tested_elements=len(media),
            metadata={
                "media_count": len(media),
            },
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(
                "Le test 4.12.2 nécessite un DOM."
            )

        return context.dom
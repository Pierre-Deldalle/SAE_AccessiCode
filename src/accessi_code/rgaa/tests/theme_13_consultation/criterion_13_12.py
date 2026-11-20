from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns for detecting DeviceMotionEvent usage
DEVICE_MOTION_PATTERNS = [
    re.compile(r"DeviceMotionEvent", re.IGNORECASE),
    re.compile(r"devicemotion", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']devicemotion[\"']", re.IGNORECASE),
    re.compile(r"ondevicemotion\s*=", re.IGNORECASE),
    # Accelerometer API
    re.compile(r"Accelerometer", re.IGNORECASE),
    re.compile(r"new\s+Accelerometer\s*\(", re.IGNORECASE),
    re.compile(r"accelerometer\.start\s*\(", re.IGNORECASE),
    # LinearAccelerationSensor
    re.compile(r"LinearAccelerationSensor", re.IGNORECASE),
    re.compile(r"new\s+LinearAccelerationSensor\s*\(", re.IGNORECASE),
    # Gyroscope
    re.compile(r"Gyroscope", re.IGNORECASE),
    re.compile(r"new\s+Gyroscope\s*\(", re.IGNORECASE),
    re.compile(r"gyroscope\.start\s*\(", re.IGNORECASE),
]

# Patterns for detecting DeviceOrientationEvent usage
DEVICE_ORIENTATION_PATTERNS = [
    re.compile(r"DeviceOrientationEvent", re.IGNORECASE),
    re.compile(r"deviceorientation", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']deviceorientation[\"']", re.IGNORECASE),
    re.compile(r"ondeviceorientation\s*=", re.IGNORECASE),
    re.compile(r"deviceorientationabsolute", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']deviceorientationabsolute[\"']", re.IGNORECASE),
    # Magnetometer / AbsoluteOrientationSensor
    re.compile(r"Magnetometer", re.IGNORECASE),
    re.compile(r"new\s+Magnetometer\s*\(", re.IGNORECASE),
    re.compile(r"AbsoluteOrientationSensor", re.IGNORECASE),
    re.compile(r"new\s+AbsoluteOrientationSensor\s*\(", re.IGNORECASE),
    re.compile(r"RelativeOrientationSensor", re.IGNORECASE),
    re.compile(r"new\s+RelativeOrientationSensor\s*\(", re.IGNORECASE),
]

# Patterns for detecting gesture/motion towards device (proximity, camera, etc.)
GESTURE_TOWARDS_DEVICE_PATTERNS = [
    # Proximity sensor
    re.compile(r"ProximitySensor", re.IGNORECASE),
    re.compile(r"new\s+ProximitySensor\s*\(", re.IGNORECASE),
    re.compile(r"proximitysensor", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']proximity[\"']", re.IGNORECASE),
    re.compile(r"onproximity\s*=", re.IGNORECASE),
    # Screen Orientation / Wake Lock (may indicate motion-based interaction)
    re.compile(r"ScreenOrientation", re.IGNORECASE),
    re.compile(r"lock\s*\(\s*[\"']portrait", re.IGNORECASE),
    re.compile(r"lock\s*\(\s*[\"']landscape", re.IGNORECASE),
    # Camera-based gestures (getUserMedia with facingMode)
    re.compile(r"getUserMedia\s*\(\s*\{[^}]*facingMode", re.IGNORECASE),
    re.compile(r"facingMode\s*:\s*[\"']environment[\"']", re.IGNORECASE),
    re.compile(r"facingMode\s*:\s*[\"']user[\"']", re.IGNORECASE),
    # Generic gesture detection libraries/patterns
    re.compile(r"hammer\.js", re.IGNORECASE),
    re.compile(r"Hammer\s*\(", re.IGNORECASE),
    re.compile(r"gesture", re.IGNORECASE),
    re.compile(r"swipe", re.IGNORECASE),
    re.compile(r"pinch", re.IGNORECASE),
    re.compile(r"rotate", re.IGNORECASE),
]

# Patterns for detecting motion/gesture disable mechanisms
MOTION_DISABLE_PATTERNS = [
    # Settings/preferences for motion reduction
    re.compile(r"prefers-reduced-motion", re.IGNORECASE),
    re.compile(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)", re.IGNORECASE),
    re.compile(r"matchMedia\s*\(\s*[\"']\(prefers-reduced-motion:\s*reduce\)[\"']", re.IGNORECASE),
    # Explicit motion/gesture toggle
    re.compile(r"disable.*motion", re.IGNORECASE),
    re.compile(r"enable.*motion", re.IGNORECASE),
    re.compile(r"motion.*toggle", re.IGNORECASE),
    re.compile(r"gesture.*toggle", re.IGNORECASE),
    re.compile(r"motion.*setting", re.IGNORECASE),
    re.compile(r"gesture.*setting", re.IGNORECASE),
    re.compile(r"désactiver.*mouvement", re.IGNORECASE),
    re.compile(r"activer.*mouvement", re.IGNORECASE),
    re.compile(r"réduire.*mouvement", re.IGNORECASE),
    re.compile(r"réduire.*animation", re.IGNORECASE),
    # Checkbox/toggle for motion
    re.compile(r"input.*type\s*=\s*[\"']checkbox[\"'].*motion", re.IGNORECASE),
    re.compile(r"input.*type\s*=\s*[\"']checkbox[\"'].*gesture", re.IGNORECASE),
    re.compile(r"role\s*=\s*[\"']switch[\"'].*motion", re.IGNORECASE),
    re.compile(r"role\s*=\s*[\"']switch[\"'].*gesture", re.IGNORECASE),
]

# Keywords for interfaces where motion is essential (cas particuliers)
ESSENTIAL_MOTION_KEYWORDS = [
    "podomètre",
    "pedometer",
    "step counter",
    "compteur de pas",
    "fitness",
    "activité physique",
    "physical activity",
    "running",
    "course",
    "jogging",
    "marche",
    "walking",
    "exercise",
    "exercice",
    "workout",
    "entraînement",
    "health",
    "santé",
    "wellness",
    "bien-être",
    "activity tracker",
    "tracker d'activité",
    "smartwatch",
    "montre connectée",
    "accéléromètre",
    "accelerometer",
    "gyroscope",
    "gps",
    "navigation",
    "compass",
    "boussole",
    "level",
    "niveau",
    "inclinometer",
    "inclinometer",
    "seismograph",
    "sismographe",
    "shake",
    "secouer",
    "shake to",
    "secouer pour",
    "motion game",
    "jeu de mouvement",
    "motion control",
    "contrôle par mouvement",
    "gesture control",
    "contrôle gestuel",
    "air gesture",
    "geste dans l'air",
    "hand tracking",
    "suivi de main",
    "body tracking",
    "suivi corporel",
    "pose estimation",
    "estimation de pose",
    "augmented reality",
    "réalité augmentée",
    "ar ",
    "vr ",
    "virtual reality",
    "réalité virtuelle",
    "mixed reality",
    "réalité mixte",
]


def _find_motion_event_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find elements/scripts using device motion events (accelerometer, gyroscope, devicemotion)."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue
        content = script.string

        matches = []
        for pattern in DEVICE_MOTION_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "type": "devicemotion",
                    "matches": matches,
                    "content_preview": content[:300],
                }
            )

    # Also check inline event handlers on elements
    all_elements = soup.find_all(True)
    for elem in all_elements:
        for attr in ["ondevicemotion"]:
            val = elem.get(attr)
            if isinstance(val, str) and val.strip():
                # Create a fake match for inline handlers
                matches = [
                    {
                        "pattern": "inline_handler",
                        "match": attr,
                        "context": val[:200],
                    }
                ]
                results.append(
                    {
                        "index": len(results),
                        "element": elem,
                        "type": "inline_devicemotion",
                        "attribute": attr,
                        "handler": val[:200],
                        "tag": elem.name,
                        "id": elem.get("id"),
                        "classes": elem.get("class", []),
                        "matches": matches,
                    }
                )

    return results


def _find_orientation_event_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find elements/scripts using device orientation events."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue
        content = script.string

        matches = []
        for pattern in DEVICE_ORIENTATION_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "type": "deviceorientation",
                    "matches": matches,
                    "content_preview": content[:300],
                }
            )

    # Inline handlers
    all_elements = soup.find_all(True)
    for elem in all_elements:
        for attr in ["ondeviceorientation", "ondeviceorientationabsolute"]:
            val = elem.get(attr)
            if isinstance(val, str) and val.strip():
                matches = [
                    {
                        "pattern": "inline_handler",
                        "match": attr,
                        "context": val[:200],
                    }
                ]
                results.append(
                    {
                        "index": len(results),
                        "element": elem,
                        "type": "inline_deviceorientation",
                        "attribute": attr,
                        "handler": val[:200],
                        "tag": elem.name,
                        "id": elem.get("id"),
                        "classes": elem.get("class", []),
                        "matches": matches,
                    }
                )

    return results


def _find_gesture_towards_device_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find elements/scripts using gesture/proximity/camera towards device."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue
        content = script.string

        matches = []
        for pattern in GESTURE_TOWARDS_DEVICE_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "type": "gesture_towards_device",
                    "matches": matches,
                    "content_preview": content[:300],
                }
            )

    # Check for getUserMedia with facingMode in HTML (video elements with specific constraints)
    videos = soup.find_all("video")
    for video in videos:
        # Check if there's a related script setting facingMode
        pass  # Hard to detect statically without JS execution

    return results


def _find_motion_disable_mechanisms(soup: BeautifulSoup) -> list[dict]:
    """Find mechanisms to disable motion/gesture detection."""
    results = []

    # Check CSS for prefers-reduced-motion
    styles = soup.find_all("style")
    for style in styles:
        if style.string:
            content = style.string
            for pattern in MOTION_DISABLE_PATTERNS:
                if pattern.search(content):
                    results.append(
                        {
                            "type": "css_prefers_reduced_motion",
                            "element": style,
                            "match": pattern.pattern,
                            "content_preview": content[:300],
                        }
                    )
                    break

    # Check scripts for motion disable logic
    scripts = soup.find_all("script")
    for script in scripts:
        if not script.string:
            continue
        content = script.string
        for pattern in MOTION_DISABLE_PATTERNS:
            if pattern.search(content):
                results.append(
                    {
                        "type": "script_motion_disable",
                        "element": script,
                        "match": pattern.pattern,
                        "content_preview": content[:300],
                    }
                )
                break

    # Check for UI controls (checkboxes, switches, buttons) related to motion/gesture
    controls = soup.find_all(["input", "button", "a", "label"])
    for control in controls:
        text = (control.get_text() or "").lower()
        control_id = (control.get("id") or "").lower()
        control_class = " ".join(control.get("class", [])).lower()
        control_aria = (control.get("aria-label") or "").lower()
        control_name = (control.get("name") or "").lower()

        combined = f"{text} {control_id} {control_class} {control_aria} {control_name}"

        motion_keywords = [
            "motion",
            "mouvement",
            "gesture",
            "geste",
            "shake",
            "secouer",
            "accelerometer",
            "accéléromètre",
            "gyroscope",
            "orientation",
            "proximity",
            "proximité",
            "reduced motion",
            "réduire mouvement",
            "réduire animation",
            "désactiver mouvement",
            "activer mouvement",
            "pause",
            "résumer",
            "reprendre",
            "resume",
            "tracking",
            "suivi",
            "start",
            "stop",
            "démarrer",
            "arrêter",
            "enable",
            "disable",
            "activer",
            "désactiver",
            "on",
            "off",
            "toggle",
            "basculer",
        ]

        if any(kw in combined for kw in motion_keywords):
            results.append(
                {
                    "type": "ui_motion_control",
                    "element": control,
                    "tag": control.name,
                    "id": control.get("id"),
                    "classes": control.get("class", []),
                    "text": text[:200],
                    "aria_label": control_aria,
                    "matched_keywords": [kw for kw in motion_keywords if kw in combined],
                }
            )

    return results


def _check_essential_motion_context(soup: BeautifulSoup) -> tuple[bool, list[str]]:
    """Check if the page appears to be an interface where motion is essential."""
    reasons = []

    # Check page title
    title_tag = soup.find("title")
    title_text = ""
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()
        for keyword in ESSENTIAL_MOTION_KEYWORDS:
            if keyword.lower() in title_text:
                reasons.append(f"Title indicates essential motion interface: '{keyword}'")
                return True, reasons

    # Check page content
    body_text = soup.get_text().lower()
    for keyword in ESSENTIAL_MOTION_KEYWORDS:
        if keyword.lower() in body_text:
            reasons.append(f"Page content indicates essential motion interface: '{keyword}'")
            return True, reasons

    # Check for specific data attributes
    elements_with_data = soup.find_all(attrs={"data-pedometer": True})
    if elements_with_data:
        reasons.append("data-pedometer attribute detected")
        return True, reasons

    elements_with_data = soup.find_all(attrs={"data-fitness": True})
    if elements_with_data:
        reasons.append("data-fitness attribute detected")
        return True, reasons

    elements_with_data = soup.find_all(attrs={"data-ar": True})
    if elements_with_data:
        reasons.append("data-ar (augmented reality) attribute detected")
        return True, reasons

    elements_with_data = soup.find_all(attrs={"data-vr": True})
    if elements_with_data:
        reasons.append("data-vr (virtual reality) attribute detected")
        return True, reasons

    elements_with_data = soup.find_all(attrs={"data-motion-game": True})
    if elements_with_data:
        reasons.append("data-motion-game attribute detected")
        return True, reasons

    return False, reasons


def _get_element_selector(soup: BeautifulSoup, element, handler_type: str, index: int) -> str:
    """Generate a readable selector for an element."""
    if element is None:
        return f"{handler_type}[index={index}]"

    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"

    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(c) for c in classes[:2])}"

    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass

    return f"{element.name}[index={index}]"


def _has_ui_alternative(soup: BeautifulSoup, motion_feature_desc: str) -> tuple[bool, list[str]]:
    """
    Check if there's a UI alternative for the motion feature.
    This is heuristic - actual verification requires manual testing.
    """
    alternatives = []

    # Look for buttons/links that might provide the same functionality
    controls = soup.find_all(["button", "a", "input", "select"])

    motion_keywords_map = {
        "shake": ["shake", "secouer", "rafraîchir", "refresh", "undo", "annuler"],
        "tilt": ["tilt", "incliner", "pencher", "navigation", "naviguer", "scroll", "défiler"],
        "rotate": ["rotate", "rotation", "pivoter", "orienter"],
        "gesture": ["gesture", "geste", "swipe", "balayer", "pinch", "pincer", "zoom"],
        "proximity": ["proximity", "proximité", "near", "proche", "hover", "survol"],
        "camera": ["camera", "caméra", "photo", "scan", "scanner", "qr", "barcode", "code-barres"],
        "step": ["step", "pas", "walk", "marche", "count", "compter"],
        "fitness": ["fitness", "exercise", "exercice", "workout", "entraînement", "activity", "activité"],
        "navigation": [
            "navigation",
            "naviguer",
            "scroll",
            "défiler",
            "nord",
            "sud",
            "est",
            "ouest",
            "north",
            "south",
            "east",
            "west",
            "boussole",
            "compass",
            "cap",
            "heading",
            "direction",
            "orienter",
            "go to",
            "aller",
            "position",
            "localiser",
        ],
        "device orientation": [
            "device orientation",
            "orientation de l'appareil",
            "deviceorientation",
            "alpha",
            "beta",
            "gamma",
            "rotate",
            "rotation",
            "gauche",
            "droite",
            "left",
            "right",
            "pivoter",
            "orienter",
        ],
        "absolute orientation": [
            "absolute orientation",
            "orientation absolue",
            "deviceorientationabsolute",
            "magnetometer",
            "magnétomètre",
            "compass",
            "boussole",
            "heading",
            "cap",
            "nord",
            "sud",
            "est",
            "ouest",
            "north",
            "south",
            "east",
            "west",
        ],
        "proximity detection": ["proximity", "proximité", "near", "proche", "proximitysensor"],
        "camera-based gesture": [
            "camera",
            "caméra",
            "getusermedia",
            "facingmode",
            "environment",
            "user",
            "scan",
            "scanner",
            "qr",
            "barcode",
            "code-barres",
            "photo",
        ],
        "touch/pointer gesture": [
            "hammer",
            "gesture",
            "geste",
            "swipe",
            "balayer",
            "pinch",
            "pincer",
            "rotate",
            "zoom",
            "touch",
            "toucher",
            "pointer",
        ],
    }

    # Find relevant keywords from the motion feature description
    relevant_keywords = []
    for category, keywords in motion_keywords_map.items():
        if category in motion_feature_desc.lower():
            relevant_keywords.extend(keywords)

    if not relevant_keywords:
        # Generic keywords - any interactive element could be an alternative
        relevant_keywords = [
            "button",
            "bouton",
            "link",
            "lien",
            "menu",
            "control",
            "contrôle",
            "action",
            "click",
            "clic",
            "press",
            "appui",
            "tap",
            "toucher",
            "submit",
            "soumettre",
            "reset",
            "réinitialiser",
            "cancel",
            "annuler",
            "undo",
            "refaire",
            "redo",
            "next",
            "suivant",
            "prev",
            "précédent",
            "previous",
            "back",
            "retour",
            "menu",
            "option",
            "setting",
            "paramètre",
            "pref",
            "préférence",
        ]

    for control in controls:
        ctrl_text = (control.get_text() or "").lower()
        ctrl_id = (control.get("id") or "").lower()
        ctrl_class = " ".join(control.get("class", [])).lower()
        ctrl_aria = (control.get("aria-label") or "").lower()

        combined = f"{ctrl_text} {ctrl_id} {ctrl_class} {ctrl_aria}"

        if any(kw in combined for kw in relevant_keywords):
            selector = _get_element_selector(soup, control, "control", 0)
            alternatives.append(f"UI control found: {selector} ({ctrl_text[:50]})")

    return len(alternatives) > 0, alternatives


class Test13121(RGAATest):
    """
    Test 13.12.1 : Dans chaque page web, les fonctionnalités disponibles en bougeant
    l'appareil peuvent-elles être accomplies avec des composants d'interface utilisateur
    (hors cas particuliers) ?

    Cas particuliers : Le mouvement est essentiel à l'accomplissement de la fonctionnalité
    (ex. podomètre) ou la détection du mouvement est utilisée pour contrôler une
    fonctionnalité au travers d'une interface compatible avec l'accessibilité.
    """

    test_id = "13.12.1"
    criterion_id = "13.12"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.12.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential motion interface (cas particulier)
        is_essential, essential_reasons = _check_essential_motion_context(soup)

        # Find device motion handlers (moving the device)
        motion_handlers = _find_motion_event_handlers(soup)

        if not motion_handlers:
            base_metadata = {
                "motion_handlers_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "compliant_count": 0,
                "is_essential_motion": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    (
                        "vérifier l'absence de gestionnaires de mouvement non détectés "
                        "(code minifié, bibliothèques externes)"
                    ),
                    "vérifier que les fonctionnalités de mouvement ont une alternative UI",
                    "identifier les cas particuliers (podomètre, fitness, AR/VR, jeu de mouvement, navigation)",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à mouvement essentiel détectée. "
                    "Le critère 13.12.1 ne s'applique pas si le mouvement est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à mouvement essentiel détectée (cas particulier). "
                        "Aucun gestionnaire de mouvement explicite trouvé. "
                        f"Raisons : {', '.join(essential_reasons)}"
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )
            else:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.PASS,
                    summary=(
                        "Aucun gestionnaire d'événement de mouvement (devicemotion, accelerometer, gyroscope) détecté. "
                        "Aucune fonctionnalité déclenchée par le mouvement de l'appareil."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each motion handler
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0
        compliant_count = 0

        for i, handler in enumerate(motion_handlers):
            selector = _get_element_selector(soup, handler["element"], handler["type"], i)
            handler_type = handler["type"]
            content_preview = handler.get("content_preview", "")

            # Try to infer what the motion feature does from context
            feature_desc = self._infer_motion_feature(content_preview, handler["matches"])

            # Check for UI alternative
            has_ui_alt, ui_alternatives = _has_ui_alternative(soup, feature_desc)

            if is_essential:
                # Cas particulier : motion is essential
                if has_ui_alt:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de mouvement détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}'. "
                                "Interface à mouvement essentiel (cas particulier) "
                                "MAIS alternative UI détectée."
                            ),
                            recommendation=(
                                "Conforme au critère 13.12.1 (cas particulier avec alternative UI). "
                                "Vérifier manuellement que l'alternative est accessible et équivalente."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": True,
                                "essential_reasons": essential_reasons,
                                "has_ui_alternative": True,
                                "ui_alternatives": ui_alternatives,
                                "matches": handler["matches"],
                            },
                        )
                    )
                else:
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de mouvement détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}'. "
                                "Interface à mouvement essentiel (cas particulier) : "
                                "AUCUNE ALTERNATIVE UI DÉTECTÉE."
                            ),
                            recommendation=(
                                "VÉRIFICATION MANUELLE REQUISE : Le critère 13.12.1 exige une alternative UI "
                                "même pour les cas particuliers si l'interface est le seul moyen d'accès. "
                                "Vérifier : "
                                "1) Si cette interface est le SEUL moyen d'accéder au service ; "
                                "2) Si oui, implémenter une alternative UI accessible "
                                "(boutons, menu, raccourcis clavier, etc.) ; "
                                "3) Si non (service accessible autrement), le critère est non applicable."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": True,
                                "essential_reasons": essential_reasons,
                                "has_ui_alternative": False,
                                "matches": handler["matches"],
                                "required_checks": [
                                    "vérifier si l'interface est le seul moyen d'accès au service",
                                    "si seul moyen : implémenter alternative UI accessible",
                                    "si autre moyen d'accès : critère non applicable",
                                ],
                            },
                        )
                    )
            else:
                # Pas un cas particulier : doit avoir alternative UI
                if has_ui_alt:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de mouvement détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}' AVEC alternative UI."
                            ),
                            recommendation=(
                                "Conforme au critère 13.12.1 : alternative UI détectée. "
                                "Vérifier manuellement l'accessibilité et l'équivalence de l'alternative."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": False,
                                "has_ui_alternative": True,
                                "ui_alternatives": ui_alternatives,
                                "matches": handler["matches"],
                            },
                        )
                    )
                else:
                    non_compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de mouvement détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}' SANS alternative UI détectée. "
                                "La fonctionnalité n'est accessible qu'en bougeant l'appareil."
                            ),
                            recommendation=(
                                "Non conforme au critère 13.12.1 : implémenter une alternative "
                                "via des composants d'interface utilisateur (boutons, liens, menus, "
                                "raccourcis clavier, commandes vocales, etc.)."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": False,
                                "has_ui_alternative": False,
                                "matches": handler["matches"],
                            },
                        )
                    )

        tested_elements = len(motion_handlers)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) de mouvement détecté(s). "
                f"{non_compliant_count} non conforme(s) (pas d'alternative UI), "
                f"{needs_review_count} à vérifier (cas particulier sans alternative), "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) de mouvement détecté(s). "
                f"{needs_review_count} cas particulier(s) sans alternative UI détectée, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) de mouvement détecté(s). "
                f"Tous ont une alternative UI (conformes au critère 13.12.1)."
            )

        metadata = {
            "motion_handlers_count": len(motion_handlers),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "compliant_count": compliant_count,
            "is_essential_motion": is_essential,
            "essential_reasons": essential_reasons,
            "required_manual_checks": [
                "vérifier l'absence de gestionnaires de mouvement non détectés (code minifié, bibliothèques externes)",
                "vérifier que chaque fonctionnalité de mouvement a une alternative UI accessible",
                "identifier les cas particuliers (podomètre, fitness, AR/VR, jeu de mouvement, navigation, boussole)",
                "si cas particulier : vérifier qu'une alternative UI est proposée si c'est le seul accès",
                "vérifier l'accessibilité clavier des alternatives UI",
                "vérifier l'équivalence fonctionnelle entre mouvement et alternative UI",
            ],
        }

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata=metadata,
        )

    def _infer_motion_feature(self, content_preview: str, matches: list) -> str:
        """Infer what the motion feature does from context."""
        content = content_preview.lower()
        match_text = " ".join(m.get("context", "").lower() for m in matches[:3])

        combined = f"{content} {match_text}"

        # Check for shake detection (acceleration threshold) - must be first
        if any(kw in combined for kw in ["shake", "secouer"]):
            return "shake (secouer l'appareil)"
        # Check for acceleration-based shake (common pattern: acceleration.x > threshold)
        elif ("acceleration" in combined or "accélération" in combined) and (
            ">" in combined or "threshold" in combined or "seuil" in combined
        ):
            return "shake (secouer l'appareil)"
        # Navigation/orientation - check before step counting
        elif any(kw in combined for kw in ["navigat", "gps", "compass", "boussole", "heading", "cap", "updatecompass"]):
            return "navigation/orientation"
        elif any(kw in combined for kw in ["tilt", "inclin", "pencher"]):
            return "tilt (incliner l'appareil)"
        elif any(kw in combined for kw in ["rotate", "rotation", "pivot", "orient"]):
            return "rotate (rotation de l'appareil)"
        elif any(kw in combined for kw in ["step", "pas", "walk", "marche", "pedometer", "podomètre"]):
            return "step counting (comptage de pas)"
        elif any(
            kw in combined
            for kw in [
                "fitness",
                "exercise",
                "exercice",
                "workout",
                "entraînement",
                "activity",
                "activité",
            ]
        ):
            return "fitness/activity tracking"
        elif any(kw in combined for kw in ["ar ", "augmented", "réalité augmentée"]):
            return "augmented reality"
        elif any(kw in combined for kw in ["vr ", "virtual", "réalité virtuelle"]):
            return "virtual reality"
        elif any(kw in combined for kw in ["game", "jeu", "play", "jouer"]):
            return "motion game"
        elif any(kw in combined for kw in ["gesture", "geste", "swipe", "pinch", "zoom"]):
            return "gesture detection"
        elif any(kw in combined for kw in ["proximity", "proximité", "near"]):
            return "proximity detection"
        elif any(kw in combined for kw in ["accelerometer", "accéléromètre", "acceleration", "accélération"]):
            return "accelerometer-based feature"
        elif any(kw in combined for kw in ["gyroscope", "gyro"]):
            return "gyroscope-based feature"
        else:
            return "motion-based feature (type non identifié)"


class Test13122(RGAATest):
    """
    Test 13.12.2 : Dans chaque page web, les fonctionnalités disponibles en faisant
    un geste en direction de l'appareil peuvent-elles être accomplies avec des
    composants d'interface utilisateur (hors cas particuliers) ?

    Cas particuliers : Le mouvement est essentiel à l'accomplissement de la fonctionnalité
    (ex. podomètre) ou la détection du mouvement est utilisée pour contrôler une
    fonctionnalité au travers d'une interface compatible avec l'accessibilité.
    """

    test_id = "13.12.2"
    criterion_id = "13.12"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.12.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential motion interface (cas particulier)
        is_essential, essential_reasons = _check_essential_motion_context(soup)

        # Find gesture towards device handlers (device orientation, proximity, camera gestures)
        orientation_handlers = _find_orientation_event_handlers(soup)
        gesture_handlers = _find_gesture_towards_device_handlers(soup)

        all_handlers = orientation_handlers + gesture_handlers

        if not all_handlers:
            base_metadata = {
                "orientation_handlers_count": len(orientation_handlers),
                "gesture_handlers_count": len(gesture_handlers),
                "total_handlers_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "compliant_count": 0,
                "is_essential_motion": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier l'absence de gestionnaires d'orientation/geste non détectés",
                    "vérifier que les fonctionnalités de geste vers l'appareil ont une alternative UI",
                    "identifier les cas particuliers (AR/VR, contrôle gestuel, caméra, proximité)",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à geste essentiel détectée. "
                    "Le critère 13.12.2 ne s'applique pas si le geste est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à geste essentiel détectée (cas particulier). "
                        "Aucun gestionnaire d'orientation/geste explicite trouvé. "
                        f"Raisons : {', '.join(essential_reasons)}"
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )
            else:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.PASS,
                    summary=(
                        "Aucun gestionnaire d'orientation (deviceorientation) ni de geste "
                        "vers l'appareil (proximité, caméra, gestuel) détecté. "
                        "Aucune fonctionnalité déclenchée par geste vers l'appareil."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each handler
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0
        compliant_count = 0

        for i, handler in enumerate(all_handlers):
            selector = _get_element_selector(soup, handler["element"], handler["type"], i)
            handler_type = handler["type"]
            content_preview = handler.get("content_preview", "")

            feature_desc = self._infer_gesture_feature(content_preview, handler["matches"])

            # Check for UI alternative
            has_ui_alt, ui_alternatives = _has_ui_alternative(soup, feature_desc)

            if is_essential:
                if has_ui_alt:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de geste/orientation détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}'. "
                                "Interface à geste essentiel (cas particulier) "
                                "MAIS alternative UI détectée."
                            ),
                            recommendation=(
                                "Conforme au critère 13.12.2 (cas particulier avec alternative UI). "
                                "Vérifier manuellement que l'alternative est accessible et équivalente."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": True,
                                "essential_reasons": essential_reasons,
                                "has_ui_alternative": True,
                                "ui_alternatives": ui_alternatives,
                                "matches": handler["matches"],
                            },
                        )
                    )
                else:
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de geste/orientation détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}'. "
                                "Interface à geste essentiel (cas particulier) : "
                                "AUCUNE ALTERNATIVE UI DÉTECTÉE."
                            ),
                            recommendation=(
                                "VÉRIFICATION MANUELLE REQUISE : Le critère 13.12.2 exige une alternative UI "
                                "même pour les cas particuliers si l'interface est le seul moyen d'accès. "
                                "Vérifier : "
                                "1) Si cette interface est le SEUL moyen d'accéder au service ; "
                                "2) Si oui, implémenter une alternative UI accessible ; "
                                "3) Si non, le critère est non applicable."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": True,
                                "essential_reasons": essential_reasons,
                                "has_ui_alternative": False,
                                "matches": handler["matches"],
                                "required_checks": [
                                    "vérifier si l'interface est le seul moyen d'accès au service",
                                    "si seul moyen : implémenter alternative UI accessible",
                                    "si autre moyen d'accès : critère non applicable",
                                ],
                            },
                        )
                    )
            else:
                if has_ui_alt:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de geste/orientation détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}' AVEC alternative UI."
                            ),
                            recommendation=(
                                "Conforme au critère 13.12.2 : alternative UI détectée. "
                                "Vérifier manuellement l'accessibilité et l'équivalence."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": False,
                                "has_ui_alternative": True,
                                "ui_alternatives": ui_alternatives,
                                "matches": handler["matches"],
                            },
                        )
                    )
                else:
                    non_compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire de geste/orientation détecté ({handler_type}) : "
                                f"fonctionnalité '{feature_desc}' SANS alternative UI détectée. "
                                "La fonctionnalité n'est accessible qu'en faisant un geste vers l'appareil."
                            ),
                            recommendation=(
                                "Non conforme au critère 13.12.2 : implémenter une alternative "
                                "via des composants d'interface utilisateur (boutons, menus, "
                                "raccourcis clavier, commandes vocales, etc.)."
                            ),
                            evidence={
                                "handler_type": handler_type,
                                "feature_description": feature_desc,
                                "is_essential_motion": False,
                                "has_ui_alternative": False,
                                "matches": handler["matches"],
                            },
                        )
                    )

        tested_elements = len(all_handlers)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'orientation/geste détecté(s). "
                f"{non_compliant_count} non conforme(s) (pas d'alternative UI), "
                f"{needs_review_count} à vérifier (cas particulier sans alternative), "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'orientation/geste détecté(s). "
                f"{needs_review_count} cas particulier(s) sans alternative UI détectée, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'orientation/geste détecté(s). "
                f"Tous ont une alternative UI (conformes au critère 13.12.2)."
            )

        metadata = {
            "orientation_handlers_count": len(orientation_handlers),
            "gesture_handlers_count": len(gesture_handlers),
            "total_handlers_count": len(all_handlers),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "compliant_count": compliant_count,
            "is_essential_motion": is_essential,
            "essential_reasons": essential_reasons,
            "required_manual_checks": [
                "vérifier l'absence de gestionnaires d'orientation/geste non détectés",
                "vérifier que chaque fonctionnalité de geste vers l'appareil a une alternative UI accessible",
                "identifier les cas particuliers (AR/VR, contrôle gestuel, caméra, proximité, boussole, niveau)",
                "si cas particulier : vérifier qu'une alternative UI est proposée si c'est le seul accès",
                "vérifier l'accessibilité clavier des alternatives UI",
                "vérifier l'équivalence fonctionnelle entre geste et alternative UI",
            ],
        }

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata=metadata,
        )

    def _infer_gesture_feature(self, content_preview: str, matches: list) -> str:
        """Infer what the gesture feature does from context."""
        content = content_preview.lower()
        match_text = " ".join(m.get("context", "").lower() for m in matches[:3])
        combined = f"{content} {match_text}"

        # Check for absolute orientation first (more specific)
        if any(
            kw in combined
            for kw in [
                "deviceorientationabsolute",
                "absolute",
                "magnetometer",
                "magnétomètre",
                "compass",
                "boussole",
            ]
        ):
            return "absolute orientation/compass (boussole)"
        elif any(kw in combined for kw in ["deviceorientation", "orientation", "alpha", "beta", "gamma"]):
            return "device orientation (orientation de l'appareil)"
        elif any(kw in combined for kw in ["proximity", "proximité", "near", "proche"]):
            return "proximity detection (détection de proximité)"
        elif any(
            kw in combined
            for kw in [
                "getusermedia",
                "facingmode",
                "environment",
                "user",
                "camera",
                "caméra",
                "video",
                "vidéo",
            ]
        ):
            return "camera-based gesture (geste via caméra)"
        elif any(
            kw in combined
            for kw in [
                "hammer",
                "gesture",
                "geste",
                "swipe",
                "balayer",
                "pinch",
                "pincer",
                "rotate",
                "rotation",
            ]
        ):
            return "touch/pointer gesture (geste tactile/pointeur)"
        elif any(kw in combined for kw in ["screenorientation", "lock", "portrait", "landscape"]):
            return "screen orientation lock (verrouillage orientation écran)"
        elif any(kw in combined for kw in ["ar ", "augmented", "réalité augmentée", "marker", "tracking", "suivi"]):
            return "augmented reality tracking"
        elif any(kw in combined for kw in ["vr ", "virtual", "réalité virtuelle", "headset", "casque"]):
            return "virtual reality interaction"
        elif any(kw in combined for kw in ["level", "niveau", "inclinometer", "inclinometer"]):
            return "level/inclinometer (niveau à bulle)"
        else:
            return "gesture towards device (geste vers l'appareil - type non identifié)"


class Test13123(RGAATest):
    """
    Test 13.12.3 : L'utilisateur a-t-il la possibilité de désactiver la détection
    du mouvement pour éviter un déclenchement accidentel de la fonctionnalité
    (hors cas particuliers) ?

    Cas particuliers : Le mouvement est essentiel à l'accomplissement de la fonctionnalité
    (ex. podomètre) ou la détection du mouvement est utilisée pour contrôler une
    fonctionnalité au travers d'une interface compatible avec l'accessibilité.
    """

    test_id = "13.12.3"
    criterion_id = "13.12"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.12.3 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential motion interface (cas particulier)
        is_essential, essential_reasons = _check_essential_motion_context(soup)

        # Find all motion/gesture handlers
        motion_handlers = _find_motion_event_handlers(soup)
        orientation_handlers = _find_orientation_event_handlers(soup)
        gesture_handlers = _find_gesture_towards_device_handlers(soup)

        all_motion_handlers = motion_handlers + orientation_handlers + gesture_handlers

        # Find motion disable mechanisms
        disable_mechanisms = _find_motion_disable_mechanisms(soup)

        if not all_motion_handlers:
            base_metadata = {
                "motion_handlers_count": 0,
                "disable_mechanisms_count": len(disable_mechanisms),
                "is_essential_motion": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier l'absence de gestionnaires de mouvement non détectés",
                    "vérifier la présence d'un mécanisme de désactivation si mouvement ajouté plus tard",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à mouvement essentiel détectée. "
                    "Le critère 13.12.3 ne s'applique pas si le mouvement est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à mouvement essentiel détectée (cas particulier). "
                        "Aucun gestionnaire de mouvement explicite trouvé. "
                        f"Raisons : {', '.join(essential_reasons)}"
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )
            else:
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.PASS,
                    summary=(
                        "Aucun gestionnaire de mouvement/orientation/geste détecté. "
                        "Aucune fonctionnalité de mouvement à désactiver."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Check if there's a disable mechanism
        has_disable_mechanism = len(disable_mechanisms) > 0
        prefers_reduced_motion = any(m["type"] == "css_prefers_reduced_motion" for m in disable_mechanisms)
        script_disable = any(m["type"] == "script_motion_disable" for m in disable_mechanisms)
        ui_control = any(m["type"] == "ui_motion_control" for m in disable_mechanisms)

        tested_elements = len(all_motion_handlers)
        findings: list[Finding] = []

        if is_essential:
            # Cas particulier : motion is essential
            if has_disable_mechanism:
                status = TestStatus.PASS
                summary = (
                    f"Interface à mouvement essentiel (cas particulier) : "
                    f"{tested_elements} gestionnaire(s) détecté(s). "
                    "Mécanisme de désactivation/réduction du mouvement détecté."
                )
                findings.append(
                    Finding(
                        element="page",
                        message=(
                            f"Cas particulier détecté ({', '.join(essential_reasons)}). "
                            f"{tested_elements} fonctionnalité(s) de mouvement. "
                            "Mécanisme de désactivation/réduction du mouvement disponible."
                        ),
                        recommendation=(
                            "Conforme au critère 13.12.3 (cas particulier avec mécanisme de désactivation). "
                            "Vérifier manuellement que la désactivation est effective et accessible."
                        ),
                        evidence={
                            "is_essential_motion": True,
                            "essential_reasons": essential_reasons,
                            "motion_handlers_count": tested_elements,
                            "has_disable_mechanism": True,
                            "prefers_reduced_motion": prefers_reduced_motion,
                            "script_disable": script_disable,
                            "ui_control": ui_control,
                            "disable_mechanisms": [
                                {
                                    "type": m["type"],
                                    "details": (
                                        m.get("matched_keywords")
                                        or m.get("match")
                                        or m.get("content_preview", "")[:100]
                                    ),
                                }
                                for m in disable_mechanisms
                            ],
                        },
                    )
                )
            else:
                status = TestStatus.NEEDS_REVIEW
                summary = (
                    f"Interface à mouvement essentiel (cas particulier) : "
                    f"{tested_elements} gestionnaire(s) détecté(s). "
                    "AUCUN MÉCANISME DE DÉSACTIVATION DU MOUVEMENT DÉTECTÉ."
                )
                findings.append(
                    Finding(
                        element="page",
                        message=(
                            f"Cas particulier détecté ({', '.join(essential_reasons)}). "
                            f"{tested_elements} fonctionnalité(s) de mouvement. "
                            "Aucun mécanisme pour désactiver/réduire la détection du mouvement."
                        ),
                        recommendation=(
                            "VÉRIFICATION MANUELLE REQUISE : "
                            "1) Vérifier si l'interface est le SEUL moyen d'accéder au service ; "
                            "2) Si oui, implémenter un mécanisme de désactivation accessible "
                            "(préférence utilisateur, toggle, respects prefers-reduced-motion, etc.) ; "
                            "3) Si non (service accessible autrement), le critère est non applicable."
                        ),
                        evidence={
                            "is_essential_motion": True,
                            "essential_reasons": essential_reasons,
                            "motion_handlers_count": tested_elements,
                            "has_disable_mechanism": False,
                            "required_checks": [
                                "vérifier si l'interface est le seul moyen d'accès au service",
                                "si seul moyen : implémenter mécanisme de désactivation accessible",
                                "si autre moyen d'accès : critère non applicable",
                            ],
                        },
                    )
                )
        else:
            # Pas un cas particulier : doit avoir mécanisme de désactivation
            if has_disable_mechanism:
                status = TestStatus.PASS
                summary = (
                    f"Analyse terminée : {tested_elements} gestionnaire(s) de mouvement détecté(s). "
                    "Mécanisme de désactivation/réduction du mouvement détecté."
                )
                findings.append(
                    Finding(
                        element="page",
                        message=(
                            f"{tested_elements} fonctionnalité(s) de mouvement détectée(s). "
                            "Mécanisme de désactivation/réduction du mouvement disponible."
                        ),
                        recommendation=(
                            "Conforme au critère 13.12.3 : mécanisme de désactivation détecté. "
                            "Vérifier manuellement que la désactivation est effective, accessible "
                            "et empêche bien les déclenchements accidentels."
                        ),
                        evidence={
                            "is_essential_motion": False,
                            "motion_handlers_count": tested_elements,
                            "has_disable_mechanism": True,
                            "prefers_reduced_motion": prefers_reduced_motion,
                            "script_disable": script_disable,
                            "ui_control": ui_control,
                            "disable_mechanisms": [
                                {
                                    "type": m["type"],
                                    "details": (
                                        m.get("matched_keywords")
                                        or m.get("match")
                                        or m.get("content_preview", "")[:100]
                                    ),
                                }
                                for m in disable_mechanisms
                            ],
                        },
                    )
                )
            else:
                status = TestStatus.FAIL
                summary = (
                    f"Analyse terminée : {tested_elements} gestionnaire(s) de mouvement détecté(s). "
                    "AUCUN MÉCANISME DE DÉSACTIVATION DU MOUVEMENT DÉTECTÉ. "
                    "Risque de déclenchement accidentel."
                )
                findings.append(
                    Finding(
                        element="page",
                        message=(
                            f"{tested_elements} fonctionnalité(s) de mouvement détectée(s) "
                            "SANS mécanisme pour désactiver/réduire la détection du mouvement. "
                            "Risque de déclenchement accidentel pour les utilisateurs "
                            "ayant des troubles moteurs ou utilisant l'appareil en mouvement."
                        ),
                        recommendation=(
                            "Non conforme au critère 13.12.3 : implémenter un mécanisme "
                            "permettant à l'utilisateur de désactiver la détection du mouvement. "
                            "Options : "
                            "1) Respecter la media query prefers-reduced-motion ; "
                            "2) Ajouter un toggle dans les paramètres/préférences ; "
                            "3) Ajouter un bouton accessible pour désactiver/réactiver ; "
                            "4) Fournir un raccourci clavier pour basculer."
                        ),
                        evidence={
                            "is_essential_motion": False,
                            "motion_handlers_count": tested_elements,
                            "has_disable_mechanism": False,
                            "handlers_types": list(set(h["type"] for h in all_motion_handlers)),
                        },
                    )
                )

        metadata = {
            "motion_handlers_count": len(motion_handlers),
            "orientation_handlers_count": len(orientation_handlers),
            "gesture_handlers_count": len(gesture_handlers),
            "total_motion_handlers": tested_elements,
            "disable_mechanisms_count": len(disable_mechanisms),
            "has_disable_mechanism": has_disable_mechanism,
            "prefers_reduced_motion": prefers_reduced_motion,
            "script_disable": script_disable,
            "ui_control": ui_control,
            "is_essential_motion": is_essential,
            "essential_reasons": essential_reasons,
            "required_manual_checks": [
                "vérifier l'absence de gestionnaires de mouvement non détectés",
                "vérifier que le mécanisme de désactivation est accessible (clavier, lecteur d'écran)",
                "vérifier que la désactivation empêche bien les déclenchements accidentels",
                "vérifier le respect de prefers-reduced-motion",
                "identifier les cas particuliers (podomètre, fitness, AR/VR, jeu, navigation)",
                "si cas particulier : vérifier mécanisme de désactivation si seul accès",
            ],
        }

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata=metadata,
        )

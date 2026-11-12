from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


# Patterns to detect multi-touch handling in JavaScript (2+ fingers)
MULTI_TOUCH_PATTERNS = [
    # Touch event with multiple touches (touches.length > 1, >= 2, etc.)
    re.compile(r"touches\.length\s*(?:>=?|!=|==|<=?)\s*\d+", re.IGNORECASE),
    re.compile(r"changedTouches\.length\s*(?:>=?|!=|==|<=?)\s*\d+", re.IGNORECASE),
    re.compile(r"targetTouches\.length\s*(?:>=?|!=|==|<=?)\s*\d+", re.IGNORECASE),
    # Multi-touch event properties (accessing 2nd touch)
    re.compile(r"event\.touches\[1\]", re.IGNORECASE),
    re.compile(r"event\.touches\[2\]", re.IGNORECASE),
    re.compile(r"event\.changedTouches\[1\]", re.IGNORECASE),
    re.compile(r"event\.targetTouches\[1\]", re.IGNORECASE),
    # Gesture events (non-standard but used for multi-touch)
    re.compile(r"gesturestart", re.IGNORECASE),
    re.compile(r"gesturechange", re.IGNORECASE),
    re.compile(r"gestureend", re.IGNORECASE),
    # Scale/rotation detection (pinch zoom, rotate - typically 2 fingers)
    re.compile(r"event\.scale", re.IGNORECASE),
    re.compile(r"event\.rotation", re.IGNORECASE),
    # Touch point distance calculation (pinch detection)
    re.compile(r"Math\.hypot\s*\(", re.IGNORECASE),
    re.compile(r"distance\s*\(\s*.*touches", re.IGNORECASE),
    re.compile(r"getDistance\s*\(", re.IGNORECASE),
    # Hammer.js / similar gesture libraries (multi-touch gestures)
    re.compile(r"Hammer\s*\(", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']pinch", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']rotate", re.IGNORECASE),
    re.compile(r"new\s+Hammer", re.IGNORECASE),
    # Pointer events with multiple pointers
    re.compile(r"activePointers", re.IGNORECASE),
    re.compile(r"pointerMap", re.IGNORECASE),
    # Explicit multi-touch keywords (more specific to avoid comment matches)
    re.compile(r"\bmultiTouch\b", re.IGNORECASE),
    re.compile(r"\btwoFinger\b", re.IGNORECASE),
    re.compile(r"\bpinch\b", re.IGNORECASE),
]

# Patterns to detect path-based gestures (trajectory following)
PATH_GESTURE_PATTERNS = [
    # Pattern drawing / gesture recognition
    re.compile(r"gesture.*recogn", re.IGNORECASE),
    re.compile(r"pattern.*lock", re.IGNORECASE),
    re.compile(r"draw.*pattern", re.IGNORECASE),
    re.compile(r"signature.*pad", re.IGNORECASE),
    re.compile(r"signature.*canvas", re.IGNORECASE),
    # Touch trajectory tracking
    re.compile(r"touchmove.*path", re.IGNORECASE),
    re.compile(r"track.*touch", re.IGNORECASE),
    re.compile(r"record.*touch", re.IGNORECASE),
    re.compile(r"touch.*trajector", re.IGNORECASE),
    re.compile(r"points\[\]\s*=\s*\[\]", re.IGNORECASE),
    re.compile(r"path\.push\s*\(", re.IGNORECASE),
    # Canvas-based drawing
    re.compile(r"ctx\.beginPath\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"ctx\.moveTo\s*\(", re.IGNORECASE),
    re.compile(r"ctx\.lineTo\s*\(", re.IGNORECASE),
    re.compile(r"ctx\.stroke\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"canvas.*draw", re.IGNORECASE),
    # Virtual keyboard pattern
    re.compile(r"virtual.*keyboard", re.IGNORECASE),
    re.compile(r"onScreenKeyboard", re.IGNORECASE),
    re.compile(r"pattern.*unlock", re.IGNORECASE),
    # Swipe/carousel with trajectory (single finger path)
    re.compile(r"swipe", re.IGNORECASE),
    re.compile(r"drag.*drop", re.IGNORECASE),
    re.compile(r"carousel", re.IGNORECASE),
    re.compile(r"slider", re.IGNORECASE),
    # Touch path tracking variables
    re.compile(r"startX", re.IGNORECASE),
    re.compile(r"startY", re.IGNORECASE),
    re.compile(r"endX", re.IGNORECASE),
    re.compile(r"endY", re.IGNORECASE),
    re.compile(r"deltaX", re.IGNORECASE),
    re.compile(r"deltaY", re.IGNORECASE),
]

# Patterns for alternative single-point controls
SINGLE_POINT_ALTERNATIVE_PATTERNS = [
    # Navigation buttons
    re.compile(r"prev(?:ious)?\s*[=:]", re.IGNORECASE),
    re.compile(r"next\s*[=:]", re.IGNORECASE),
    re.compile(r"previous\s*[=:]", re.IGNORECASE),
    re.compile(r"button.*prev", re.IGNORECASE),
    re.compile(r"button.*next", re.IGNORECASE),
    # Zoom controls
    re.compile(r"zoom\s*[+-]", re.IGNORECASE),
    re.compile(r"zoomIn", re.IGNORECASE),
    re.compile(r"zoomOut", re.IGNORECASE),
    re.compile(r"scale\s*[+-]", re.IGNORECASE),
    re.compile(r"\.zoom\s*\(", re.IGNORECASE),
    # Carousel/slider controls
    re.compile(r"carousel", re.IGNORECASE),
    re.compile(r"slider", re.IGNORECASE),
    re.compile(r"pagination", re.IGNORECASE),
    re.compile(r"dot.*nav", re.IGNORECASE),
    # Keyboard/pattern alternatives
    re.compile(r"keypad", re.IGNORECASE),
    re.compile(r"num(?:ber)?pad", re.IGNORECASE),
    re.compile(r"pin.*input", re.IGNORECASE),
    re.compile(r"password.*input", re.IGNORECASE),
    re.compile(r"text.*input", re.IGNORECASE),
    # Generic alternative indicators
    re.compile(r"alternative", re.IGNORECASE),
    re.compile(r"accessible", re.IGNORECASE),
    re.compile(r"fallback", re.IGNORECASE),
]

# Keywords for interfaces where complex gestures are essential (cas particuliers)
ESSENTIAL_GESTURE_KEYWORDS = [
    "signature",
    "sign",
    "signez",
    "sign here",
    "dessin",
    "drawing",
    "sketch",
    "esquisse",
    "peinture",
    "paint",
    "handwriting",
    "écriture",
    "calligraphie",
    "calligraphy",
    "gesture.*password",
    "pattern.*lock",
    "pattern.*unlock",
    "trajectory",
    "trajectoire",
    "freehand",
    "à main levée",
    "dessin libre",
    "free drawing",
]


def _find_multi_touch_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find JavaScript that handles multi-touch gestures."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        for pattern in MULTI_TOUCH_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 150)
                end = min(len(content), match.end() + 250)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )

        if matches:
            # Categorize the type of multi-touch - create separate entry per gesture type
            content_lower = content.lower()
            gesture_types = []
            if any(kw in content_lower for kw in ["pinch", "scale", "zoom"]):
                gesture_types.append("pinch_zoom")
            if any(kw in content_lower for kw in ["rotate", "rotation"]):
                gesture_types.append("rotate")
            if any(kw in content_lower for kw in ["swipe", "drag"]):
                gesture_types.append("swipe_drag")
            if any(kw in content_lower for kw in ["hammer", "gesture"]):
                gesture_types.append("gesture_library")

            # Create separate result entry for each gesture type for better granularity
            for gt in gesture_types if gesture_types else ["unknown"]:
                results.append(
                    {
                        "index": i,
                        "element": script,
                        "matches": matches,
                        "content_preview": content[:300],
                        "gesture_types": [gt],
                    }
                )

    return results


def _find_path_gesture_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find JavaScript that handles path-based gestures (trajectory following)."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        for pattern in PATH_GESTURE_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 150)
                end = min(len(content), match.end() + 250)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )

        if matches:
            # Categorize the type of path gesture - collect ALL matching types
            content_lower = content.lower()
            gesture_types = []
            # Pattern lock: look for pattern, unlock, lock, or points array for pattern
            if any(kw in content_lower for kw in ["pattern", "unlock", "lock", "points.push", "drawpath"]):
                gesture_types.append("pattern_lock")
            # Signature drawing
            if any(kw in content_lower for kw in ["signature", "sign", "signez", "sign here"]):
                gesture_types.append("signature_drawing")
            # Virtual keyboard
            if any(kw in content_lower for kw in ["virtual keyboard", "onScreenKeyboard", "keypad"]):
                gesture_types.append("virtual_keyboard")
            # Swipe/carousel
            if any(kw in content_lower for kw in ["swipe", "carousel", "slider"]):
                gesture_types.append("swipe_drag")
            # Drag/drop
            if any(kw in content_lower for kw in ["drag", "drop"]):
                gesture_types.append("drag_drop")
            # Canvas drawing
            if any(kw in content_lower for kw in ["dessin", "drawing", "sketch", "handwriting"]):
                gesture_types.append("canvas_drawing")
            # Trajectory tracking
            if any(kw in content_lower for kw in ["canvas", "path", "trajector", "startx", "starty", "deltax", "deltay"]):
                gesture_types.append("trajectory_tracking")

            # Create separate result entry for each gesture type for better granularity
            for gt in gesture_types if gesture_types else ["unknown"]:
                results.append(
                    {
                        "index": i,
                        "element": script,
                        "matches": matches,
                        "content_preview": content[:300],
                        "gesture_types": [gt],
                    }
                )

    return results


def _check_essential_gesture_context(soup: BeautifulSoup) -> tuple[bool, list[str]]:
    """
    Check if the page appears to be an interface where complex gestures are essential.
    Returns (is_essential, reasons).
    Only clearly essential interfaces: signature pads, drawing/sketch apps, pattern locks.
    """
    reasons = []

    # Check page title for clear essential indicators
    title_tag = soup.find("title")
    title_text = ""
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()
        # Strong indicators in title
        strong_indicators = [
            "signature",
            "signez",
            "sign here",
            "pattern lock",
            "pattern unlock",
            "déverrouillage",
            "gesture password",
            "mot de passe gestuel",
            "dessin libre",
            "free drawing",
            "sketch",
            "signature pad",
            "dessin accessible",
            "drawing accessible",
        ]
        for indicator in strong_indicators:
            if indicator in title_text:
                reasons.append(f"Title indicates essential gesture: '{indicator}'")
                return True, reasons

    # Check for canvas with drawing-related context when title suggests drawing
    canvas_elements = soup.find_all("canvas")
    if canvas_elements and ("dessin" in title_text or "drawing" in title_text or "sketch" in title_text):
        for canvas in canvas_elements:
            canvas_id = canvas.get("id", "").lower()
            canvas_class = " ".join(canvas.get("class", [])).lower()
            if any(kw in f"{canvas_id} {canvas_class}" for kw in ["draw", "dessin", "sketch", "paint", "signature", "sign"]):
                reasons.append("Canvas with drawing context in page titled for drawing")
                return True, reasons

    # Check for canvas with strong essential indicators in ID/class
    canvas_elements = soup.find_all("canvas")
    for canvas in canvas_elements:
        canvas_id = canvas.get("id", "").lower()
        canvas_class = " ".join(canvas.get("class", [])).lower()
        canvas_text = f"{canvas_id} {canvas_class}"
        # Strong indicators for canvas
        strong_canvas_indicators = [
            "signature",
            "signpad",
            "sign-pad",
            "patternlock",
            "pattern-lock",
            "drawingpad",
            "drawing-pad",
            "sketchpad",
            "sketch-pad",
            "freedraw",
            "free-draw",
        ]
        for indicator in strong_canvas_indicators:
            if indicator in canvas_text:
                reasons.append(f"Canvas element strongly suggests essential gesture: '{indicator}'")
                return True, reasons

    # Check for specific input elements
    inputs = soup.find_all("input")
    for inp in inputs:
        input_type = inp.get("type", "").lower()
        input_id = inp.get("id", "").lower()
        input_class = " ".join(inp.get("class", [])).lower()
        input_text = f"{input_type} {input_id} {input_class}"
        if any(kw in input_text for kw in ["patternlock", "pattern-lock", "signature", "signpad"]):
            reasons.append(f"Input element suggests essential gesture functionality")
            return True, reasons

    # Check body text for strong indicators
    body_text = soup.get_text().lower()
    strong_body_indicators = [
        "signez ici",
        "sign here",
        "tracez votre signature",
        "pattern de déverrouillage",
        "pattern unlock",
        "gesture password",
        "mot de passe gestuel",
        "dessin à main levée",
        "freehand drawing",
    ]
    for indicator in strong_body_indicators:
        if indicator in body_text:
            reasons.append(f"Page content strongly indicates essential gesture: '{indicator}'")
            return True, reasons

    return False, reasons


def _has_single_point_alternative(soup: BeautifulSoup, gesture_type: str, is_essential: bool = False) -> tuple[bool, list[str]]:
    """
    Check if there's an alternative single-point control for the given gesture type.
    Returns (has_alternative, alternative_types_found).
    """
    alternatives_found = []

    # Get all interactive elements
    interactive_elements = soup.find_all(["button", "a", "input", "select", "textarea", "nav"])

    # Also check for elements with click handlers
    all_elements = soup.find_all(True)
    for elem in all_elements:
        for attr in ["onclick", "onmousedown", "onpointerdown"]:
            if elem.get(attr):
                interactive_elements.append(elem)
                break

    # Check text content, aria-label, title, id, class, onclick for alternative keywords
    search_texts = []
    for elem in interactive_elements:
        texts_to_check = []
        # Element text content
        if elem.string:
            texts_to_check.append(elem.string.lower())
        # Attributes including onclick handlers
        for attr in ["aria-label", "title", "alt", "id", "class", "name", "data-testid", "onclick", "onmousedown", "onpointerdown"]:
            val = elem.get(attr, "")
            if isinstance(val, str):
                texts_to_check.append(val.lower())
            elif isinstance(val, list):
                texts_to_check.extend([str(v).lower() for v in val])

        search_texts.extend(texts_to_check)

    # Also check for pagination/nav elements specifically for carousel/slider
    # Only consider actual navigation controls (nav, ul, ol with pagination class, or elements with role=navigation)
    if gesture_type in ["swipe_drag", "carousel", "swipe"]:
        pagination_elements = soup.find_all(
            class_=re.compile(r"pagination|slider-nav|carousel-nav|pagination-nav", re.IGNORECASE)
        )
        # Also check nav elements and elements with role=navigation
        nav_elements = soup.find_all(["nav"])
        nav_elements.extend(soup.find_all(attrs={"role": "navigation"}))
        all_nav_elements = pagination_elements + nav_elements
        for elem in all_nav_elements:
            for attr in ["class", "id", "aria-label"]:
                val = elem.get(attr, "")
                if isinstance(val, str):
                    search_texts.append(val.lower())
                elif isinstance(val, list):
                    search_texts.extend([str(v).lower() for v in val])

    combined_text = " ".join(search_texts)

    # Check for alternatives based on gesture type
    if gesture_type in ["pinch_zoom"]:
        zoom_alts = ["zoom", "zoom in", "zoom out", "agrandir", "réduire", "+", "-", "plus", "moins", "scale", "zoomin", "zoomout"]
        for alt in zoom_alts:
            if alt in combined_text:
                alternatives_found.append(f"zoom_control_{alt}")
                break

    if gesture_type in ["rotate"]:
        rotate_alts = ["rotate", "rotation", "pivoter", "turn", "left", "right", "gauche", "droite", "rotateleft", "rotateright"]
        for alt in rotate_alts:
            if alt in combined_text:
                alternatives_found.append(f"rotate_control_{alt}")
                break

    if gesture_type in ["swipe_drag", "carousel", "swipe", "trajectory_tracking"]:
        nav_alts = ["prev", "previous", "précédent", "next", "suivant", "carousel", "slider", "pagination", "dot", "page"]
        for alt in nav_alts:
            if alt in combined_text:
                alternatives_found.append(f"nav_control_{alt}")
                break

    if gesture_type in ["pattern_lock", "virtual_keyboard"]:
        input_alts = ["keypad", "num pad", "numpad", "pin", "password", "text input", "clavier", "chiffres", "input", "text"]
        for alt in input_alts:
            if alt in combined_text:
                alternatives_found.append(f"input_alternative_{alt}")
                break

    if gesture_type in ["canvas_drawing", "signature_drawing", "trajectory_tracking", "drag_drop"]:
        # For drawing/signature, alternatives are file upload, text input, etc.
        input_alts = ["file", "upload", "import", "text", "saisir", "écrire", "input", "name", "nom", "signature"]
        for alt in input_alts:
            if alt in combined_text:
                alternatives_found.append(f"input_alternative_{alt}")
                break

    # For essential gestures, also check for any generic input/alternative
    if is_essential and not alternatives_found:
        generic_alts = ["file", "upload", "import", "text", "input", "name", "nom", "signature", "saisir", "écrire", "accessible", "alternative", "fallback"]
        for alt in generic_alts:
            if alt in combined_text:
                alternatives_found.append(f"generic_essential_alternative_{alt}")
                break

    # Generic accessible/alternative indicators
    if "accessible" in combined_text or "alternative" in combined_text or "fallback" in combined_text:
        alternatives_found.append("generic_accessible_alternative")

    return len(alternatives_found) > 0, alternatives_found


def _get_element_selector(soup: BeautifulSoup, element, tag: str, index: int) -> str:
    """Generate a readable selector for an element."""
    if element is None:
        return f"{tag}[index={index}]"

    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"

    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

    same_tag = soup.find_all(tag)
    if len(same_tag) > 1:
        try:
            return f"{tag}[index={same_tag.index(element)}]"
        except ValueError:
            pass

    return f"{tag}[index={index}]"


class Test13101(RGAATest):
    """
    Test 13.10.1 : Dans chaque page web, chaque fonctionnalité utilisable ou disponible
    suite à un contact multipoint est-elle également utilisable ou disponible suite à un
    contact en un point unique de l'écran (hors cas particuliers).

    Exemple : la possibilité de consulter les éléments d'une liste par un mouvement de
    balayage horizontal droit ou gauche doit aussi être disponible au moyen de boutons
    "précédent" et "suivant" ou encore un geste de pincer et zoomer qui peut être
    alternativement réalisé au moyen de boutons "plus" et "moins".
    """

    test_id = "13.10.1"
    criterion_id = "13.10"

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
                summary="Le DOM n'est pas disponible ; le test 13.10.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential gesture interface (cas particulier)
        is_essential, essential_reasons = _check_essential_gesture_context(soup)

        # Find all multi-touch handlers
        multi_touch_handlers = _find_multi_touch_handlers(soup)

        if not multi_touch_handlers:
            base_metadata = {
                "multi_touch_handlers_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "is_essential_gesture": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier l'absence de gestes multipoints non détectés (bibliothèques externes, code minifié)",
                    "vérifier que les fonctionnalités tactiles ont une alternative au clic simple",
                    "identifier les cas particuliers (signature, dessin, pattern lock essentiel)",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à geste essentiel détectée. "
                    "Le critère 13.10.1 ne s'applique pas si le geste multipoint est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à geste multipoint essentiel détectée (cas particulier). "
                        f"Aucun gestionnaire multipoint explicite trouvé. Raisons : {', '.join(essential_reasons)}"
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
                        "Aucun gestionnaire de geste multipoint détecté. "
                        "Les fonctionnalités devraient être accessibles au contact simple."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each multi-touch handler
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0

        for i, handler in enumerate(multi_touch_handlers):
            selector = _get_element_selector(soup, handler["element"], "script", i)
            gesture_types = handler.get("gesture_types", ["unknown"])

            for gesture_type in gesture_types:
                # Check for single-point alternative
                has_alternative, alt_types = _has_single_point_alternative(soup, gesture_type, is_essential)

                if is_essential:
                    # Cas particulier : vérifier s'il y a une alternative
                    if has_alternative:
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste multipoint '{gesture_type}' détecté. "
                                    "Interface à geste essentiel (cas particulier) MAIS alternative détectée."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.10.1 (cas particulier avec alternative). "
                                    "Vérifier manuellement que l'alternative permet un accès équivalent."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": True,
                                    "essential_reasons": essential_reasons,
                                    "has_alternative": True,
                                    "alternative_types": alt_types,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )
                    else:
                        needs_review_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste multipoint '{gesture_type}' détecté. "
                                    "Interface à geste essentiel (cas particulier) : "
                                    "AUCUNE ALTERNATIVE DÉTECTÉE pour contact simple."
                                ),
                                recommendation=(
                                    "CRITIQUE : Le critère 13.10.1 exige une alternative "
                                    "si l'interface est le seul moyen d'accéder au service. "
                                    "Vérifier manuellement : "
                                    "1) Si cette interface est le SEUL moyen d'accès au service ; "
                                    "2) Si oui, implémenter une alternative accessible "
                                    "(boutons, clavier, etc.) ; "
                                    "3) Si non (service accessible autrement), "
                                    "le critère est non applicable."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": True,
                                    "essential_reasons": essential_reasons,
                                    "has_alternative": False,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                    "required_checks": [
                                        "vérifier si l'interface est le seul moyen d'accès au service",
                                        "si seul moyen : implémenter alternative accessible",
                                        "si autre moyen d'accès : critère non applicable",
                                    ],
                                },
                            )
                        )
                else:
                    # Pas un cas particulier : toute fonctionnalité multipoint doit avoir une alternative
                    if has_alternative:
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste multipoint '{gesture_type}' détecté avec alternative au contact simple."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.10.1 : alternative détectée. "
                                    "Vérifier manuellement l'accessibilité de l'alternative."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": False,
                                    "has_alternative": True,
                                    "alternative_types": alt_types,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )
                    else:
                        non_compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste multipoint '{gesture_type}' détecté SANS alternative au contact simple. "
                                    "Cette fonctionnalité n'est pas accessible aux utilisateurs "
                                    "ne pouvant pas effectuer de gestes multipoints."
                                ),
                                recommendation=(
                                    f"Non conforme au critère 13.10.1 : implémenter une alternative "
                                    f"au contact simple pour le geste '{gesture_type}'. "
                                    "Exemples : boutons précédent/suivant pour swipe, "
                                    "boutons +/- pour pincer-zoomer, clavier pour pattern lock."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": False,
                                    "has_alternative": False,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )

        tested_elements = len(multi_touch_handlers)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) multipoint détecté(s). "
                f"{non_compliant_count} sans alternative (non conforme), "
                f"{needs_review_count} à vérifier (cas particulier sans alternative)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) multipoint détecté(s). "
                f"{needs_review_count} cas particulier(s) sans alternative détectée."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) multipoint détecté(s). "
                f"Tous ont une alternative au contact simple."
            )

        metadata = {
            "multi_touch_handlers_count": len(multi_touch_handlers),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "is_essential_gesture": is_essential,
            "essential_reasons": essential_reasons,
            "gesture_types_found": list(set(
                gt for h in multi_touch_handlers for gt in h.get("gesture_types", [])
            )),
            "required_manual_checks": [
                "vérifier l'absence de gestes multipoints non détectés (bibliothèques externes, code minifié)",
                "vérifier que les alternatives au contact simple sont accessibles au clavier",
                "vérifier que les alternatives sont visibles et compréhensibles",
                "identifier les cas particuliers (signature, dessin, pattern lock essentiel)",
                "si cas particulier : vérifier qu'une alternative est proposée si c'est le seul accès",
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


class Test13102(RGAATest):
    """
    Test 13.10.2 : Dans chaque page web, chaque fonctionnalité utilisable ou disponible
    suite à un geste basé sur le suivi d'une trajectoire sur l'écran est-elle également
    utilisable ou disponible suite à un contact en un point unique de l'écran
    (hors cas particuliers).

    Exemple : la possibilité de composer son mot de passe en suivant une trajectoire sur
    un clavier virtuel doit aussi être disponible au moyen de pressions successives sur
    les touches du clavier.
    """

    test_id = "13.10.2"
    criterion_id = "13.10"

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
                summary="Le DOM n'est pas disponible ; le test 13.10.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential gesture interface (cas particulier)
        is_essential, essential_reasons = _check_essential_gesture_context(soup)

        # Find all path-based gesture handlers
        path_gesture_handlers = _find_path_gesture_handlers(soup)

        if not path_gesture_handlers:
            base_metadata = {
                "path_gesture_handlers_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "is_essential_gesture": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier l'absence de gestes par trajectoire non détectés",
                    "vérifier que les fonctionnalités par trajectoire ont une alternative au point unique",
                    "identifier les cas particuliers (signature, dessin libre, pattern lock essentiel)",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à geste par trajectoire essentiel détectée. "
                    "Le critère 13.10.2 ne s'applique pas si le suivi de trajectoire est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à geste par trajectoire essentiel détectée (cas particulier). "
                        f"Aucun gestionnaire de trajectoire explicite trouvé. Raisons : {', '.join(essential_reasons)}"
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
                        "Aucun gestionnaire de geste par trajectoire détecté. "
                        "Les fonctionnalités devraient être accessibles au contact simple."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each path gesture handler
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0

        for i, handler in enumerate(path_gesture_handlers):
            selector = _get_element_selector(soup, handler["element"], "script", i)
            gesture_types = handler.get("gesture_types", ["unknown"])

            for gesture_type in gesture_types:
                # Check for single-point alternative
                has_alternative, alt_types = _has_single_point_alternative(soup, gesture_type, is_essential)

                if is_essential:
                    # Cas particulier : vérifier s'il y a une alternative
                    if has_alternative:
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste par trajectoire '{gesture_type}' détecté. "
                                    "Interface à geste essentiel (cas particulier) MAIS alternative détectée."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.10.2 (cas particulier avec alternative). "
                                    "Vérifier manuellement que l'alternative permet un accès équivalent."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": True,
                                    "essential_reasons": essential_reasons,
                                    "has_alternative": True,
                                    "alternative_types": alt_types,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )
                    else:
                        needs_review_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste par trajectoire '{gesture_type}' détecté. "
                                    "Interface à geste essentiel (cas particulier) : "
                                    "AUCUNE ALTERNATIVE DÉTECTÉE pour contact en point unique."
                                ),
                                recommendation=(
                                    "CRITIQUE : Le critère 13.10.2 exige une alternative "
                                    "si l'interface est le seul moyen d'accéder au service. "
                                    "Vérifier manuellement : "
                                    "1) Si cette interface est le SEUL moyen d'accès au service ; "
                                    "2) Si oui, implémenter une alternative accessible "
                                    "(saisie clavier, boutons, etc.) ; "
                                    "3) Si non (service accessible autrement), "
                                    "le critère est non applicable."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": True,
                                    "essential_reasons": essential_reasons,
                                    "has_alternative": False,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                    "required_checks": [
                                        "vérifier si l'interface est le seul moyen d'accès au service",
                                        "si seul moyen : implémenter alternative accessible",
                                        "si autre moyen d'accès : critère non applicable",
                                    ],
                                },
                            )
                        )
                else:
                    # Pas un cas particulier : toute fonctionnalité par trajectoire doit avoir une alternative
                    if has_alternative:
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste par trajectoire '{gesture_type}' détecté avec alternative au point unique."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.10.2 : alternative détectée. "
                                    "Vérifier manuellement l'accessibilité de l'alternative."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": False,
                                    "has_alternative": True,
                                    "alternative_types": alt_types,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )
                    else:
                        non_compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Geste par trajectoire '{gesture_type}' détecté SANS alternative au point unique. "
                                    "Cette fonctionnalité n'est pas accessible aux utilisateurs "
                                    "ne pouvant pas suivre une trajectoire sur l'écran."
                                ),
                                recommendation=(
                                    f"Non conforme au critère 13.10.2 : implémenter une alternative "
                                    f"au point unique pour le geste '{gesture_type}'. "
                                    "Exemples : saisie au clavier pour pattern lock, "
                                    "boutons pour carousel/swipe, formulaire pour signature."
                                ),
                                evidence={
                                    "gesture_type": gesture_type,
                                    "is_essential_gesture": False,
                                    "has_alternative": False,
                                    "matches": [{k: v for k, v in m.items() if k != "element"} for m in handler["matches"]],
                                },
                            )
                        )

        tested_elements = len(path_gesture_handlers)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) par trajectoire détecté(s). "
                f"{non_compliant_count} sans alternative (non conforme), "
                f"{needs_review_count} à vérifier (cas particulier sans alternative)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) par trajectoire détecté(s). "
                f"{needs_review_count} cas particulier(s) sans alternative détectée."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) par trajectoire détecté(s). "
                f"Tous ont une alternative au point unique."
            )

        metadata = {
            "path_gesture_handlers_count": len(path_gesture_handlers),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "is_essential_gesture": is_essential,
            "essential_reasons": essential_reasons,
            "gesture_types_found": list(set(
                gt for h in path_gesture_handlers for gt in h.get("gesture_types", [])
            )),
            "required_manual_checks": [
                "vérifier l'absence de gestes par trajectoire non détectés (code minifié, bibliothèques)",
                "vérifier que les alternatives au point unique sont accessibles au clavier",
                "vérifier que les alternatives sont visibles et compréhensibles",
                "identifier les cas particuliers (signature, dessin libre, pattern lock essentiel)",
                "si cas particulier : vérifier qu'une alternative est proposée si c'est le seul accès",
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
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns to detect pointer down event handlers (mousedown, pointerdown, touchstart)
POINTER_DOWN_PATTERNS = [
    # HTML event attributes
    re.compile(r"\bonmousedown\s*=", re.IGNORECASE),
    re.compile(r"\bonpointerdown\s*=", re.IGNORECASE),
    re.compile(r"\bontouchstart\s*=", re.IGNORECASE),
    # addEventListener patterns
    re.compile(r"addEventListener\s*\(\s*[\"']mousedown[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']pointerdown[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']touchstart[\"']", re.IGNORECASE),
    # React/Vue/Angular style handlers
    re.compile(r"onMouseDown\s*=", re.IGNORECASE),
    re.compile(r"onPointerDown\s*=", re.IGNORECASE),
    re.compile(r"onTouchStart\s*=", re.IGNORECASE),
    re.compile(r"@mousedown\s*=", re.IGNORECASE),
    re.compile(r"@pointerdown\s*=", re.IGNORECASE),
    re.compile(r"@touchstart\s*=", re.IGNORECASE),
    # jQuery
    re.compile(r"\.mousedown\s*\(", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']mousedown[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']pointerdown[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']touchstart[\"']", re.IGNORECASE),
]

# Patterns to detect pointer up/cancel event handlers (mouseup, pointerup, pointercancel, touchend, touchcancel)
POINTER_UP_CANCEL_PATTERNS = [
    # HTML event attributes
    re.compile(r"\bonmouseup\s*=", re.IGNORECASE),
    re.compile(r"\bonpointerup\s*=", re.IGNORECASE),
    re.compile(r"\bonpointercancel\s*=", re.IGNORECASE),
    re.compile(r"\bontouchend\s*=", re.IGNORECASE),
    re.compile(r"\bontouchcancel\s*=", re.IGNORECASE),
    # addEventListener patterns
    re.compile(r"addEventListener\s*\(\s*[\"']mouseup[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']pointerup[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']pointercancel[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']touchend[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']touchcancel[\"']", re.IGNORECASE),
    # React/Vue/Angular style handlers
    re.compile(r"onMouseUp\s*=", re.IGNORECASE),
    re.compile(r"onPointerUp\s*=", re.IGNORECASE),
    re.compile(r"onPointerCancel\s*=", re.IGNORECASE),
    re.compile(r"onTouchEnd\s*=", re.IGNORECASE),
    re.compile(r"onTouchCancel\s*=", re.IGNORECASE),
    re.compile(r"@mouseup\s*=", re.IGNORECASE),
    re.compile(r"@pointerup\s*=", re.IGNORECASE),
    re.compile(r"@pointercancel\s*=", re.IGNORECASE),
    re.compile(r"@touchend\s*=", re.IGNORECASE),
    re.compile(r"@touchcancel\s*=", re.IGNORECASE),
    # jQuery
    re.compile(r"\.mouseup\s*\(", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']mouseup[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']pointerup[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']pointercancel[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']touchend[\"']", re.IGNORECASE),
    re.compile(r"\.on\s*\(\s*[\"']touchcancel[\"']", re.IGNORECASE),
]

# Patterns for drag and drop functionality
DRAG_DROP_PATTERNS = [
    # HTML5 Drag and Drop API
    re.compile(r"draggable\s*=\s*[\"']true[\"']", re.IGNORECASE),
    re.compile(r"ondragstart\s*=", re.IGNORECASE),
    re.compile(r"ondrag\s*=", re.IGNORECASE),
    re.compile(r"ondragend\s*=", re.IGNORECASE),
    re.compile(r"ondragenter\s*=", re.IGNORECASE),
    re.compile(r"ondragover\s*=", re.IGNORECASE),
    re.compile(r"ondragleave\s*=", re.IGNORECASE),
    re.compile(r"ondrop\s*=", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']dragstart[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']drag[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']dragend[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']dragenter[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']dragover[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']dragleave[\"']", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*[\"']drop[\"']", re.IGNORECASE),
    # React/Vue/Angular
    re.compile(r"onDragStart\s*=", re.IGNORECASE),
    re.compile(r"onDrag\s*=", re.IGNORECASE),
    re.compile(r"onDragEnd\s*=", re.IGNORECASE),
    re.compile(r"onDragEnter\s*=", re.IGNORECASE),
    re.compile(r"onDragOver\s*=", re.IGNORECASE),
    re.compile(r"onDragLeave\s*=", re.IGNORECASE),
    re.compile(r"onDrop\s*=", re.IGNORECASE),
    # DataTransfer usage
    re.compile(r"dataTransfer", re.IGNORECASE),
    re.compile(r"setData\s*\(", re.IGNORECASE),
    re.compile(r"getData\s*\(", re.IGNORECASE),
]

# Patterns for cancel/abandon mechanisms
CANCEL_ABANDON_PATTERNS = [
    # Confirmation dialogs
    re.compile(r"confirm\s*\(", re.IGNORECASE),
    re.compile(r"window\.confirm\s*\(", re.IGNORECASE),
    re.compile(r"alert\s*\(", re.IGNORECASE),
    # Escape key handling
    re.compile(r"keydown.*[\"']Escape[\"']", re.IGNORECASE),
    re.compile(r"keydown.*[\"']Esc[\"']", re.IGNORECASE),
    re.compile(r"keyCode\s*===\s*27", re.IGNORECASE),
    re.compile(r"key\s*===\s*[\"']Escape[\"']", re.IGNORECASE),
    # Cancel/abort buttons
    re.compile(r"abort\s*\(", re.IGNORECASE),
    re.compile(r"cancel\s*\(", re.IGNORECASE),
    re.compile(r"\.abort\s*\(", re.IGNORECASE),
    re.compile(r"\.cancel\s*\(", re.IGNORECASE),
    # Reset/restore position
    re.compile(r"reset.*position", re.IGNORECASE),
    re.compile(r"restore.*position", re.IGNORECASE),
    re.compile(r"initial.*position", re.IGNORECASE),
    # Pointer capture release
    re.compile(r"releasePointerCapture\s*\(", re.IGNORECASE),
    re.compile(r"setPointerCapture\s*\(", re.IGNORECASE),
]

# Keywords for interfaces where down-event is essential (cas particuliers)
ESSENTIAL_DOWN_EVENT_KEYWORDS = [
    "keyboard emulator",
    "émulateur clavier",
    "virtual keyboard",
    "clavier virtuel",
    "piano",
    "drum",
    "batterie",
    "musical instrument",
    "instrument de musique",
    "game",
    "jeu",
    "gaming",
    "arcade",
    "emulator",
    "émulateur",
    "synthesizer",
    "synthétiseur",
    "midi",
    "keypad",
    "numpad",
    "touch screen keyboard",
    "clavier tactile",
    "on-screen keyboard",
    "clavier à l'écran",
    "accessibility keyboard",
    "clavier accessibilité",
    "braille",
    "chorded keyboard",
    "clavier accordé",
]


def _find_pointer_down_handlers(soup: BeautifulSoup) -> list[dict]:
    """Find elements with pointer down event handlers (mousedown, pointerdown, touchstart)."""
    results = []
    all_elements = soup.find_all(True)

    for i, element in enumerate(all_elements):
        matches = []

        # Check HTML event attributes for direct pointer down handlers
        for attr in ["onmousedown", "onpointerdown", "ontouchstart", "onMouseDown", "onPointerDown", "onTouchStart"]:
            val = element.get(attr)
            if isinstance(val, str) and val.strip():
                matches.append(
                    {
                        "type": "html_attribute",
                        "attribute": attr,
                        "handler": val[:200],
                    }
                )

        # Check for draggable elements (HTML5 Drag & Drop API)
        # These are activated via pointer devices (mousedown/touchstart + move)
        is_draggable = element.get("draggable", "").lower() == "true"
        has_drag_attrs = any(
            element.get(attr)
            for attr in ["ondragstart", "ondrag", "ondragend", "ondragenter", "ondragover", "ondragleave", "ondrop"]
            if isinstance(element.get(attr), str) and element.get(attr).strip()
        )

        if is_draggable or has_drag_attrs:
            # This element can be dragged via pointer - treat as pointer-down interaction
            if not matches:
                matches.append(
                    {
                        "type": "drag_drop",
                        "attribute": "draggable" if is_draggable else "drag_handler",
                        "handler": "HTML5 Drag & Drop API",
                    }
                )

        # Check inline JavaScript in script tags
        scripts = element.find_all("script")
        for script in scripts:
            if not script.string:
                continue
            content = script.string
            for pattern in POINTER_DOWN_PATTERNS:
                for match in pattern.finditer(content):
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 200)
                    matches.append(
                        {
                            "type": "script_pattern",
                            "pattern": pattern.pattern,
                            "match": match.group(),
                            "context": content[start:end],
                        }
                    )

        if matches:
            # Check if this element also has up/cancel handlers
            has_up_cancel = _element_has_up_cancel_handlers(element, soup)

            # Check if this element has drag/drop
            has_drag_drop = _element_has_drag_drop(element, soup)

            # Check for cancel/abandon mechanism
            has_cancel_abandon = _element_has_cancel_abandon(element, soup)

            results.append(
                {
                    "index": i,
                    "element": element,
                    "matches": matches,
                    "tag": element.name,
                    "id": element.get("id"),
                    "classes": element.get("class", []),
                    "has_up_cancel": has_up_cancel,
                    "has_drag_drop": has_drag_drop,
                    "has_cancel_abandon": has_cancel_abandon,
                }
            )

    return results


def _element_has_up_cancel_handlers(element, soup: BeautifulSoup) -> bool:
    """Check if an element or its scripts have pointer up/cancel handlers."""
    # Check HTML attributes on the element
    for attr in [
        "onmouseup",
        "onpointerup",
        "onpointercancel",
        "ontouchend",
        "ontouchcancel",
        "onMouseUp",
        "onPointerUp",
        "onPointerCancel",
        "onTouchEnd",
        "onTouchCancel",
    ]:
        val = element.get(attr)
        if isinstance(val, str) and val.strip():
            return True

    # Check scripts within or related to this element
    scripts = element.find_all("script")
    for script in scripts:
        if not script.string:
            continue
        content = script.string
        for pattern in POINTER_UP_CANCEL_PATTERNS:
            if pattern.search(content):
                return True

    # Also check parent element for event delegation
    parent = element.parent
    if parent:
        for attr in ["onmouseup", "onpointerup", "onpointercancel", "ontouchend", "ontouchcancel"]:
            val = parent.get(attr)
            if isinstance(val, str) and val.strip():
                return True

    return False


def _element_has_drag_drop(element, soup: BeautifulSoup) -> bool:
    """Check if an element has drag and drop functionality."""
    # Check HTML attributes
    if element.get("draggable", "").lower() == "true":
        return True

    for attr in ["ondragstart", "ondrag", "ondragend", "ondragenter", "ondragover", "ondragleave", "ondrop"]:
        val = element.get(attr)
        if isinstance(val, str) and val.strip():
            return True

    # Check scripts
    scripts = element.find_all("script")
    for script in scripts:
        if not script.string:
            continue
        content = script.string
        for pattern in DRAG_DROP_PATTERNS:
            if pattern.search(content):
                return True

    return False


def _element_has_cancel_abandon(element, soup: BeautifulSoup) -> bool:
    """Check if an element or page has cancel/abandon mechanisms."""
    # Check scripts in the element
    scripts = element.find_all("script")
    for script in scripts:
        if not script.string:
            continue
        content = script.string
        for pattern in CANCEL_ABANDON_PATTERNS:
            if pattern.search(content):
                return True

    # Check page-level scripts for cancel patterns (e.g., Escape key handlers)
    page_scripts = soup.find_all("script")
    for script in page_scripts:
        if not script.string:
            continue
        content = script.string
        for pattern in CANCEL_ABANDON_PATTERNS:
            if pattern.search(content):
                return True

    # Check for confirmation dialog buttons or cancel buttons in the page
    buttons = soup.find_all(["button", "input", "a"])
    for btn in buttons:
        btn_text = (btn.get_text() or "").lower()
        btn_id = (btn.get("id") or "").lower()
        btn_class = " ".join(btn.get("class", [])).lower()
        btn_aria = (btn.get("aria-label") or "").lower()

        combined = f"{btn_text} {btn_id} {btn_class} {btn_aria}"
        cancel_keywords = [
            "annuler",
            "cancel",
            "abandon",
            "abort",
            "retour",
            "back",
            "undo",
            "rétablir",
            "restaurer",
            "arrêter",
            "stop",
            "quitter",
            "exit",
            "close",
            "fermer",
            "dismiss",
            "rejeter",
            "refuser",
        ]
        if any(kw in combined for kw in cancel_keywords):
            return True

    return False


def _check_essential_down_event_context(soup: BeautifulSoup) -> tuple[bool, list[str]]:
    """
    Check if the page appears to be an interface where down-event activation is essential.
    Returns (is_essential, reasons).
    """
    reasons = []

    # Check page title
    title_tag = soup.find("title")
    title_text = ""
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()
        for keyword in ESSENTIAL_DOWN_EVENT_KEYWORDS:
            if keyword.lower() in title_text:
                reasons.append(f"Title indicates essential down-event interface: '{keyword}'")
                return True, reasons

    # Check for piano/keyboard/music related elements
    body_text = soup.get_text().lower()
    for keyword in ESSENTIAL_DOWN_EVENT_KEYWORDS:
        if keyword.lower() in body_text:
            reasons.append(f"Page content indicates essential down-event interface: '{keyword}'")
            return True, reasons

    # Check for elements with role="button" that behave like piano keys
    piano_like = soup.find_all(attrs={"role": "button"})
    piano_key_classes = ["piano-key", "key-white", "key-black", "drum-pad", "key-pad"]
    for elem in piano_like:
        classes = " ".join(elem.get("class", [])).lower()
        if any(cls in classes for cls in piano_key_classes):
            reasons.append("Piano/drum key-like elements detected")
            return True, reasons

    # Check for data attributes indicating keyboard/musical instrument
    elements_with_data = soup.find_all(attrs={"data-instrument": True})
    if elements_with_data:
        reasons.append("data-instrument attribute detected")
        return True, reasons

    elements_with_data = soup.find_all(attrs={"data-keyboard": True})
    if elements_with_data:
        reasons.append("data-keyboard attribute detected")
        return True, reasons

    return False, reasons


def _get_element_selector(soup: BeautifulSoup, element, index: int) -> str:
    """Generate a readable selector for an element."""
    if element is None:
        return f"element[index={index}]"

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


class Test13111(RGAATest):
    """
    Test 13.11.1 : Dans chaque page web, les actions déclenchées au moyen d'un dispositif
    de pointage sur un point unique de l'écran vérifient-elles l'une de ces conditions
    (hors cas particuliers) ?

    L'action est déclenchée au moment où le dispositif de pointage est relâché ou relevé ;
    L'action est déclenchée au moment où le dispositif de pointage est pressé ou posé puis
    annulée lorsque le dispositif de pointage est relâché ou relevé ;
    Un mécanisme est disponible pour abandonner (avant achèvement de l'action) ou annuler
    (après achèvement) l'exécution de l'action.

    Cas particuliers : Il existe une gestion de cas particulier lorsque la fonctionnalité
    nécessite que le comportement attendu soit réalisé lors d'un événement descendant,
    par exemple, un émulateur de clavier dont les touches doivent s'activer à la pression
    comme sur un clavier physique. Dans ces situations, le critère est non applicable.
    """

    test_id = "13.11.1"
    criterion_id = "13.11"

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
                summary="Le DOM n'est pas disponible ; le test 13.11.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential down-event interface (cas particulier)
        is_essential, essential_reasons = _check_essential_down_event_context(soup)

        # Find all pointer down handlers
        pointer_down_handlers = _find_pointer_down_handlers(soup)

        if not pointer_down_handlers:
            base_metadata = {
                "pointer_down_handlers_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "compliant_count": 0,
                "is_essential_down_event": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier l'absence de gestionnaires d'événement descendant non détectés "
                    "(code minifié, bibliothèques externes)",
                    "vérifier que les actions se déclenchent au relâchement (up event) par défaut",
                    "vérifier la présence de mécanismes d'abandon/annulation pour drag & drop",
                    "identifier les cas particuliers (émulateur clavier, piano, jeu, instrument de musique)",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : interface à événement descendant essentiel détectée. "
                    "Le critère 13.11.1 ne s'applique pas si l'activation à la pression est indispensable."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à événement descendant essentiel détectée (cas particulier). "
                        "Aucun gestionnaire d'événement descendant explicite trouvé. "
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
                        "Aucun gestionnaire d'événement descendant (mousedown, pointerdown, touchstart) détecté. "
                        "Les actions devraient être déclenchées au relâchement (up event)."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each pointer down handler
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0
        compliant_count = 0

        for i, handler in enumerate(pointer_down_handlers):
            selector = _get_element_selector(soup, handler["element"], i)
            tag = handler["tag"]
            element_id = handler["id"]
            classes = handler["classes"]

            has_up_cancel = handler["has_up_cancel"]
            has_drag_drop = handler["has_drag_drop"]
            has_cancel_abandon = handler["has_cancel_abandon"]

            # Determine compliance
            if is_essential:
                # Cas particulier : down-event essential - check if there's at least cancel mechanism
                if has_cancel_abandon or has_up_cancel:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Gestionnaire descendant détecté sur {tag}"
                                f"{f'#{element_id}' if element_id else ''}"
                                f"{f'.{".".join(classes[:2])}' if classes else ''}. "
                                "Interface à événement descendant essentiel (cas particulier) "
                                "MAIS mécanisme d'annulation/abandon détecté."
                            ),
                            recommendation=(
                                "Conforme au critère 13.11.1 (cas particulier avec mécanisme d'annulation). "
                                "Vérifier manuellement que l'annulation est accessible."
                            ),
                            evidence={
                                "tag": tag,
                                "id": element_id,
                                "classes": classes,
                                "is_essential_down_event": True,
                                "essential_reasons": essential_reasons,
                                "has_up_cancel": has_up_cancel,
                                "has_drag_drop": has_drag_drop,
                                "has_cancel_abandon": has_cancel_abandon,
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
                                f"Gestionnaire descendant détecté sur {tag}"
                                f"{f'#{element_id}' if element_id else ''}"
                                f"{f'.{".".join(classes[:2])}' if classes else ''}. "
                                "Interface à événement descendant essentiel (cas particulier) : "
                                "AUCUN MÉCANISME D'ANNULATION/ABANDON DÉTECTÉ."
                            ),
                            recommendation=(
                                "CRITIQUE : Le critère 13.11.1 exige un mécanisme d'abandon/annulation "
                                "même pour les cas particuliers si l'interface est le seul moyen d'accès. "
                                "Vérifier manuellement : "
                                "1) Si cette interface est le SEUL moyen d'accès au service ; "
                                "2) Si oui, implémenter un mécanisme d'annulation accessible "
                                "(touche Échap, bouton annuler, confirmation, etc.) ; "
                                "3) Si non (service accessible autrement), le critère est non applicable."
                            ),
                            evidence={
                                "tag": tag,
                                "id": element_id,
                                "classes": classes,
                                "is_essential_down_event": True,
                                "essential_reasons": essential_reasons,
                                "has_up_cancel": has_up_cancel,
                                "has_drag_drop": has_drag_drop,
                                "has_cancel_abandon": has_cancel_abandon,
                                "matches": handler["matches"],
                                "required_checks": [
                                    "vérifier si l'interface est le seul moyen d'accès au service",
                                    "si seul moyen : implémenter mécanisme d'annulation accessible "
                                    "(Échap, bouton, etc.)",
                                    "si autre moyen d'accès : critère non applicable",
                                ],
                            },
                        )
                    )
            else:
                # Pas un cas particulier : l'action doit se déclencher au up OU avoir un mécanisme d'annulation
                # Pour drag & drop : vérification spécifique
                if has_drag_drop:
                    if has_cancel_abandon:
                        compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Drag & drop détecté sur {tag}"
                                    f"{f'#{element_id}' if element_id else ''}"
                                    f"{f'.{".".join(classes[:2])}' if classes else ''} "
                                    "avec mécanisme d'abandon/annulation."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.11.1 : mécanisme d'abandon/annulation "
                                    "détecté pour drag & drop. "
                                    "Vérifier manuellement : relâchement hors zone = abandon, "
                                    "confirmation dépôt = annulation possible."
                                ),
                                evidence={
                                    "tag": tag,
                                    "id": element_id,
                                    "classes": classes,
                                    "interaction_type": "drag_drop",
                                    "has_up_cancel": has_up_cancel,
                                    "has_cancel_abandon": has_cancel_abandon,
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
                                    f"Drag & drop détecté sur {tag}"
                                    f"{f'#{element_id}' if element_id else ''}"
                                    f"{f'.{".".join(classes[:2])}' if classes else ''} "
                                    "SANS mécanisme d'abandon/annulation détecté."
                                ),
                                recommendation=(
                                    "Non conforme au critère 13.11.1 : implémenter un mécanisme "
                                    "d'abandon/annulation pour le drag & drop. "
                                    "Exemples : relâchement hors zone cible = abandon, "
                                    "dialogue de confirmation avant dépôt, "
                                    "touche Échap pour annuler, bouton annuler/rétablir."
                                ),
                                evidence={
                                    "tag": tag,
                                    "id": element_id,
                                    "classes": classes,
                                    "interaction_type": "drag_drop",
                                    "has_up_cancel": has_up_cancel,
                                    "has_cancel_abandon": has_cancel_abandon,
                                    "matches": handler["matches"],
                                },
                            )
                        )
                else:
                    # Action simple (clic, appui) : doit avoir up event OU mécanisme d'annulation
                    if has_up_cancel:
                        compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Gestionnaire descendant détecté sur {tag}"
                                    f"{f'#{element_id}' if element_id else ''}"
                                    f"{f'.{".".join(classes[:2])}' if classes else ''} "
                                    "AVEC gestionnaire de relâchement/annulation (up/cancel event)."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.11.1 : l'action est annulée ou déclenchée au relâchement. "
                                    "Vérifier manuellement que l'action ne s'exécute pas à la pression seule."
                                ),
                                evidence={
                                    "tag": tag,
                                    "id": element_id,
                                    "classes": classes,
                                    "interaction_type": "simple_action",
                                    "has_up_cancel": has_up_cancel,
                                    "has_cancel_abandon": has_cancel_abandon,
                                    "matches": handler["matches"],
                                },
                            )
                        )
                    elif has_cancel_abandon:
                        compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Gestionnaire descendant détecté sur {tag}"
                                    f"{f'#{element_id}' if element_id else ''}"
                                    f"{f'.{".".join(classes[:2])}' if classes else ''} "
                                    "AVEC mécanisme d'abandon/annulation détecté."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.11.1 : mécanisme d'abandon/annulation disponible. "
                                    "Vérifier manuellement l'accessibilité du mécanisme."
                                ),
                                evidence={
                                    "tag": tag,
                                    "id": element_id,
                                    "classes": classes,
                                    "interaction_type": "simple_action",
                                    "has_up_cancel": has_up_cancel,
                                    "has_cancel_abandon": has_cancel_abandon,
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
                                    f"Gestionnaire descendant détecté sur {tag}"
                                    f"{f'#{element_id}' if element_id else ''}"
                                    f"{f'.{".".join(classes[:2])}' if classes else ''} "
                                    "SANS gestionnaire de relâchement (up/cancel) NI mécanisme d'abandon/annulation. "
                                    "L'action risque de se déclencher à la pression seule."
                                ),
                                recommendation=(
                                    "Non conforme au critère 13.11.1 : l'action doit être déclenchée au relâchement "
                                    "(mouseup, pointerup, touchend) OU avoir un mécanisme d'annulation/abandon. "
                                    "Corriger en déplaçant la logique vers l'event up ou en ajoutant "
                                    "un mécanisme d'annulation (confirmation, touche Échap, bouton annuler)."
                                ),
                                evidence={
                                    "tag": tag,
                                    "id": element_id,
                                    "classes": classes,
                                    "interaction_type": "simple_action",
                                    "has_up_cancel": has_up_cancel,
                                    "has_cancel_abandon": has_cancel_abandon,
                                    "matches": handler["matches"],
                                },
                            )
                        )

        tested_elements = len(pointer_down_handlers)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'événement descendant détecté(s). "
                f"{non_compliant_count} non conforme(s) (pas de up/cancel ni mécanisme d'annulation), "
                f"{needs_review_count} à vérifier (cas particulier sans mécanisme), "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'événement descendant détecté(s). "
                f"{needs_review_count} cas particulier(s) sans mécanisme d'annulation détecté, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} gestionnaire(s) d'événement descendant détecté(s). "
                f"Tous sont conformes au critère 13.11.1 (up/cancel event ou mécanisme d'annulation)."
            )

        metadata = {
            "pointer_down_handlers_count": len(pointer_down_handlers),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "compliant_count": compliant_count,
            "is_essential_down_event": is_essential,
            "essential_reasons": essential_reasons,
            "drag_drop_count": sum(1 for h in pointer_down_handlers if h["has_drag_drop"]),
            "required_manual_checks": [
                "vérifier l'absence de gestionnaires descendants non détectés (code minifié, bibliothèques externes)",
                "vérifier que les actions simples se déclenchent au relâchement (up event) et non à la pression",
                "vérifier la présence de mécanismes d'abandon/annulation pour drag & drop "
                "(relâchement hors zone, confirmation, Échap)",
                "identifier les cas particuliers (émulateur clavier, piano, jeu, instrument de musique, synthétiseur)",
                "si cas particulier : vérifier qu'un mécanisme d'annulation est proposé si c'est le seul accès",
                "vérifier l'accessibilité clavier des mécanismes d'annulation (touche Échap)",
                "vérifier que les dialogues de confirmation sont accessibles",
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

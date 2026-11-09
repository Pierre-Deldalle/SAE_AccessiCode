from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Pattern to detect window.open() calls
WINDOW_OPEN_PATTERN = re.compile(
    r"window\.open\s*\(\s*[^)]*\)",
    re.IGNORECASE,
)

# Inline event handler attributes that indicate user-triggered actions
INLINE_EVENT_HANDLERS = [
    "onclick",
    "onmousedown",
    "onmouseup",
    "onkeydown",
    "onkeyup",
    "onkeypress",
    "onsubmit",
    "onchange",
    "oninput",
    "onblur",
    "onfocus",  # Note: focus can be problematic per WCAG 3.2.1
]

# Patterns that suggest the window.open is inside an event handler (user-triggered)
# in script content
JS_EVENT_HANDLER_PATTERNS = [
    re.compile(r"addEventListener\s*\(\s*['\"]click['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]mousedown['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]mouseup['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]keydown['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]keyup['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]keypress['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]submit['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]change['\"]", re.IGNORECASE),
    re.compile(r"addEventListener\s*\(\s*['\"]input['\"]", re.IGNORECASE),
    # Inline handler assignments in JS
    re.compile(r"\.onclick\s*=", re.IGNORECASE),
    re.compile(r"\.onmousedown\s*=", re.IGNORECASE),
    re.compile(r"\.onmouseup\s*=", re.IGNORECASE),
    re.compile(r"\.onkeydown\s*=", re.IGNORECASE),
    re.compile(r"\.onkeyup\s*=", re.IGNORECASE),
    re.compile(r"\.onkeypress\s*=", re.IGNORECASE),
    re.compile(r"\.onsubmit\s*=", re.IGNORECASE),
    re.compile(r"\.onchange\s*=", re.IGNORECASE),
]

# Patterns that suggest automatic execution on page load
AUTO_EXECUTION_PATTERNS = [
    re.compile(r"window\.addEventListener\s*\(\s*['\"]load['\"]", re.IGNORECASE),
    re.compile(r"window\.addEventListener\s*\(\s*['\"]DOMContentLoaded['\"]", re.IGNORECASE),
    re.compile(r"document\.addEventListener\s*\(\s*['\"]DOMContentLoaded['\"]", re.IGNORECASE),
    re.compile(r"\.onload\s*=", re.IGNORECASE),
    re.compile(r"window\.onload\s*=", re.IGNORECASE),
    re.compile(r"document\.onload\s*=", re.IGNORECASE),
    re.compile(r"\(\s*function\s*\(\s*\)\s*\{", re.IGNORECASE),  # IIFE pattern
    re.compile(r"\(\s*\(\s*\)\s*=>\s*\{", re.IGNORECASE),  # Arrow function IIFE
]


def _is_in_js_event_handler(script_content: str, match_start: int) -> bool:
    """
    Check if a window.open call at position match_start is inside a JS event handler.
    This is a heuristic - looks for event handler patterns before the match.
    """
    # Look at the preceding code (up to 500 chars) for event handler patterns
    preceding = script_content[max(0, match_start - 500) : match_start]

    for pattern in JS_EVENT_HANDLER_PATTERNS:
        if pattern.search(preceding):
            return True

    return False


def _is_in_auto_execution(script_content: str, match_start: int) -> bool:
    """
    Check if a window.open call at position match_start is in an auto-execution context
    (onload, DOMContentLoaded, IIFE, etc.).
    """
    preceding = script_content[max(0, match_start - 500) : match_start]

    for pattern in AUTO_EXECUTION_PATTERNS:
        if pattern.search(preceding):
            return True

    return False


def _find_inline_event_handler_window_opens(soup: BeautifulSoup) -> list[dict]:
    """
    Find window.open() calls in inline event handler attributes (onclick, etc.)
    on HTML elements.
    """
    results = []

    for handler_attr in INLINE_EVENT_HANDLERS:
        elements = soup.find_all(attrs={handler_attr: True})
        for elem in elements:
            handler_value = elem.get(handler_attr, "")
            if isinstance(handler_value, str) and WINDOW_OPEN_PATTERN.search(handler_value):
                # Find all matches in this handler
                for match in WINDOW_OPEN_PATTERN.finditer(handler_value):
                    match_text = match.group(0)
                    results.append(
                        {
                            "element": elem,
                            "handler_attribute": handler_attr,
                            "handler_value": handler_value,
                            "match": match_text,
                            "context": "inline_event_handler",
                        }
                    )

    return results


def _find_script_window_opens(soup: BeautifulSoup) -> list[dict]:
    """
    Find window.open() calls in script tags and classify their context.
    """
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string

        for match in WINDOW_OPEN_PATTERN.finditer(content):
            match_start = match.start()
            match_text = match.group(0)

            # Check if it's in a JS event handler (user-triggered)
            if _is_in_js_event_handler(content, match_start):
                context = "js_event_handler"
            # Check if it's in auto-execution context
            elif _is_in_auto_execution(content, match_start):
                context = "auto"
            else:
                # Could be at top level or in a function - uncertain
                context = "unknown"

            # Get a preview around the match
            preview_start = max(0, match_start - 100)
            preview_end = min(len(content), match_start + 200)
            preview = content[preview_start:preview_end]

            results.append(
                {
                    "index": i,
                    "element": script,
                    "match": match_text,
                    "context": context,
                    "content_preview": preview,
                    "match_position": match_start,
                }
            )

    return results


def _find_all_window_opens(soup: BeautifulSoup) -> list[dict]:
    """
    Find all window.open() calls in both scripts and inline event handlers.
    Returns a unified list with context classification.
    """
    results = []

    # Find window.open in script tags
    script_opens = _find_script_window_opens(soup)
    results.extend(script_opens)

    # Find window.open in inline event handlers
    inline_opens = _find_inline_event_handler_window_opens(soup)
    results.extend(inline_opens)

    return results


def _get_script_element_selector(soup: BeautifulSoup, element, index: int) -> str:
    """Generate a readable selector for a script element."""
    if element is None:
        return f"script[index={index}]"

    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"

    scripts = soup.find_all("script")
    if len(scripts) > 1:
        try:
            return f"script[index={scripts.index(element)}]"
        except ValueError:
            pass

    return f"script[index={index}]"


def _get_inline_element_selector(element) -> str:
    """Generate a readable selector for an element with inline event handler."""
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"

    tag_name = element.name
    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{tag_name}.{'.'.join(str(c) for c in classes[:2])}"

    # Fallback to tag with index among same tag
    return f"{tag_name}"


class Test1321(RGAATest):
    """
    Test 13.2.1 : Dans chaque page web, l'ouverture d'une nouvelle fenêtre
    ne doit pas être déclenchée sans action de l'utilisateur.

    Vérifie qu'aucun window.open() n'est appelé automatiquement au chargement
    de la page (sans interaction utilisateur).
    """

    test_id = "13.2.1"
    criterion_id = "13.2"

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
                summary="Le DOM n'est pas disponible ; le test 13.2.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        all_window_opens = _find_all_window_opens(soup)

        if not all_window_opens:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun appel à window.open() détecté dans les scripts ni gestionnaires d'événements de la page."
                ),
                tested_elements=0,
                metadata={},
            )

        # Classify by context
        auto_opens = [w for w in all_window_opens if w["context"] == "auto"]
        js_event_opens = [w for w in all_window_opens if w["context"] == "js_event_handler"]
        inline_event_opens = [w for w in all_window_opens if w["context"] == "inline_event_handler"]
        unknown_opens = [w for w in all_window_opens if w["context"] == "unknown"]

        # Suspicious = auto + unknown (potential violations)
        suspicious_opens = auto_opens + unknown_opens

        # Likely compliant = event handlers (both JS and inline)
        event_handler_opens = js_event_opens + inline_event_opens

        if not suspicious_opens and not event_handler_opens:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun appel à window.open() détecté dans les scripts de la page.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0
        compliant_count = 0

        # Check suspicious (auto/unknown) window opens
        for i, open_call in enumerate(suspicious_opens):
            if open_call["context"] == "auto":
                element = open_call["element"]
                selector = _get_script_element_selector(soup, element, open_call.get("index", i))
            else:  # unknown
                element = open_call["element"]
                selector = _get_script_element_selector(soup, element, open_call.get("index", i))

            context = open_call["context"]
            preview = open_call["content_preview"]
            match_text = open_call["match"]

            if context == "auto":
                non_compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"window.open() détecté dans un contexte d'exécution automatique "
                            f"(onload, DOMContentLoaded, IIFE) : {match_text}"
                        ),
                        recommendation=(
                            "Le critère 13.2 exige que l'ouverture d'une nouvelle fenêtre "
                            "ne soit déclenchée qu'après une action explicite de l'utilisateur "
                            "(clic, soumission, etc.). Supprimer l'ouverture automatique ou "
                            "la lier à une action utilisateur."
                        ),
                        evidence={
                            "match": match_text,
                            "context": context,
                            "content_preview": preview,
                            "violation": "auto_window_open",
                        },
                    )
                )
            else:  # context == "unknown"
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"window.open() détecté dans un contexte indéterminé : {match_text}. "
                            "Impossible de déterminer automatiquement s'il est déclenché par "
                            "l'utilisateur ou automatiquement."
                        ),
                        recommendation=(
                            "Vérifier manuellement : "
                            "1) Si ce window.open() est appelé suite à une action utilisateur "
                            "(clic sur lien/bouton, soumission formulaire) -> conforme ; "
                            "2) Si il est appelé automatiquement au chargement -> non conforme ; "
                            "3) Si c'est une fonction appelée ultérieurement par événement -> "
                            "vérifier le déclencheur."
                        ),
                        evidence={
                            "match": match_text,
                            "context": context,
                            "content_preview": preview,
                            "needs_manual_check": True,
                        },
                    )
                )

        # Check event handler window opens (likely compliant but document)
        for i, open_call in enumerate(event_handler_opens):
            if open_call["context"] == "inline_event_handler":
                selector = _get_inline_element_selector(open_call["element"])
                handler_attr = open_call["handler_attribute"]
                match_text = open_call["match"]
                preview = open_call["handler_value"][:200]

                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"window.open() détecté dans un gestionnaire d'événement inline "
                            f"({handler_attr}) : {match_text}. Probablement conforme."
                        ),
                        recommendation=(
                            "Conforme au critère 13.2 si l'événement est une action utilisateur "
                            "explicite. Vérifier manuellement que l'élément déclencheur est accessible "
                            "et que l'ouverture est prévisible pour l'utilisateur. "
                            "Attention : onfocus peut déclencher sans action explicite (WCAG 3.2.1)."
                        ),
                        evidence={
                            "match": match_text,
                            "context": "inline_event_handler",
                            "handler_attribute": handler_attr,
                            "content_preview": preview,
                            "likely_compliant": True,
                        },
                    )
                )
            else:  # js_event_handler
                selector = _get_script_element_selector(soup, open_call["element"], open_call.get("index", i))
                preview = open_call["content_preview"]
                match_text = open_call["match"]

                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"window.open() détecté dans un gestionnaire d'événement JS "
                            f"(addEventListener, onclick=...) : {match_text}. Probablement conforme."
                        ),
                        recommendation=(
                            "Conforme au critère 13.2 si l'événement est une action utilisateur "
                            "explicite. Vérifier manuellement que l'élément déclencheur est accessible "
                            "et que l'ouverture est prévisible pour l'utilisateur."
                        ),
                        evidence={
                            "match": match_text,
                            "context": "js_event_handler",
                            "content_preview": preview,
                            "likely_compliant": True,
                        },
                    )
                )

        tested_elements = len(all_window_opens)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} appel(s) window.open() détecté(s). "
                f"{non_compliant_count} ouverture(s) automatique(s) non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} probable(s) conforme(s) (événement utilisateur)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} appel(s) window.open() détecté(s). "
                f"{needs_review_count} contexte(s) indéterminé(s) à vérifier manuellement, "
                f"{compliant_count} probable(s) conforme(s) (événement utilisateur)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} appel(s) window.open() détecté(s). "
                f"Tous sont dans des gestionnaires d'événements utilisateur (conformes)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "total_window_opens": len(all_window_opens),
                "auto_context_count": len(auto_opens),
                "unknown_context_count": len(unknown_opens),
                "js_event_handler_count": len(js_event_opens),
                "inline_event_handler_count": len(inline_event_opens),
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "compliant_count": compliant_count,
                "required_manual_checks": [
                    "vérifier que les window.open() de contexte 'unknown' sont déclenchés par action utilisateur",
                    "vérifier l'accessibilité des éléments déclencheurs (boutons, liens)",
                    "vérifier que l'ouverture de fenêtre est prévisible pour l'utilisateur",
                    "vérifier l'absence de pop-ups au chargement de la page",
                    "vérifier la conformité WCAG 3.2.1 (On Focus) - attention aux gestionnaires onfocus",
                ],
            },
        )

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns to detect orientation locking mechanisms (strict locks)
SCREEN_ORIENTATION_LOCK_PATTERNS = [
    # Screen Orientation API
    re.compile(r"screen\.orientation\.lock\s*\(", re.IGNORECASE),
    re.compile(r"screen\.lockOrientation\s*\(", re.IGNORECASE),
    re.compile(r"screen\.mozLockOrientation\s*\(", re.IGNORECASE),
    re.compile(r"screen\.msLockOrientation\s*\(", re.IGNORECASE),
]

# Patterns for orientation change event listeners (may be legitimate for adaptation)
SCREEN_ORIENTATION_EVENT_PATTERNS = [
    re.compile(r"orientationchange", re.IGNORECASE),
    re.compile(r"onorientationchange", re.IGNORECASE),
]

# CSS patterns for orientation-specific content hiding
CSS_ORIENTATION_MEDIA_QUERY_PATTERN = re.compile(
    r"@media\s*\([^)]*orientation\s*:\s*(portrait|landscape)\s*\)",
    re.IGNORECASE | re.DOTALL,
)

# Viewport meta tag patterns that might restrict orientation
VIEWPORT_ORIENTATION_PATTERN = re.compile(
    r"orientation\s*=\s*(portrait|landscape)",
    re.IGNORECASE,
)

# CSS classes/IDs that suggest orientation-specific content
# Patterns match class names (without dot prefix) and IDs (without # prefix)
ORIENTATION_SPECIFIC_SELECTORS = [
    re.compile(r"portrait[-_]only", re.IGNORECASE),
    re.compile(r"landscape[-_]only", re.IGNORECASE),
    re.compile(r"portrait[-_]only", re.IGNORECASE),  # For ID matching
    re.compile(r"landscape[-_]only", re.IGNORECASE),  # For ID matching
    re.compile(r"\[orientation\s*=\s*[\"']?(portrait|landscape)[\"']?\]", re.IGNORECASE),
]

# Keywords for interfaces where orientation is essential (cas particuliers)
ESSENTIAL_ORIENTATION_KEYWORDS = [
    "game",
    "jeu",
    "piano",
    "clavier",
    "check",
    "chèque",
    "check-deposit",
    "deposit",
    "bank",
    "banque",
    "vr",
    "virtual-reality",
    "ar",
    "augmented-reality",
    "compass",
    "boussole",
    "level",
    "niveau",
    "instrument",
    "drawing",
    "dessin",
    "sketch",
    "signature",
]


def _find_orientation_lock_js(soup: BeautifulSoup) -> list[dict]:
    """Find JavaScript that locks or restricts screen orientation (strict locks)."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        for pattern in SCREEN_ORIENTATION_LOCK_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "matches": matches,
                    "content_preview": content[:300],
                    "lock_type": "strict",
                }
            )

    return results


def _find_orientation_event_listeners(soup: BeautifulSoup) -> list[dict]:
    """Find JavaScript orientation change event listeners (may be legitimate)."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        for pattern in SCREEN_ORIENTATION_EVENT_PATTERNS:
            for match in pattern.finditer(content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "matches": matches,
                    "content_preview": content[:300],
                    "lock_type": "event_listener",
                }
            )

    return results


def _find_css_orientation_media_queries(soup: BeautifulSoup) -> list[dict]:
    """Find CSS @media queries that target specific orientations."""
    results = []

    # Check inline styles
    style_tags = soup.find_all("style")
    for i, style_tag in enumerate(style_tags):
        if not style_tag.string:
            continue

        css_text = style_tag.string
        for match in CSS_ORIENTATION_MEDIA_QUERY_PATTERN.finditer(css_text):
            orientation = match.group(1).lower()
            start = max(0, match.start() - 200)
            end = min(len(css_text), match.end() + 500)
            results.append(
                {
                    "type": "style_tag",
                    "index": i,
                    "element": style_tag,
                    "orientation": orientation,
                    "context": css_text[start:end],
                    "full_query": match.group(0)[:200],
                }
            )

    # Check link stylesheets (inline only, external not accessible)
    # Could be extended to fetch external CSS if needed

    return results


def _find_viewport_orientation_restriction(soup: BeautifulSoup) -> list[dict]:
    """Find viewport meta tags that restrict orientation."""
    results = []
    meta_tags = soup.find_all("meta", attrs={"name": re.compile(r"viewport", re.IGNORECASE)})

    for i, meta in enumerate(meta_tags):
        content = meta.get("content", "")
        if isinstance(content, str) and VIEWPORT_ORIENTATION_PATTERN.search(content):
            match = VIEWPORT_ORIENTATION_PATTERN.search(content)
            results.append(
                {
                    "index": i,
                    "element": meta,
                    "orientation": match.group(1).lower(),
                    "content": content,
                }
            )

    return results


def _find_orientation_specific_content(soup: BeautifulSoup) -> list[dict]:
    """Find HTML elements with orientation-specific classes/attributes."""
    results = []
    seen_elements = set()  # Avoid duplicates

    for pattern in ORIENTATION_SPECIFIC_SELECTORS:
        elements = []

        # Check all elements for class matches
        all_elements = soup.find_all(class_=True)
        for elem in all_elements:
            classes = elem.get("class", [])
            if isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes)
            else:
                class_str = str(classes)
            if pattern.search(class_str):
                elements.append(elem)

        # Check all elements for ID matches
        all_elements = soup.find_all(id=True)
        for elem in all_elements:
            if pattern.search(elem.get("id", "")):
                elements.append(elem)

        # Check for attribute patterns (e.g., orientation="portrait")
        all_elements = soup.find_all(True)
        for elem in all_elements:
            for attr_name, attr_value in elem.attrs.items():
                if isinstance(attr_value, str) and pattern.search(attr_value):
                    elements.append(elem)
                    break

        for elem in elements:
            # Avoid duplicates
            elem_id = id(elem)
            if elem_id in seen_elements:
                continue
            seen_elements.add(elem_id)

            results.append(
                {
                    "element": elem,
                    "selector_pattern": pattern.pattern,
                    "tag": elem.name,
                    "classes": elem.get("class", []),
                    "id": elem.get("id", ""),
                    "attributes": dict(elem.attrs),
                }
            )

    return results


def _check_essential_orientation_context(soup: BeautifulSoup) -> tuple[bool, list[str]]:
    """
    Check if the page appears to be an interface where orientation is essential.
    Returns (is_essential, reasons).
    """
    reasons = []

    # Check page title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()
        for kw in ESSENTIAL_ORIENTATION_KEYWORDS:
            if kw in title_text:
                reasons.append(f"Title contains '{kw}'")
                return True, reasons

    # Check for canvas/WebGL (often games)
    canvas = soup.find("canvas")
    if canvas:
        # Check if it has game-like attributes or large size
        width = canvas.get("width")
        height = canvas.get("height")
        if width and height:
            try:
                w = int(str(width).replace("px", ""))
                h = int(str(height).replace("px", ""))
                if w > 300 and h > 300:
                    reasons.append("Large canvas element (possible game/VR)")
                    return True, reasons
            except (ValueError, TypeError):  # fmt: skip
                pass

    # Check for VR/AR related elements
    vr_elements = soup.find_all(attrs={"xr-session": True})
    if vr_elements:
        reasons.append("WebXR session detected")
        return True, reasons

    # Check for specific meta tags or attributes
    # Check all text content for keywords (heuristic)
    body_text = soup.get_text().lower()
    essential_indicators = [
        "jeu vidéo",
        "video game",
        "réalité virtuelle",
        "virtual reality",
        "dépôt chèque",
        "check deposit",
    ]
    for indicator in essential_indicators:
        if indicator in body_text:
            reasons.append(f"Page content mentions '{indicator}'")
            return True, reasons

    return False, reasons


def _has_alternative_access(soup: BeautifulSoup) -> bool:
    """
    Check if there's an alternative way to access the content/service
    when orientation is locked (for essential orientation interfaces).
    """
    # Look for links/buttons to alternative version
    alt_keywords = [
        "version accessible",
        "accessible version",
        "sans orientation",
        "without orientation",
        "alternative",
        "accessible",
        "version statique",
        "static version",
        "mode portrait",
        "mode paysage",
        "portrait mode",
        "landscape mode",
    ]

    controls = soup.find_all(["a", "button", "input"], string=re.compile("|".join(alt_keywords), re.IGNORECASE))

    # Also check aria-label, title attributes
    for elem in soup.find_all(["a", "button", "input", "link"]):
        for attr in ["aria-label", "title", "alt"]:
            value = elem.get(attr, "")
            if isinstance(value, str) and any(kw in value.lower() for kw in alt_keywords):
                return True

    return len(controls) > 0


class Test1391(RGAATest):
    """
    Test 13.9.1 : Dans chaque page web, chaque contenu vérifie-t-il ces conditions (hors cas particuliers) ?

    La consultation est possible quel que soit le mode d'orientation de l'écran ;
    Le contenu proposé reste le même quel que soit le mode d'orientation de l'écran utilisé
    même si sa présentation et le moyen d'y accéder peut différer.

    Cas particuliers : interfaces pour lesquelles l'orientation du périphérique est essentielle
    (jeux, piano, dépôt de chèques bancaires, etc.). Dans ces cas, le critère est non applicable,
    mais une alternative devrait être mise en place si c'est le seul moyen d'accéder au service.
    """

    test_id = "13.9.1"
    criterion_id = "13.9"

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
                summary="Le DOM n'est pas disponible ; le test 13.9.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Check if this is an essential orientation interface (cas particulier)
        is_essential, essential_reasons = _check_essential_orientation_context(soup)

        # Find all orientation restriction mechanisms
        js_locks = _find_orientation_lock_js(soup)
        js_event_listeners = _find_orientation_event_listeners(soup)
        css_media_queries = _find_css_orientation_media_queries(soup)
        viewport_restrictions = _find_viewport_orientation_restriction(soup)
        orientation_specific_content = _find_orientation_specific_content(soup)

        all_issues = []

        # Collect JavaScript strict orientation locks
        for js_lock in js_locks:
            all_issues.append(
                {
                    "type": "js_orientation_lock",
                    "element": js_lock["element"],
                    "matches": js_lock["matches"],
                    "description": "JavaScript verrouillant l'orientation de l'écran détecté (screen.orientation.lock)",
                    "severity": "high",
                }
            )

        # Collect JavaScript orientation event listeners (may be legitimate)
        for js_event in js_event_listeners:
            all_issues.append(
                {
                    "type": "js_orientation_event_listener",
                    "element": js_event["element"],
                    "matches": js_event["matches"],
                    "description": (
                        "Écouteur d'événement orientationchange détecté (peut être légitime pour adaptation)"
                    ),
                    "severity": "low",
                }
            )

        # Collect CSS media queries that hide/show content based on orientation
        for mq in css_media_queries:
            all_issues.append(
                {
                    "type": "css_orientation_media_query",
                    "element": mq["element"],
                    "orientation": mq["orientation"],
                    "context": mq["context"],
                    "description": f"Requête média CSS ciblant l'orientation '{mq['orientation']}' détectée",
                    "severity": "medium",
                }
            )

        # Collect viewport orientation restrictions
        for vp in viewport_restrictions:
            all_issues.append(
                {
                    "type": "viewport_orientation_restriction",
                    "element": vp["element"],
                    "orientation": vp["orientation"],
                    "content": vp["content"],
                    "description": f"Balise viewport restreignant l'orientation à '{vp['orientation']}'",
                    "severity": "high",
                }
            )

        # Collect orientation-specific content
        for osc in orientation_specific_content:
            all_issues.append(
                {
                    "type": "orientation_specific_content",
                    "element": osc["element"],
                    "tag": osc["tag"],
                    "classes": osc["classes"],
                    "id": osc["id"],
                    "description": (
                        "Contenu spécifique à une orientation détecté (classe/ID suggérant portrait/landscape only)"
                    ),
                    "severity": "medium",
                }
            )

        if not all_issues:
            base_metadata = {
                "total_issues": 0,
                "js_locks_count": 0,
                "js_event_listeners_count": 0,
                "css_media_queries_count": 0,
                "viewport_restrictions_count": 0,
                "orientation_specific_content_count": 0,
                "non_compliant_count": 0,
                "needs_review_count": 0,
                "is_essential_orientation": is_essential,
                "essential_reasons": essential_reasons,
                "required_manual_checks": [
                    "vérifier que la consultation est possible en mode portrait ET paysage",
                    "vérifier que le contenu proposé est identique dans les deux orientations",
                    "vérifier que seule la présentation/moyen d'accès peut différer",
                    "identifier les cas particuliers (jeux, piano, dépôt chèque, VR/AR, boussole, niveau, signature)",
                    (
                        "si cas particulier : vérifier qu'une alternative accessible "
                        "est proposée si c'est le seul accès au service"
                    ),
                    "vérifier l'absence de screen.orientation.lock() ou verrouillage viewport",
                    "vérifier que les @media (orientation:) ne masquent pas de contenu",
                ],
            }

            if is_essential:
                base_metadata["note"] = (
                    "Cas particulier : vérifier manuellement qu'une alternative "
                    "est proposée si c'est le seul moyen d'accès au service."
                )
                return TestResult(
                    test_id=self.test_id,
                    criterion_id=self.criterion_id,
                    status=TestStatus.NOT_APPLICABLE,
                    summary=(
                        "Interface à orientation essentielle détectée (cas particulier). "
                        "Aucun mécanisme de verrouillage d'orientation explicite trouvé. "
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
                        "Aucun mécanisme de restriction d'orientation détecté. "
                        "Le contenu devrait être consultable en portrait et paysage."
                    ),
                    tested_elements=0,
                    metadata=base_metadata,
                )

        # Analyze each issue
        findings: list[Finding] = []
        non_compliant_count = 0
        needs_review_count = 0

        for i, issue in enumerate(all_issues):
            selector = self._get_issue_selector(soup, issue, i)
            issue_type = issue["type"]

            if is_essential:
                # Cas particulier : vérifier s'il y a une alternative
                has_alternative = _has_alternative_access(soup)

                if has_alternative:
                    # Alternative disponible -> conforme (mais signaler le verrouillage)
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. "
                                "Interface à orientation essentielle (cas particulier) MAIS alternative détectée."
                            ),
                            recommendation=(
                                "Conforme au critère 13.9.1 (cas particulier avec alternative). "
                                "Vérifier manuellement que l'alternative permet un accès équivalent au service."
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": True,
                                "essential_reasons": essential_reasons,
                                "has_alternative": True,
                                "details": {k: v for k, v in issue.items() if k != "element"},
                            },
                        )
                    )
                else:
                    # Pas d'alternative -> NEEDS_REVIEW (cas particulier sans alternative détectée)
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. "
                                "Interface à orientation essentielle (cas particulier) : "
                                "AUCUNE ALTERNATIVE DÉTECTÉE pour les utilisateurs "
                                "ne pouvant pas utiliser cette orientation."
                            ),
                            recommendation=(
                                "CRITIQUE : Le critère 13.9.1 exige une alternative "
                                "si l'interface est le seul moyen d'accéder au service. "
                                "Vérifier manuellement : "
                                "1) Si cette interface est le SEUL moyen d'accès au service ; "
                                "2) Si oui, implémenter une alternative accessible "
                                "(version sans restriction d'orientation) ; "
                                "3) Si non (service accessible autrement), "
                                "le critère est non applicable."
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": True,
                                "essential_reasons": essential_reasons,
                                "has_alternative": False,
                                "details": {k: v for k, v in issue.items() if k != "element"},
                                "required_checks": [
                                    "vérifier si l'interface est le seul moyen d'accès au service",
                                    "si seul moyen : implémenter alternative accessible",
                                    "si autre moyen d'accès : critère non applicable",
                                ],
                            },
                        )
                    )
            else:
                # Pas un cas particulier -> toute restriction est non conforme
                if issue_type in ["js_orientation_lock", "viewport_orientation_restriction"]:
                    # Verrouillage strict = FAIL
                    non_compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. Ce verrouillage empêche la consultation dans une orientation."
                            ),
                            recommendation=(
                                f"Non conforme au critère 13.9.1 : supprimer le verrouillage "
                                f"d'orientation ({issue_type}). "
                                "Le contenu doit être consultable en portrait ET en paysage. "
                                "Utiliser plutôt des media queries pour adapter la présentation "
                                "sans restreindre l'orientation."
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": False,
                                "details": {k: v for k, v in issue.items() if k != "element"},
                            },
                        )
                    )
                elif issue_type == "js_orientation_event_listener":
                    # Écouteur orientationchange = NEEDS_REVIEW (peut être légitime pour adaptation)
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. "
                                "Vérifier que cet écouteur ne verrouille pas l'orientation "
                                "mais adapte seulement la présentation."
                            ),
                            recommendation=(
                                "Vérification manuelle requise : "
                                "1) L'écouteur orientationchange est-il utilisé pour ADAPTER "
                                "la présentation (réorganisation, tailles) ? -> CONFORME ; "
                                "2) L'écouteur est-il utilisé pour EMPÊCHER le changement "
                                "d'orientation ou masquer du contenu ? -> NON CONFORME ; "
                                "3) Le contenu proposé reste-t-il IDENTIQUE "
                                "dans les deux orientations ?"
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": False,
                                "details": {k: v for k, v in issue.items() if k != "element"},
                                "required_checks": [
                                    "vérifier adaptation présentation seulement (pas verrouillage)",
                                    "vérifier que le contenu proposé est identique",
                                    "vérifier qu'aucun contenu n'est masqué",
                                ],
                            },
                        )
                    )
                elif issue_type == "css_orientation_media_query":
                    # Media query orientation = NEEDS_REVIEW (peut être légitime pour adaptation présentation)
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. "
                                "Vérifier que cela n'empêche pas l'accès au contenu dans l'autre orientation."
                            ),
                            recommendation=(
                                "Vérification manuelle requise : "
                                "1) Le contenu est-il MASQUÉ (display:none, visibility:hidden) "
                                "dans une orientation ? -> NON CONFORME ; "
                                "2) La présentation est-elle seulement ADAPTÉE "
                                "(réorganisation, tailles différentes) ? -> CONFORME ; "
                                "3) Le contenu proposé reste-t-il IDENTIQUE "
                                "dans les deux orientations ?"
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": False,
                                "orientation": issue.get("orientation"),
                                "context": issue.get("context", "")[:500],
                                "details": {k: v for k, v in issue.items() if k != "element"},
                                "required_checks": [
                                    "vérifier qu'aucun contenu n'est masqué dans une orientation",
                                    "vérifier que le contenu proposé est identique",
                                    "vérifier que seule la présentation/moyen d'accès diffère",
                                ],
                            },
                        )
                    )
                elif issue_type == "orientation_specific_content":
                    # Contenu spécifique à une orientation = NEEDS_REVIEW
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"{issue['description']}. "
                                "Vérifier que le contenu n'est pas exclusivement disponible dans une seule orientation."
                            ),
                            recommendation=(
                                "Vérification manuelle requise : "
                                "1) Ce contenu est-il disponible dans l'autre orientation "
                                "(même info, présentation différente) ? -> CONFORME ; "
                                "2) Ce contenu est-il MASQUÉ/INACCESSIBLE "
                                "dans l'autre orientation ? -> NON CONFORME ; "
                                "3) S'agit-il d'une fonctionnalité légitimement liée "
                                "à l'orientation (ex: boussole) ? -> CAS PARTICULIER."
                            ),
                            evidence={
                                "issue_type": issue_type,
                                "is_essential_orientation": False,
                                "tag": issue.get("tag"),
                                "classes": issue.get("classes"),
                                "id": issue.get("id"),
                                "details": {k: v for k, v in issue.items() if k != "element"},
                                "required_checks": [
                                    "vérifier disponibilité du contenu dans l'autre orientation",
                                    "vérifier si c'est un cas particulier légitime",
                                ],
                            },
                        )
                    )

        tested_elements = len(all_issues)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} restriction(s) d'orientation détectée(s). "
                f"{non_compliant_count} non conforme(s) (verrouillage strict), "
                f"{needs_review_count} à vérifier manuellement."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} mécanisme(s) lié(s) à l'orientation détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle "
                "(media queries d'adaptation, contenu spécifique à une orientation)."
            )
        else:
            # Should not happen if we have issues but all were compliant (essential with alternative)
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} mécanisme(s) d'orientation détecté(s). "
                f"Tous sont conformes (cas particuliers avec alternative)."
            )

        metadata = {
            "total_issues": len(all_issues),
            "js_locks_count": len(js_locks),
            "js_event_listeners_count": len(js_event_listeners),
            "css_media_queries_count": len(css_media_queries),
            "viewport_restrictions_count": len(viewport_restrictions),
            "orientation_specific_content_count": len(orientation_specific_content),
            "non_compliant_count": non_compliant_count,
            "needs_review_count": needs_review_count,
            "is_essential_orientation": is_essential,
            "essential_reasons": essential_reasons,
            "required_manual_checks": [
                "vérifier que la consultation est possible en mode portrait ET paysage",
                "vérifier que le contenu proposé est identique dans les deux orientations",
                "vérifier que seule la présentation/moyen d'accès peut différer",
                "identifier les cas particuliers (jeux, piano, dépôt chèque, VR/AR, boussole, niveau, signature)",
                (
                    "si cas particulier : vérifier qu'une alternative accessible "
                    "est proposée si c'est le seul accès au service"
                ),
                "vérifier l'absence de screen.orientation.lock() ou verrouillage viewport",
                "vérifier que les @media (orientation:) ne masquent pas de contenu",
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

    def _get_issue_selector(self, soup: BeautifulSoup, issue: dict, index: int) -> str:
        """Generate a readable selector for an issue."""
        element = issue.get("element")
        issue_type = issue.get("type", "")

        if element is None:
            return f"{issue_type}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            tag = element.name or issue_type
            return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

        if element.name in ["style", "script", "meta"]:
            same_tag = soup.find_all(element.name)
            if len(same_tag) > 1:
                try:
                    return f"{element.name}[index={same_tag.index(element)}]"
                except ValueError:
                    pass
            return f"{element.name}[index={index}]"

        tag = element.name or issue_type
        same_tag = soup.find_all(tag)
        if len(same_tag) > 1:
            try:
                return f"{tag}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{tag}[index={index}]"

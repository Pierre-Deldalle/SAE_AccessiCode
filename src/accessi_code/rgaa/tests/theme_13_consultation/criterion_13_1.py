from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns for detecting refresh/redirect mechanisms
META_REFRESH_PATTERN = re.compile(
    r'<meta\s+http-equiv\s*=\s*["\']refresh["\']\s+content\s*=\s*["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)

META_REFRESH_CONTENT_PATTERN = re.compile(
    r"^\s*(\d+)\s*(?:;\s*url\s*=\s*([^;]+))?\s*$",
    flags=re.IGNORECASE,
)

# Pattern to detect JavaScript-based redirects/refreshes
JS_REDIRECT_PATTERNS = [
    re.compile(r'window\.location\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'window\.location\.href\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'window\.location\.replace\s*\(\s*["\'][^"\']+["\']\s*\)', re.IGNORECASE),
    re.compile(r'document\.location\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'location\.href\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'location\.replace\s*\(\s*["\'][^"\']+["\']\s*\)', re.IGNORECASE),
    re.compile(r'location\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
]

JS_TIMER_PATTERNS = [
    re.compile(r"setTimeout\s*\(\s*[^,)]+", re.IGNORECASE),
    re.compile(r"setInterval\s*\(\s*[^,)]+", re.IGNORECASE),
]

# Session timeout patterns (common patterns for session expiration)
JS_SESSION_TIMEOUT_PATTERNS = [
    re.compile(r"session\s*(?:timeout|expire)", re.IGNORECASE),
    re.compile(r"idle\s*(?:timeout|warning)", re.IGNORECASE),
    re.compile(r"auto\s*(?:logout|logoff)", re.IGNORECASE),
]


def _parse_meta_refresh_content(content: str) -> tuple[int | None, str | None]:
    """
    Parse the content attribute of a meta refresh tag.
    Returns (seconds, url) where url is None if not a redirect.
    """
    match = META_REFRESH_CONTENT_PATTERN.match(content.strip())
    if not match:
        return None, None

    try:
        seconds = int(match.group(1))
    except ValueError:
        return None, None

    url = match.group(2)
    if url:
        url = url.strip().strip("\"'")

    return seconds, url


def _has_user_control_mechanism(soup: BeautifulSoup, element_name: str, element_index: int) -> bool:
    """
    Check if there's a user control mechanism for the given element.
    This is a basic check - in practice, this requires manual verification.
    """
    # Look for buttons/links that might control the refresh/redirect
    # This is a heuristic - real implementation would need more sophisticated analysis
    controls = soup.find_all(
        ["button", "a", "input"],
        string=re.compile(
            r"(arrêter|stop|pause|relancer|restart|reprendre|augmenter|increase|prolonger|extend|avertir|warn|alerte|alert)",
            re.IGNORECASE,
        ),
    )
    return len(controls) > 0


def _find_meta_refresh_elements(soup: BeautifulSoup) -> list[dict]:
    """Find all meta refresh elements in the document head."""
    results = []
    head = soup.find("head")
    if not head:
        return results

    meta_tags = head.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.IGNORECASE)})

    for i, meta in enumerate(meta_tags):
        content = meta.get("content", "")
        if isinstance(content, str):
            seconds, url = _parse_meta_refresh_content(content)
            if seconds is not None:
                results.append(
                    {
                        "index": i,
                        "element": meta,
                        "seconds": seconds,
                        "url": url,
                        "is_redirect": url is not None,
                        "raw_content": content,
                    }
                )

    return results


def _find_embedded_refresh_elements(soup: BeautifulSoup) -> list[dict]:
    """Find object, embed, svg, canvas elements that may auto-refresh."""
    results = []
    tag_names = ["object", "embed", "svg", "canvas"]

    for tag_name in tag_names:
        elements = soup.find_all(tag_name)
        for i, elem in enumerate(elements):
            # Check for attributes that might indicate auto-refresh
            # This is heuristic - actual refresh behavior often requires JS
            results.append(
                {
                    "index": i,
                    "tag": tag_name,
                    "element": elem,
                    "attributes": dict(elem.attrs),
                }
            )

    return results


def _find_js_redirects(soup: BeautifulSoup) -> list[dict]:
    """Find JavaScript-based redirects in script tags."""
    results = []
    scripts = soup.find_all("script")

    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string

        # Check for redirect patterns
        for pattern in JS_REDIRECT_PATTERNS:
            if pattern.search(content):
                # Check if it's inside a timer
                has_timer = any(timer_pat.search(content) for timer_pat in JS_TIMER_PATTERNS)
                results.append(
                    {
                        "index": i,
                        "element": script,
                        "has_timer": has_timer,
                        "content_preview": content[:200],
                    }
                )
                break

    return results


def _find_session_timeouts(soup: BeautifulSoup) -> list[dict]:
    """Find potential session timeout mechanisms."""
    results = []

    # Check scripts
    scripts = soup.find_all("script")
    for i, script in enumerate(scripts):
        if not script.string:
            continue
        content = script.string
        for pattern in JS_SESSION_TIMEOUT_PATTERNS:
            if pattern.search(content):
                results.append(
                    {
                        "index": i,
                        "type": "script",
                        "element": script,
                        "content_preview": content[:200],
                    }
                )
                break

    # Check meta tags for session-related content
    meta_tags = soup.find_all("meta")
    for i, meta in enumerate(meta_tags):
        content = meta.get("content", "")
        name = meta.get("name", "")
        http_equiv = meta.get("http-equiv", "")

        # Check all relevant attributes for session/timeout/expire keywords
        check_attrs = []
        if isinstance(content, str):
            check_attrs.append(content)
        if isinstance(name, str):
            check_attrs.append(name)
        if isinstance(http_equiv, str):
            check_attrs.append(http_equiv)

        combined = " ".join(check_attrs).lower()
        if "session" in combined or "timeout" in combined or "expire" in combined:
            results.append(
                {
                    "index": i,
                    "type": "meta",
                    "element": meta,
                    "name": name,
                    "http_equiv": http_equiv,
                    "content": content,
                }
            )

    return results


class Test1311(RGAATest):
    """
    Test 13.1.1 : Pour chaque page web, chaque procédé de rafraîchissement
    (balise <object>, balise <embed>, balise <svg>, balise <canvas>,
    balise <meta>) vérifie-t-il une de ces conditions (hors cas particuliers) ?

    L'utilisateur peut arrêter ou relancer le rafraîchissement ;
    L'utilisateur peut augmenter la limite de temps entre deux rafraîchissements de dix fois, au moins ;
    L'utilisateur est averti de l'imminence du rafraîchissement et dispose de vingt secondes, au moins,
    pour augmenter la limite de temps avant le prochain rafraîchissement ;
    La limite de temps entre deux rafraîchissements est de vingt heures, au moins.
    """

    test_id = "13.1.1"
    criterion_id = "13.1"

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
                summary="Le DOM n'est pas disponible ; le test 13.1.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Find all refresh mechanisms
        meta_refreshes = _find_meta_refresh_elements(soup)
        embedded_refreshes = _find_embedded_refresh_elements(soup)

        all_refreshes = []
        for mr in meta_refreshes:
            if not mr["is_redirect"]:  # Only refreshes, not redirects
                all_refreshes.append(
                    {
                        "type": "meta_refresh",
                        "seconds": mr["seconds"],
                        "element": mr["element"],
                        "raw_content": mr["raw_content"],
                    }
                )

        for er in embedded_refreshes:
            all_refreshes.append(
                {
                    "type": er["tag"],
                    "seconds": None,  # Unknown without JS analysis
                    "element": er["element"],
                    "attributes": er["attributes"],
                }
            )

        if not all_refreshes:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun procédé de rafraîchissement automatique détecté (meta refresh, object, embed, svg, canvas)."
                ),
                tested_elements=0,
                metadata={
                    "meta_refresh_count": len(meta_refreshes),
                    "embedded_element_count": len(embedded_refreshes),
                },
            )

        # Analyze each refresh mechanism
        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, refresh in enumerate(all_refreshes):
            seconds = refresh.get("seconds")
            element = refresh["element"]
            refresh_type = refresh["type"]

            # Build a readable selector for the element
            selector = self._get_element_selector(soup, element, refresh_type, i)

            # Check compliance
            # For meta refresh with known interval:
            if seconds is not None:
                if seconds >= 72000:  # 20 hours = 72000 seconds
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=f"Rafraîchissement meta ({seconds}s) : intervalle ≥ 20 heures.",
                            recommendation="Conforme au critère 13.1.1 (condition 4).",
                            evidence={
                                "type": refresh_type,
                                "seconds": seconds,
                                "condition_met": "interval_20h_plus",
                            },
                        )
                    )
                elif seconds == 0:
                    # Immediate refresh - this is essentially a redirect, handled in 13.1.2
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=f"Rafraîchissement meta immédiat ({seconds}s) : vérification manuelle requise.",
                            recommendation=(
                                "Vérifier si c'est une redirection (test 13.1.2) ou un rafraîchissement légitime."
                            ),
                            evidence={
                                "type": refresh_type,
                                "seconds": seconds,
                                "needs_manual_check": True,
                            },
                        )
                    )
                else:
                    # Check for user control mechanisms
                    has_control = _has_user_control_mechanism(soup, refresh_type, i)
                    if has_control:
                        compliant_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Rafraîchissement {refresh_type} ({seconds}s) : "
                                    "mécanisme de contrôle utilisateur détecté."
                                ),
                                recommendation=(
                                    "Conforme au critère 13.1.1 (condition 1 ou 2). "
                                    "Vérifier manuellement l'accessibilité du contrôle."
                                ),
                                evidence={
                                    "type": refresh_type,
                                    "seconds": seconds,
                                    "condition_met": "user_control_detected",
                                },
                            )
                        )
                    else:
                        # Check if there's a warning mechanism (heuristic)
                        # This would need manual verification
                        needs_review_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=(
                                    f"Rafraîchissement {refresh_type} ({seconds}s) : "
                                    "aucun mécanisme de contrôle utilisateur détecté automatiquement. "
                                    "Vérification manuelle requise pour : "
                                    "1) arrêt/relance possible ; "
                                    "2) augmentation délai 10x ; "
                                    "3) avertissement 20s avant ; "
                                    "4) délai ≥ 20h."
                                ),
                                recommendation=(
                                    "Vérifier manuellement la présence d'un des mécanismes suivants : "
                                    "1) Bouton/lien pour arrêter/relancer le rafraîchissement ; "
                                    "2) Option pour augmenter le délai de 10x ; "
                                    "3) Avertissement 20s avant avec possibilité d'augmenter le délai ; "
                                    "4) Délai entre rafraîchissements ≥ 20 heures."
                                ),
                                evidence={
                                    "type": refresh_type,
                                    "seconds": seconds,
                                    "needs_manual_check": True,
                                    "checks_required": [
                                        "user_can_stop_restart",
                                        "user_can_increase_10x",
                                        "warning_20s_before",
                                        "interval_20h_plus",
                                    ],
                                },
                            )
                        )
            else:
                # Embedded elements (object, embed, svg, canvas) - interval unknown
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Élément {refresh_type} détecté : "
                            "impossible de déterminer l'intervalle de rafraîchissement automatiquement. "
                            "Vérification manuelle requise."
                        ),
                        recommendation=(
                            "Vérifier manuellement : "
                            "1) Si l'élément rafraîchit automatiquement son contenu ; "
                            "2) Si oui, présence d'un mécanisme de contrôle utilisateur ; "
                            "3) Si le délai est ≥ 20h."
                        ),
                        evidence={
                            "type": refresh_type,
                            "attributes": refresh.get("attributes", {}),
                            "needs_manual_check": True,
                        },
                    )
                )

        # Determine overall status
        tested_elements = len(all_refreshes)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} procédé(s) de rafraîchissement détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} procédé(s) de rafraîchissement détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} procédé(s) de rafraîchissement détecté(s). "
                f"Tous sont conformes au critère 13.1.1."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "meta_refresh_count": len(meta_refreshes),
                "embedded_element_count": len(embedded_refreshes),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "vérifier la présence de contrôles utilisateur accessibles (arrêt/relance)",
                    "vérifier l'option d'augmentation du délai (10x)",
                    "vérifier l'avertissement 20 secondes avant rafraîchissement",
                    "vérifier que le délai est ≥ 20 heures si applicable",
                    "vérifier l'accessibilité clavier des contrôles",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, refresh_type: str, index: int) -> str:
        """Generate a readable selector for an element."""
        if element is None:
            return f"{refresh_type}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            return f"{refresh_type}.{'.'.join(str(c) for c in classes[:2])}"

        if refresh_type in ["object", "embed", "svg", "canvas"]:
            same_tag = soup.find_all(refresh_type)
        else:
            same_tag = soup.find_all("meta")

        if len(same_tag) > 1:
            try:
                return f"{refresh_type}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{refresh_type}[index={index}]"


class Test1312(RGAATest):
    """
    Test 13.1.2 : Pour chaque page web, chaque procédé de redirection effectué via
    une balise <meta> est-il immédiat (hors cas particuliers) ?
    """

    test_id = "13.1.2"
    criterion_id = "13.1"

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
                summary="Le DOM n'est pas disponible ; le test 13.1.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        meta_refreshes = _find_meta_refresh_elements(soup)

        # Filter only redirects (meta refresh with URL)
        meta_redirects = [mr for mr in meta_refreshes if mr["is_redirect"]]

        if not meta_redirects:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary='Aucune redirection via balise <meta http-equiv="refresh"> détectée.',
                tested_elements=0,
                metadata={"meta_refresh_count": len(meta_refreshes)},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0

        for i, redirect in enumerate(meta_redirects):
            seconds = redirect["seconds"]
            url = redirect["url"]
            element = redirect["element"]

            selector = self._get_element_selector(soup, element, "meta", i)

            if seconds == 0:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=f"Redirection meta immédiate (0s) vers {url}.",
                        recommendation="Conforme au critère 13.1.2 : redirection immédiate.",
                        evidence={
                            "seconds": seconds,
                            "target_url": url,
                            "condition_met": "immediate_redirect",
                        },
                    )
                )
            else:
                non_compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=f"Redirection meta différée ({seconds}s) vers {url} : non immédiate.",
                        recommendation=(
                            "Le critère 13.1.2 exige une redirection immédiate (0 seconde). "
                            "Soit rendre la redirection immédiate, soit vérifier si le critère "
                            "est non applicable (cas particulier : redirection essentielle)."
                        ),
                        evidence={
                            "seconds": seconds,
                            "target_url": url,
                            "condition_met": "delayed_redirect",
                        },
                    )
                )

        tested_elements = len(meta_redirects)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} redirection(s) meta détectée(s). "
                f"{non_compliant_count} non immédiate(s), {compliant_count} immédiate(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} redirection(s) meta détectée(s). "
                f"Toutes sont immédiates (conformes au critère 13.1.2)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "meta_redirect_count": len(meta_redirects),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "required_manual_checks": [
                    "vérifier si la redirection différée est un cas particulier (redirection essentielle)",
                    "vérifier l'accessibilité de la redirection pour les technologies d'assistance",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
        """Generate a readable selector for a meta element."""
        if element is None:
            return f"{tag}[index={index}]"

        # Meta elements typically don't have IDs, use index
        same_tag = soup.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.IGNORECASE)})
        if len(same_tag) > 1:
            try:
                return f"meta[http-equiv=refresh][index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"meta[http-equiv=refresh][index={index}]"


class Test1313(RGAATest):
    """
    Test 13.1.3 : Pour chaque page web, chaque procédé de redirection effectué via
    un script vérifie-t-il une de ces conditions (hors cas particuliers) ?

    L'utilisateur peut arrêter ou relancer la redirection ;
    L'utilisateur peut augmenter la limite de temps avant la redirection de dix fois, au moins ;
    L'utilisateur est averti de l'imminence de la redirection et dispose de vingt secondes, au moins,
    pour augmenter la limite de temps avant la prochaine redirection ;
    La limite de temps avant la redirection est de vingt heures, au moins.
    """

    test_id = "13.1.3"
    criterion_id = "13.1"

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
                summary="Le DOM n'est pas disponible ; le test 13.1.3 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        js_redirects = _find_js_redirects(soup)

        if not js_redirects:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune redirection via script détectée.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, redirect in enumerate(js_redirects):
            has_timer = redirect["has_timer"]
            element = redirect["element"]
            content_preview = redirect["content_preview"]

            selector = self._get_element_selector(soup, element, "script", i)

            if has_timer:
                # There's a setTimeout/setInterval - check for user control
                has_control = _has_user_control_mechanism(soup, "script_redirect", i)

                if has_control:
                    compliant_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                "Redirection script avec temporisation : mécanisme de contrôle utilisateur détecté."
                            ),
                            recommendation=(
                                "Conforme au critère 13.1.3 (condition 1 ou 2). Vérifier manuellement l'accessibilité."
                            ),
                            evidence={
                                "has_timer": True,
                                "condition_met": "user_control_detected",
                                "content_preview": content_preview,
                            },
                        )
                    )
                else:
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                "Redirection script avec temporisation détectée : "
                                "aucun mécanisme de contrôle utilisateur détecté automatiquement. "
                                "Vérification manuelle requise pour : "
                                "1) arrêt/relance possible ; "
                                "2) augmentation délai 10x ; "
                                "3) avertissement 20s avant ; "
                                "4) délai ≥ 20h."
                            ),
                            recommendation=(
                                "Vérifier manuellement la présence d'un des mécanismes suivants : "
                                "1) Bouton/lien pour arrêter/relancer la redirection ; "
                                "2) Option pour augmenter le délai de 10x ; "
                                "3) Avertissement 20s avant avec possibilité d'augmenter le délai ; "
                                "4) Délai avant redirection ≥ 20 heures."
                            ),
                            evidence={
                                "has_timer": True,
                                "needs_manual_check": True,
                                "checks_required": [
                                    "user_can_stop_restart",
                                    "user_can_increase_10x",
                                    "warning_20s_before",
                                    "delay_20h_plus",
                                ],
                                "content_preview": content_preview,
                            },
                        )
                    )
            else:
                # Immediate redirect without timer - could be user-triggered
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            "Redirection script immédiate détectée : "
                            "vérifier si elle est déclenchée par action utilisateur."
                        ),
                        recommendation=(
                            "Vérifier manuellement : "
                            "1) Si la redirection est déclenchée par une action utilisateur "
                            "explicite (clic, soumission) -> conforme ; "
                            "2) Si elle est automatique -> appliquer les conditions "
                            "du critère 13.1.3 ; "
                            "3) Si c'est une redirection essentielle (cas particulier) -> "
                            "non applicable."
                        ),
                        evidence={
                            "has_timer": False,
                            "needs_manual_check": True,
                            "content_preview": content_preview,
                        },
                    )
                )

        tested_elements = len(js_redirects)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} redirection(s) script détectée(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} redirection(s) script détectée(s). "
                f"{needs_review_count} nécessitent une vérification manuelle, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} redirection(s) script détectée(s). "
                f"Toutes sont conformes au critère 13.1.3."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "js_redirect_count": len(js_redirects),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "vérifier si la redirection est déclenchée par action utilisateur",
                    "vérifier la présence de contrôles utilisateur accessibles (arrêt/relance)",
                    "vérifier l'option d'augmentation du délai (10x)",
                    "vérifier l'avertissement 20 secondes avant redirection",
                    "vérifier que le délai est ≥ 20 heures si applicable",
                    "vérifier si c'est un cas particulier (redirection essentielle)",
                    "vérifier l'accessibilité clavier des contrôles",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
        """Generate a readable selector for a script element."""
        if element is None:
            return f"{tag}[index={index}]"

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


class Test1314(RGAATest):
    """
    Test 13.1.4 : Pour chaque page web, chaque procédé limitant le temps d'une session
    vérifie-t-il une de ces conditions (hors cas particuliers) ?

    L'utilisateur peut supprimer la limite de temps ;
    L'utilisateur peut augmenter la limite de temps ;
    La limite de temps avant la fin de la session est de vingt heures au moins.
    """

    test_id = "13.1.4"
    criterion_id = "13.1"

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
                summary="Le DOM n'est pas disponible ; le test 13.1.4 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        session_timeouts = _find_session_timeouts(soup)

        if not session_timeouts:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun procédé de limitation de temps de session détecté.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, timeout in enumerate(session_timeouts):
            element = timeout["element"]
            timeout_type = timeout["type"]

            selector = self._get_element_selector(soup, element, timeout_type, i)

            # Check for user control mechanisms
            has_control = _has_user_control_mechanism(soup, "session_timeout", i)

            if has_control:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(f"Limite de session ({timeout_type}) : mécanisme de contrôle utilisateur détecté."),
                        recommendation=(
                            "Conforme au critère 13.1.4 (condition 1 ou 2). Vérifier manuellement l'accessibilité."
                        ),
                        evidence={
                            "type": timeout_type,
                            "condition_met": "user_control_detected",
                        },
                    )
                )
            else:
                # Check meta tag for explicit timeout value
                if timeout_type == "meta":
                    content = timeout.get("content", "")
                    # Try to extract timeout value
                    match = re.search(r"(\d+)", content)
                    if match:
                        try:
                            seconds = int(match.group(1))
                            if seconds >= 72000:  # 20 hours
                                compliant_count += 1
                                findings.append(
                                    Finding(
                                        element=selector,
                                        message=f"Limite de session meta : {seconds}s (≥ 20h).",
                                        recommendation="Conforme au critère 13.1.4 (condition 3).",
                                        evidence={
                                            "type": timeout_type,
                                            "seconds": seconds,
                                            "condition_met": "timeout_20h_plus",
                                        },
                                    )
                                )
                            else:
                                needs_review_count += 1
                                findings.append(
                                    Finding(
                                        element=selector,
                                        message=(
                                            f"Limite de session meta : {seconds}s (< 20h). "
                                            "Aucun mécanisme de contrôle utilisateur détecté."
                                        ),
                                        recommendation=(
                                            "Vérifier manuellement : "
                                            "1) Possibilité pour l'utilisateur de supprimer la limite ; "
                                            "2) Possibilité pour l'utilisateur d'augmenter la limite ; "
                                            "3) Si c'est un cas particulier (limite essentielle) -> non applicable."
                                        ),
                                        evidence={
                                            "type": timeout_type,
                                            "seconds": seconds,
                                            "needs_manual_check": True,
                                            "checks_required": [
                                                "user_can_remove_limit",
                                                "user_can_increase_limit",
                                                "essential_limit_exception",
                                            ],
                                        },
                                    )
                                )
                        except ValueError:
                            needs_review_count += 1
                            findings.append(
                                Finding(
                                    element=selector,
                                    message=(f"Limite de session meta détectée mais valeur non parsable : {content}."),
                                    recommendation=(
                                        "Vérifier manuellement la durée et la présence de contrôles utilisateur."
                                    ),
                                    evidence={
                                        "type": timeout_type,
                                        "content": content,
                                        "needs_manual_check": True,
                                    },
                                )
                            )
                    else:
                        needs_review_count += 1
                        findings.append(
                            Finding(
                                element=selector,
                                message=f"Limite de session meta détectée : {content}.",
                                recommendation=(
                                    "Vérifier manuellement la durée et la présence de contrôles utilisateur."
                                ),
                                evidence={
                                    "type": timeout_type,
                                    "content": content,
                                    "needs_manual_check": True,
                                },
                            )
                        )
                else:
                    # Script-based session timeout
                    needs_review_count += 1
                    findings.append(
                        Finding(
                            element=selector,
                            message=(
                                f"Limite de session script détectée ({timeout.get('content_preview', '')[:100]}...). "
                                "Aucun mécanisme de contrôle utilisateur détecté automatiquement."
                            ),
                            recommendation=(
                                "Vérifier manuellement : "
                                "1) Possibilité pour l'utilisateur de supprimer la limite "
                                "de temps ; "
                                "2) Possibilité pour l'utilisateur d'augmenter la limite "
                                "de temps ; "
                                "3) Si la limite est ≥ 20 heures ; "
                                "4) Si c'est un cas particulier (limite essentielle, "
                                "ex: session bancaire) -> non applicable."
                            ),
                            evidence={
                                "type": timeout_type,
                                "needs_manual_check": True,
                                "checks_required": [
                                    "user_can_remove_limit",
                                    "user_can_increase_limit",
                                    "timeout_20h_plus",
                                    "essential_limit_exception",
                                ],
                            },
                        )
                    )

        tested_elements = len(session_timeouts)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} limite(s) de session détectée(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} limite(s) de session détectée(s). "
                f"{needs_review_count} nécessitent une vérification manuelle, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} limite(s) de session détectée(s). "
                f"Toutes sont conformes au critère 13.1.4."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "session_timeout_count": len(session_timeouts),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "vérifier la possibilité pour l'utilisateur de supprimer la limite",
                    "vérifier la possibilité pour l'utilisateur d'augmenter la limite",
                    "vérifier si la limite est ≥ 20 heures",
                    "vérifier si c'est un cas particulier "
                    "(limite essentielle : ex. session bancaire, test chronométré)",
                    "vérifier l'accessibilité clavier des contrôles de session",
                    "vérifier l'avertissement avant expiration de session",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, timeout_type: str, index: int) -> str:
        """Generate a readable selector for a session timeout element."""
        if element is None:
            return f"{timeout_type}[index={index}]"

        if timeout_type == "meta":
            element_id = element.get("id")
            if isinstance(element_id, str) and element_id:
                return f"#{element_id}"
            metas = soup.find_all("meta")
            if len(metas) > 1:
                try:
                    return f"meta[index={metas.index(element)}]"
                except ValueError:
                    pass
            return f"meta[index={index}]"
        else:
            # script
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

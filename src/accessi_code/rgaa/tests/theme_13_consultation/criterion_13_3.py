from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Office document file extensions
OFFICE_EXTENSIONS = {
    "pdf": "PDF",
    "doc": "DOC",
    "docx": "DOCX",
    "odt": "ODT",
    "epub": "EPUB",
    "daisy": "DAISY",
}

# Patterns to detect download links
DOWNLOAD_LINK_PATTERNS = [
    re.compile(r"télécharger", re.IGNORECASE),
    re.compile(r"download", re.IGNORECASE),
    re.compile(r"téléchargement", re.IGNORECASE),
    re.compile(r"ouvrir", re.IGNORECASE),
    re.compile(r"open", re.IGNORECASE),
    re.compile(r"afficher", re.IGNORECASE),
    re.compile(r"view", re.IGNORECASE),
]

# Additional patterns for buttons that might open documents
DOCUMENT_BUTTON_PATTERNS = [
    re.compile(r"pdf", re.IGNORECASE),
    re.compile(r"doc", re.IGNORECASE),
    re.compile(r"word", re.IGNORECASE),
    re.compile(r"odt", re.IGNORECASE),
    re.compile(r"epub", re.IGNORECASE),
    re.compile(r"daisy", re.IGNORECASE),
]

# File extension pattern at the end of URLs
FILE_EXTENSION_PATTERN = re.compile(r"\.([a-z0-9]+)(?:\?|#|$)", re.IGNORECASE)


def _is_office_document_url(url: str) -> tuple[bool, str | None]:
    """
    Check if a URL points to an office document.
    Returns (is_office_document, format_name).
    """
    parsed = urlparse(url)
    path = parsed.path.lower()

    match = FILE_EXTENSION_PATTERN.search(path)
    if not match:
        return False, None

    ext = match.group(1).lower()
    if ext in OFFICE_EXTENSIONS:
        return True, OFFICE_EXTENSIONS[ext]

    return False, None


def _find_download_links(soup: BeautifulSoup, base_url: str | None = None) -> list[dict]:
    """
    Find all links and form controls that may allow downloading office documents.
    """
    results = []

    # Find <a> tags with href
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not isinstance(href, str):
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url or "", href) if base_url else href

        is_office, format_name = _is_office_document_url(full_url)
        if is_office:
            results.append(
                {
                    "type": "link",
                    "element": link,
                    "url": full_url,
                    "format": format_name,
                    "text": link.get_text(strip=True),
                    "title": link.get("title", ""),
                }
            )

    # Find <button> and <input type="submit"> that might trigger downloads
    # Look for buttons/forms with download-related text OR document-related text
    for button in soup.find_all(["button", "input"]):
        if button.name == "input" and button.get("type") not in ["submit", "button"]:
            continue

        button_text = ""
        if button.name == "button":
            button_text = button.get_text(strip=True)
        elif button.name == "input":
            button_text = button.get("value", "") or ""

        # Check if button text suggests download or document
        is_download_button = any(pattern.search(button_text) for pattern in DOWNLOAD_LINK_PATTERNS)
        is_document_button = any(pattern.search(button_text) for pattern in DOCUMENT_BUTTON_PATTERNS)

        # Also check onclick for office document URLs regardless of button text
        onclick = button.get("onclick", "")
        has_office_onclick = False
        onclick_urls = []
        if isinstance(onclick, str):
            url_matches = re.findall(r'["\']([^"\']+\.(?:pdf|doc|docx|odt|epub|daisy))["\']', onclick, re.IGNORECASE)
            for url_match in url_matches:
                full_url = urljoin(base_url or "", url_match) if base_url else url_match
                is_office, format_name = _is_office_document_url(full_url)
                if is_office:
                    onclick_urls.append((full_url, format_name))
                    has_office_onclick = True

        if is_download_button or is_document_button or has_office_onclick:
            # Try to find associated form action
            form = button.find_parent("form")
            action_url = ""
            if form and form.get("action"):
                action_url = urljoin(base_url or "", form.get("action", "")) if base_url else form.get("action", "")

            # Handle onclick URLs
            for full_url, format_name in onclick_urls:
                results.append(
                    {
                        "type": "button",
                        "element": button,
                        "url": full_url,
                        "format": format_name,
                        "text": button_text,
                        "source": "onclick",
                    }
                )

            # Handle form action
            if action_url:
                is_office, format_name = _is_office_document_url(action_url)
                if is_office:
                    results.append(
                        {
                            "type": "form_button",
                            "element": button,
                            "url": action_url,
                            "format": format_name,
                            "text": button_text,
                            "source": "form_action",
                        }
                    )

    return results


def _find_alternative_links(soup: BeautifulSoup, base_url: str | None = None) -> list[dict]:
    """
    Find links that may be accessible alternatives (HTML versions, accessible PDFs, etc.).
    """
    results = []

    # Patterns for HTML alternatives (most reliable)
    html_alternative_patterns = [
        re.compile(r"version\s+accessible", re.IGNORECASE),
        re.compile(r"accessible\s+version", re.IGNORECASE),
        re.compile(r"version\s+html", re.IGNORECASE),
        re.compile(r"html\s+accessible", re.IGNORECASE),
        re.compile(r"version\s+en\s+html", re.IGNORECASE),
        re.compile(r"\bhtml$", re.IGNORECASE),  # Link text ending with "HTML" (e.g., "Rapport annuel HTML")
        re.compile(r"^html$", re.IGNORECASE),  # Exact match "HTML"
        re.compile(r"texte\s+seul", re.IGNORECASE),
        re.compile(r"version\s+texte", re.IGNORECASE),
        re.compile(r"alternative\s+accessible", re.IGNORECASE),
        re.compile(r"accessible\s+alternative", re.IGNORECASE),
        re.compile(r"^accessible$", re.IGNORECASE),  # Exact match "Accessible"
        re.compile(r"^version\s+accessible$", re.IGNORECASE),  # Exact match "Version accessible"
    ]

    # Patterns for accessible office document alternatives (require explicit "accessible")
    office_alternative_patterns = [
        re.compile(r"version\s+accessible", re.IGNORECASE),
        re.compile(r"accessible\s+version", re.IGNORECASE),
        re.compile(r"version\s+pdf\s+accessible", re.IGNORECASE),
        re.compile(r"pdf\s+accessible", re.IGNORECASE),
        re.compile(r"alternative\s+accessible", re.IGNORECASE),
        re.compile(r"accessible\s+alternative", re.IGNORECASE),
        re.compile(r"^accessible$", re.IGNORECASE),  # Exact match "Accessible"
        re.compile(r"^version\s+accessible$", re.IGNORECASE),  # Exact match "Version accessible"
        re.compile(r"tagg[eé]", re.IGNORECASE),  # "taggé", "taggee" for accessible PDF
    ]

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not isinstance(href, str):
            continue

        full_url = urljoin(base_url or "", href) if base_url else href
        link_text = link.get_text(strip=True)
        title = link.get("title", "") or ""

        is_office, format_name = _is_office_document_url(full_url)
        is_html = not is_office

        # Check if link suggests accessible alternative
        is_alternative = False

        if is_html:
            # HTML links: use HTML alternative patterns
            is_alternative = any(
                pattern.search(link_text) or pattern.search(title) for pattern in html_alternative_patterns
            )
        else:
            # Office document links: require explicit "accessible" or "taggé" keywords
            is_alternative = any(
                pattern.search(link_text) or pattern.search(title) for pattern in office_alternative_patterns
            )

        if is_alternative:
            results.append(
                {
                    "element": link,
                    "url": full_url,
                    "format": format_name or "HTML" if not is_office else format_name,
                    "text": link_text,
                    "is_html": is_html,
                }
            )

    return results


class Test1331(RGAATest):
    """
    Test 13.3.1 : Dans chaque page web, chaque fonctionnalité de téléchargement
    d'un document bureautique vérifie-t-elle une de ces conditions (hors cas particuliers) ?

    Le document en téléchargement est compatible avec l'accessibilité ;
    Il en existe une version alternative en téléchargement compatible avec l'accessibilité ;
    Il en existe une version alternative au format HTML compatible avec l'accessibilité.
    """

    test_id = "13.3.1"
    criterion_id = "13.3"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.SOURCE_FILES,
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
                summary="Le DOM n'est pas disponible ; le test 13.3.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Get base URL for resolving relative links
        base_url = getattr(context, "html_path", None)
        if base_url and hasattr(base_url, "as_posix"):
            base_url = base_url.as_posix()

        # Find all download links for office documents
        download_links = _find_download_links(soup, base_url)

        # Find potential accessible alternatives
        alternative_links = _find_alternative_links(soup, base_url)

        # Exclude alternative links from download links (by URL)
        alternative_urls = {alt["url"] for alt in alternative_links}
        download_links = [dl for dl in download_links if dl["url"] not in alternative_urls]

        if not download_links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien de téléchargement de document bureautique détecté.",
                tested_elements=0,
                metadata={},
            )

        # Analyze each download link
        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, dl in enumerate(download_links):
            url = dl["url"]
            format_name = dl["format"]
            element = dl["element"]
            link_text = dl["text"]

            selector = self._get_element_selector(soup, element, "a", i)

            # Check if there's an accessible alternative on the page
            has_alternative = False
            alternative_info = None

            for alt in alternative_links:
                # Heuristic: same base filename or similar text
                if self._is_likely_alternative(url, alt["url"], link_text, alt["text"]):
                    has_alternative = True
                    alternative_info = alt
                    break

            if has_alternative:
                compliant_count += 1
                alt_type = "HTML" if alternative_info["is_html"] else alternative_info["format"]
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Document {format_name} en téléchargement : "
                            f"version alternative {alt_type} détectée ({alternative_info['text']})."
                        ),
                        recommendation=(
                            f"Vérifier manuellement que la version alternative {alt_type} "
                            f"est bien accessible selon les critères RGAA."
                        ),
                        evidence={
                            "download_url": url,
                            "format": format_name,
                            "alternative_url": alternative_info["url"],
                            "alternative_type": alt_type,
                            "condition_met": "alternative_found",
                        },
                    )
                )
            else:
                # No alternative found on page - document itself must be accessible
                # This requires external tools (PAC, MS Office, etc.) - mark as NEEDS_REVIEW
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Document {format_name} en téléchargement : {link_text or url}. "
                            "Aucune version alternative accessible détectée sur la page. "
                            "Le document lui-même doit être accessible."
                        ),
                        recommendation=(
                            f"Vérifier l'accessibilité du document {format_name} : "
                            f"{self._get_verification_method(format_name)}"
                        ),
                        evidence={
                            "download_url": url,
                            "format": format_name,
                            "needs_manual_check": True,
                            "verification_method": self._get_verification_method(format_name),
                            "checks_required": [
                                "document_accessible",
                                "alternative_accessible_version_exists",
                                "alternative_html_version_exists",
                            ],
                        },
                    )
                )

        tested_elements = len(download_links)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} document(s) bureautique(s) en téléchargement détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} avec alternative détectée."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} document(s) bureautique(s) en téléchargement détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle de l'accessibilité du document, "
                f"{compliant_count} avec alternative détectée."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} document(s) bureautique(s) en téléchargement détecté(s). "
                f"Tous ont une version alternative détectée sur la page."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "download_count": len(download_links),
                "alternative_links_count": len(alternative_links),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "formats_found": list({dl["format"] for dl in download_links}),
                "required_manual_checks": [
                    (
                        "vérifier l'accessibilité de chaque document bureautique "
                        "(PAC pour PDF, vérificateur Office pour DOC/DOCX, etc.)"
                    ),
                    "vérifier l'existence de versions alternatives accessibles non détectées automatiquement",
                    (
                        "vérifier les cas particuliers "
                        "(documents publiés avant 23/09/2018 pour personnes de droit privé)"
                    ),
                    "vérifier que les versions alternatives HTML sont conformes RGAA",
                ],
            },
        )

    def _is_likely_alternative(
        self,
        download_url: str,
        alt_url: str,
        download_text: str,
        alt_text: str,
    ) -> bool:
        """
        Heuristic to determine if an alternative link corresponds to a download link.
        """
        # Compare base filenames
        download_filename = urlparse(download_url).path.split("/")[-1].lower()
        alt_filename = urlparse(alt_url).path.split("/")[-1].lower()

        # Remove extensions for comparison
        download_base = download_filename.rsplit(".", 1)[0] if "." in download_filename else download_filename
        alt_base = alt_filename.rsplit(".", 1)[0] if "." in alt_filename else alt_filename

        # Same base name suggests alternative
        if download_base and download_base == alt_base:
            return True

        # Similar base name (e.g., "document" and "document-accessible")
        if download_base and alt_base:
            # Check if one base name is contained in the other
            if download_base in alt_base or alt_base in download_base:
                return True

        # Similar text content
        if download_text.lower() in alt_text.lower() or alt_text.lower() in download_text.lower():
            return True

        # Check for common words (excluding stop words)
        download_words = set(re.findall(r"\w+", download_text.lower()))
        alt_words = set(re.findall(r"\w+", alt_text.lower()))
        common_words = download_words & alt_words
        # Remove common stop words
        stop_words = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "de",
            "du",
            "des",
            "et",
            "ou",
            "à",
            "au",
            "aux",
            "en",
            "pour",
            "avec",
            "sans",
            "sur",
            "dans",
            "version",
            "accessible",
            "html",
            "pdf",
            "doc",
            "docx",
            "odt",
            "epub",
            "daisy",
            "télécharger",
            "download",
            "ouvrir",
            "open",
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "for",
            "with",
            "without",
            "in",
            "on",
            "at",
            "by",
            "from",
        }
        meaningful_common = common_words - stop_words
        if len(meaningful_common) >= 2:  # At least 2 meaningful common words
            return True

        return False

    def _get_verification_method(self, format_name: str) -> str:
        """Get the verification method for a given format."""
        methods = {
            "PDF": (
                "Analyser avec PAC (PDF Accessibility Checker) - "
                "vérifier l'absence d'erreurs selon la "
                "'Liste document bureautique en téléchargement'"
            ),
            "DOC": (
                "Analyser avec le vérificateur d'accessibilité Microsoft Office "
                "(Fichier > Informations > Vérifier l'accessibilité)"
            ),
            "DOCX": (
                "Analyser avec le vérificateur d'accessibilité Microsoft Office "
                "(Fichier > Informations > Vérifier l'accessibilité)"
            ),
            "ODT": (
                "Analyser avec OpenOffice/LibreOffice selon la "
                "'Liste document bureautique en téléchargement' "
                "(ou convertir en DOCX et vérifier via Office)"
            ),
            "EPUB": "Analyser avec Ace by DAISY App pour valider EPUB 3",
            "DAISY": ("Analyser avec un éditeur DAISY selon la 'Liste document bureautique en téléchargement'"),
        }
        return methods.get(
            format_name,
            "Vérification manuelle selon la 'Liste document bureautique en téléchargement'",
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
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

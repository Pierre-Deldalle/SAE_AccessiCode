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

# Patterns for HTML alternatives (most reliable)
HTML_ALTERNATIVE_PATTERNS = [
    re.compile(r"version\s+accessible", re.IGNORECASE),
    re.compile(r"accessible\s+version", re.IGNORECASE),
    re.compile(r"version\s+html", re.IGNORECASE),
    re.compile(r"html\s+accessible", re.IGNORECASE),
    re.compile(r"version\s+en\s+html", re.IGNORECASE),
    re.compile(r"\bhtml$", re.IGNORECASE),  # Link text ending with "HTML"
    re.compile(r"^html$", re.IGNORECASE),  # Exact match "HTML"
    re.compile(r"texte\s+seul", re.IGNORECASE),
    re.compile(r"version\s+texte", re.IGNORECASE),
    re.compile(r"alternative\s+accessible", re.IGNORECASE),
    re.compile(r"accessible\s+alternative", re.IGNORECASE),
    re.compile(r"^accessible$", re.IGNORECASE),  # Exact match "Accessible"
    re.compile(r"^version\s+accessible$", re.IGNORECASE),  # Exact match "Version accessible"
]

# Patterns for accessible office document alternatives (require explicit "accessible")
OFFICE_ALTERNATIVE_PATTERNS = [
    re.compile(r"version\s+accessible", re.IGNORECASE),
    re.compile(r"accessible\s+version", re.IGNORECASE),
    re.compile(r"version\s+pdf\s+accessible", re.IGNORECASE),
    re.compile(r"pdf\s+accessible", re.IGNORECASE),
    re.compile(r"alternative\s+accessible", re.IGNORECASE),
    re.compile(r"accessible\s+alternative", re.IGNORECASE),
    re.compile(r"^accessible$", re.IGNORECASE),
    re.compile(r"^version\s+accessible$", re.IGNORECASE),
    re.compile(r"tagg[eé]", re.IGNORECASE),  # "taggé", "taggee" for accessible PDF
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
    for button in soup.find_all(["button", "input"]):
        if button.name == "input" and button.get("type") not in ["submit", "button"]:
            continue

        button_text = ""
        if button.name == "button":
            button_text = button.get_text(strip=True)
        elif button.name == "input":
            button_text = button.get("value", "") or ""

        # Check onclick for office document URLs
        onclick = button.get("onclick", "")
        onclick_urls = []
        if isinstance(onclick, str):
            url_matches = re.findall(r'["\']([^"\']+\.(?:pdf|doc|docx|odt|epub|daisy))["\']', onclick, re.IGNORECASE)
            for url_match in url_matches:
                full_url = urljoin(base_url or "", url_match) if base_url else url_match
                is_office, format_name = _is_office_document_url(full_url)
                if is_office:
                    onclick_urls.append((full_url, format_name))

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
        form = button.find_parent("form")
        if form and form.get("action"):
            action_url = urljoin(base_url or "", form.get("action", "")) if base_url else form.get("action", "")
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
                pattern.search(link_text) or pattern.search(title) for pattern in HTML_ALTERNATIVE_PATTERNS
            )
        else:
            # Office document links: require explicit "accessible" or "taggé" keywords
            is_alternative = any(
                pattern.search(link_text) or pattern.search(title) for pattern in OFFICE_ALTERNATIVE_PATTERNS
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


def _get_base_filename(url: str) -> str:
    """Extract base filename without extension from URL."""
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1]
    if "." in filename:
        return filename.rsplit(".", 1)[0].lower()
    return filename.lower()


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_likely_alternative_pair(
    download_url: str,
    alt_url: str,
    download_text: str,
    alt_text: str,
) -> bool:
    """
    Heuristic to determine if an alternative link corresponds to a download link.
    """
    # Compare base filenames
    download_base = _get_base_filename(download_url)
    alt_base = _get_base_filename(alt_url)

    # Same base name suggests alternative
    if download_base and download_base == alt_base:
        return True

    # Similar base name (e.g., "document" and "document-accessible")
    if download_base and alt_base:
        if download_base in alt_base or alt_base in download_base:
            return True

    # Similar text content
    norm_download = _normalize_text(download_text)
    norm_alt = _normalize_text(alt_text)
    if norm_download and norm_alt:
        if norm_download in norm_alt or norm_alt in norm_download:
            return True

    # Check for common meaningful words
    download_words = set(re.findall(r"\w+", norm_download))
    alt_words = set(re.findall(r"\w+", norm_alt))
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
    if len(meaningful_common) >= 2:
        return True

    return False


class Test1341(RGAATest):
    """
    Test 13.4.1 : Pour chaque document bureautique ayant une version accessible,
    vérifie-t-il une de ces conditions ?

    La version compatible avec l'accessibilité offre la même information ;
    La version alternative au format HTML est pertinente et offre la même information.
    """

    test_id = "13.4.1"
    criterion_id = "13.4"

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
                summary="Le DOM n'est pas disponible ; le test 13.4.1 nécessite l'analyse de la page.",
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

        if not alternative_links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Document(s) bureautique(s) en téléchargement détecté(s) mais aucune "
                    "version alternative accessible n'est indiquée sur la page."
                ),
                tested_elements=0,
                metadata={
                    "download_count": len(download_links),
                    "formats_found": list({dl["format"] for dl in download_links}),
                },
            )

        # Match download links with their alternatives
        pairs = []
        unmatched_downloads = []

        for dl in download_links:
            matched = False
            for alt in alternative_links:
                if _is_likely_alternative_pair(
                    dl["url"],
                    alt["url"],
                    dl["text"],
                    alt["text"],
                ):
                    pairs.append(
                        {
                            "download": dl,
                            "alternative": alt,
                        }
                    )
                    matched = True
                    break

            if not matched:
                unmatched_downloads.append(dl)

        if not pairs:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Document(s) bureautique(s) et alternative(s) détectée(s) mais "
                    "aucun couple document/version accessible n'a pu être associé automatiquement."
                ),
                tested_elements=0,
                metadata={
                    "download_count": len(download_links),
                    "alternative_count": len(alternative_links),
                    "unmatched_downloads": len(unmatched_downloads),
                },
            )

        # Analyze each pair
        findings: list[Finding] = []
        needs_review_count = 0
        compliant_count = 0

        for i, pair in enumerate(pairs):
            download = pair["download"]
            alternative = pair["alternative"]

            dl_url = download["url"]
            dl_format = download["format"]
            dl_text = download["text"]
            alt_url = alternative["url"]
            alt_format = alternative["format"]
            alt_text = alternative["text"]
            alt_is_html = alternative["is_html"]

            selector = self._get_element_selector(soup, download["element"], "a", i)

            # This test requires content comparison between the original document
            # and its accessible alternative. This cannot be determined automatically
            # from the HTML page alone - it requires examining the actual documents.
            # Mark as NEEDS_REVIEW for manual verification.
            needs_review_count += 1
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Couple détecté : document {dl_format} ({dl_text or dl_url}) "
                        f"→ version alternative {alt_format} ({alt_text or alt_url}). "
                        "Vérification manuelle requise : les deux versions offrent-elles la même information ?"
                    ),
                    recommendation=(
                        f"Ouvrir les deux documents ({dl_format} et {alt_format}) et comparer "
                        f"leur contenu. Vérifier que la version {alt_format} offre la même "
                        f"information que le document original."
                    ),
                    evidence={
                        "download_url": dl_url,
                        "download_format": dl_format,
                        "download_text": dl_text,
                        "alternative_url": alt_url,
                        "alternative_format": alt_format,
                        "alternative_text": alt_text,
                        "alternative_is_html": alt_is_html,
                        "needs_manual_check": True,
                        "checks_required": [
                            "same_information",
                            "alternative_relevant",
                        ],
                    },
                )
            )

        # Also report unmatched downloads that don't have a paired alternative
        for i, dl in enumerate(unmatched_downloads):
            selector = self._get_element_selector(soup, dl["element"], "a", len(pairs) + i)
            needs_review_count += 1
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Document {dl['format']} en téléchargement ({dl['text'] or dl['url']}) : "
                        "aucune version alternative accessible associée détectée sur la page. "
                        "Si une version accessible existe, vérifier qu'elle offre la même information."
                    ),
                    recommendation=(
                        "Vérifier manuellement si une version accessible de ce document existe "
                        "et si elle offre la même information."
                    ),
                    evidence={
                        "download_url": dl["url"],
                        "format": dl["format"],
                        "text": dl["text"],
                        "needs_manual_check": True,
                        "checks_required": [
                            "accessible_version_exists",
                            "same_information",
                        ],
                    },
                )
            )

        tested_elements = len(pairs) + len(unmatched_downloads)

        # This test always requires manual verification since content comparison
        # between documents cannot be automated reliably
        status = TestStatus.NEEDS_REVIEW
        summary = (
            f"Analyse terminée : {tested_elements} élément(s) concerné(s). "
            f"{len(pairs)} couple(s) document/alternative détecté(s), "
            f"{len(unmatched_downloads)} document(s) sans alternative associée. "
            f"Tous nécessitent une vérification manuelle de l'équivalence du contenu."
        )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "pairs_found": len(pairs),
                "unmatched_downloads": len(unmatched_downloads),
                "download_formats": list({dl["format"] for dl in download_links}),
                "alternative_formats": list({alt["format"] for alt in alternative_links}),
                "needs_review_count": needs_review_count,
                "compliant_count": compliant_count,
                "required_manual_checks": [
                    "vérifier que chaque version alternative offre la même information que l'original",
                    "vérifier la pertinence des versions alternatives HTML",
                    "vérifier l'exhaustivité du contenu (toutes les informations sont présentes)",
                    "vérifier l'absence de perte d'information dans la version accessible",
                    "pour les PDF taggés : vérifier la structure de lecture et les textes alternatifs",
                    "pour les versions HTML : vérifier la conformité RGAA",
                ],
            },
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

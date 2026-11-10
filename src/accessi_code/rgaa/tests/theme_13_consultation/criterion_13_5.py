from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns to detect cryptic content
# ASCII art: sequences of special characters forming images (multi-line or complex)
# Includes common ASCII art characters: | \ / _ - = + * # @ % $ & , . ( ) [ ] { } < > ^ ~ `
ASCII_ART_PATTERN = re.compile(
    r"[|\\/\-_=+*#@%$&,\.\(\)\[\]\{\}\<\>\^~\`]{4,}",  # At least 4 consecutive special chars
)

# Emoticons (Western and Eastern)
EMOTICON_PATTERNS = [
    # Western emoticons (sideways) - common ones
    re.compile(r"[:;=8][-o\^]?[\)\(DPpOo\/\\|@3\[\]{}]"),
    re.compile(r"[\)\(DPpOo\/\\|@3\[\]{}][-o\^]?[:;=8]"),
    # Eastern emoticons (kaomoji) - more specific patterns
    re.compile(r"\([^)]{1,10}\)"),  # Simple kaomoji like (^_^)
    # Common specific emoticons
    re.compile(r"¯\\_\(ツ\)_/¯"),
    re.compile(r"\(ಠ_ಠ\)"),
    re.compile(r"\(╯°□°\)╯︵┻━┻"),
]

# Cryptic syntax patterns (code-like, technical abbreviations without explanation)
# More restrictive to avoid false positives
CRYPTIC_SYNTAX_PATTERNS = [
    re.compile(r"\b[A-Z]{3,}\b"),  # All caps acronyms (3+ chars)
    # Code-like patterns with brackets/braces (but not simple parentheses in text)
    re.compile(r"[{}<>\[\]]"),  # Curly braces, angle brackets, square brackets
    # Code-like patterns: word followed by semicolon, colon, brackets (but not just parentheses in prose)
    re.compile(r"(?:^|\s)[a-z]+[;:{}\[\]]"),  # Code-like patterns (exclude simple parentheses)
]

# Common acronyms/words that should NOT be flagged as cryptic
COMMON_ACRONYMS = {
    "THE",
    "AND",
    "FOR",
    "YOU",
    "ARE",
    "NOT",
    "BUT",
    "WITH",
    "THIS",
    "THAT",
    "FROM",
    "HAVE",
    "HAS",
    "HAD",
    "WILL",
    "WOULD",
    "COULD",
    "SHOULD",
    "HTML",
    "CSS",
    "JS",
    "PHP",
    "SQL",
    "API",
    "URL",
    "HTTP",
    "HTTPS",
    "WWW",
    "DOM",
    "AJAX",
    "JSON",
    "XML",
    "UTF",
    "ISO",
    "IEC",
    "W3C",
    "WCAG",
    "RGAA",
    "ARIA",
    "PDF",
    "DOC",
    "DOCX",
    "ODT",
    "EPUB",
    "DAISY",
    "PNG",
    "JPG",
    "JPEG",
    "GIF",
    "SVG",
    "WEBP",
    "MP3",
    "MP4",
    "AVI",
    "MOV",
    "ZIP",
    "RAR",
    "TAR",
    "GZ",
    "EXE",
    "DLL",
    "SYS",
    "INI",
    "CFG",
    "LOG",
    "TXT",
    "CSV",
    "TSV",
    "RSA",
    "AES",
    "SHA",
    "MD5",
    "SSL",
    "TLS",
    "SSH",
    "FTP",
    "SFTP",
    "SMTP",
    "POP3",
    "IMAP",
    "DNS",
    "DHCP",
    "IP",
    "TCP",
    "UDP",
    "VPN",
    "LAN",
    "WAN",
    "CPU",
    "GPU",
    "RAM",
    "ROM",
    "SSD",
    "HDD",
    "USB",
    "HDMI",
    "VGA",
    "DVI",
    "OS",
    "UI",
    "UX",
    "CI",
    "CD",
    "IDE",
    "SDK",
    "REST",
    "SOAP",
    "RPC",
    "ORM",
    "MVC",
    "MVP",
    "MVVM",
    "CRUD",
    "NoSQL",
    "DB",
    "DBMS",
    "AI",
    "ML",
    "DL",
    "NLP",
    "CV",
    "RL",
    "GAN",
    "CNN",
    "RNN",
    "LSTM",
    "GRU",
    "BERT",
    "GPT",
    "LLM",
    "RLHF",
    "RAG",
    "IoT",
    "IIoT",
    "OT",
    "IT",
    "DevOps",
    "CI/CD",
    "K8s",
    "Docker",
    "VM",
    "AWS",
    "GCP",
    "Azure",
    "VMware",
    "Linux",
    "Windows",
    "macOS",
    "Unix",
    "BSD",
    "GNU",
    "POSIX",
    "IEEE",
    "ISO",
    "ANSI",
    "ASCII",
    "Unicode",
    "UTF-8",
    "UTF-16",
    "UTF-32",
    "Base64",
    "Hex",
    "RGB",
    "RGBA",
    "CMYK",
    "HSL",
    "HSLA",
    "AVIF",
    "SVG",
    "Canvas",
    "WebGL",
    "WebAssembly",
    "WASM",
    "ES6",
    "ES2015",
    "ES2016",
    "ES2017",
    "ES2018",
    "ES2019",
    "ES2020",
    "ES2021",
    "ES2022",
    "ES2023",
    "TypeScript",
    "JavaScript",
    "ECMAScript",
    "Node.js",
    "npm",
    "yarn",
    "pnpm",
    "webpack",
    "vite",
    "rollup",
    "esbuild",
    "babel",
    "React",
    "Vue",
    "Angular",
    "Svelte",
    "Next.js",
    "Nuxt",
    "Remix",
    "Gatsby",
    "Express",
    "Koa",
    "Fastify",
    "NestJS",
    "Django",
    "Flask",
    "FastAPI",
    "Starlette",
    "Spring",
    "SpringBoot",
    "Quarkus",
    "Micronaut",
    "Vert.x",
    "Play",
    "Akka",
    "Hibernate",
    "JPA",
    "MyBatis",
    "JOOQ",
    "Liquibase",
    "Flyway",
    "JUnit",
    "Mockito",
    "TestNG",
    "Selenium",
    "Cypress",
    "Playwright",
    "Puppeteer",
    "Jest",
    "Vitest",
    "Mocha",
    "Chai",
    "Enzyme",
    "Testing Library",
    "RTL",
    "Storybook",
    "Chromatic",
    "Vercel",
    "Netlify",
    "Railway",
    "Render",
    "Heroku",
    "Kubernetes",
    "Helm",
    "Kustomize",
    "ArgoCD",
    "Flux",
    "Tekton",
    "Prometheus",
    "Grafana",
    "Loki",
    "Tempo",
    "Jaeger",
    "Zipkin",
    "OpenTelemetry",
    "ELK",
    "EFK",
    "Fluentd",
    "FluentBit",
    "Logstash",
    "Beats",
    "Filebeat",
    "Metricbeat",
    "Packetbeat",
    "Heartbeat",
    "Auditbeat",
    "Functionbeat",
    "Redis",
    "Memcached",
    "PostgreSQL",
    "MySQL",
    "MariaDB",
    "MongoDB",
    "Cassandra",
    "DynamoDB",
    "Firestore",
    "Bigtable",
    "Spanner",
    "CloudSQL",
    "RDS",
    "Aurora",
    "S3",
    "GCS",
    "Blob",
    "CDN",
    "CloudFront",
    "CloudFlare",
    "Akamai",
    "Fastly",
    "Varnish",
    "Nginx",
    "Apache",
    "Traefik",
    "Envoy",
    "HAProxy",
    "Keepalived",
    "LVS",
    "BIND",
    "Unbound",
    "PowerDNS",
    "CoreDNS",
    "Etcd",
    "Consul",
    "Vault",
    "Keycloak",
    "OAuth",
    "OIDC",
    "SAML",
    "LDAP",
    "ActiveDirectory",
    "Kerberos",
    "JWT",
    "JWE",
    "JWS",
    "JWK",
    "JWA",
    "Base64URL",
    "HS256",
    "RS256",
    "ES256",
    "PS256",
    "EdDSA",
    "ECDSA",
    "ECDH",
    "X25519",
    "X448",
    "AES-GCM",
    "ChaCha20",
    "Poly1305",
    "HKDF",
    "PBKDF2",
    "Argon2",
    "Scrypt",
    "Bcrypt",
    "SHA-256",
    "SHA-384",
    "SHA-512",
    "SHA3-256",
    "SHA3-384",
    "SHA3-512",
    "BLAKE2",
    "BLAKE3",
    "RIPEMD",
    "Whirlpool",
    "Tiger",
    "Skein",
    "Keccak",
}


DEFINITION_KEYWORDS = [
    "signifie",
    "désigne",
    "représente",
    "c'est",
    "est un",
    "est une",
    "défini",
    "veut dire",
    "meaning",
]


def _check_definition_keywords(text: str) -> bool:
    """Check if text contains definition keywords."""
    return any(kw in text.lower() for kw in DEFINITION_KEYWORDS)


DEFINITION_WORDS_PATTERN = (
    r"(?:c['e]est|il s'agit de|qui signifie|signifie|désigne"
    r"|représente|correspond à|est défini comme|défini comme"
    r"|veut dire|meaning)\s+[^.!?]+"
)


class CrypticMatch:
    """Represents a detected cryptic content match with position info."""

    def __init__(self, element, text, content_type, text_node, match_start=0, match_end=0, matched_text=""):
        self.element = element
        self.text = text  # Full text of the text node
        self.content_type = content_type
        self.text_node = text_node
        self.match_start = match_start  # Position within text_node
        self.match_end = match_end  # Position within text_node
        self.matched_text = matched_text  # The actual matched cryptic text


def _find_cryptic_content(soup: BeautifulSoup) -> list[CrypticMatch]:
    """
    Find all text nodes that may contain cryptic content (ASCII art, emoticons, cryptic syntax).
    Returns list of CrypticMatch objects with position info.
    """
    results = []

    # Get all text nodes
    for text_node in soup.find_all(string=True):
        text = str(text_node).strip()
        if not text or len(text) < 2:
            continue

        # Skip text inside script, style, noscript, template
        parent = text_node.parent
        if parent and parent.name in ["script", "style", "noscript", "template"]:
            continue

        # Check for ASCII art - need multi-line or complex pattern
        ascii_match = ASCII_ART_PATTERN.search(text)
        if ascii_match:
            # Verify it looks like actual ASCII art (multiple lines or complex pattern)
            lines = text.split("\n")
            if len(lines) > 1 or len(text) > 30:
                results.append(
                    CrypticMatch(
                        element=parent,
                        text=text,
                        content_type="ascii_art",
                        text_node=text_node,
                        match_start=ascii_match.start(),
                        match_end=ascii_match.end(),
                        matched_text=ascii_match.group(),
                    )
                )
                continue

        # Also check for multi-line content in <pre> tags that looks like ASCII art
        # even without 4 consecutive special chars (common for simple diagrams)
        if parent and parent.name == "pre":
            lines = text.split("\n")
            if len(lines) > 1:
                # Check if it contains typical ASCII art characters across multiple lines
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                char_count = sum(1 for c in text if c in ascii_chars)
                # If significant portion is ASCII art chars, consider it ASCII art
                if char_count > 10 or (char_count > 5 and len(lines) > 2):
                    # Find first occurrence of ASCII art char as match position
                    first_match = None
                    for i, c in enumerate(text):
                        if c in ascii_chars:
                            first_match = i
                            break
                    if first_match is not None:
                        results.append(
                            CrypticMatch(
                                element=parent,
                                text=text,
                                content_type="ascii_art",
                                text_node=text_node,
                                match_start=first_match,
                                match_end=first_match + 1,
                                matched_text=text[first_match : first_match + 20],
                            )
                        )
                        continue

        # Check for emoticons
        for pattern in EMOTICON_PATTERNS:
            match = pattern.search(text)
            if match:
                results.append(
                    CrypticMatch(
                        element=parent,
                        text=text,
                        content_type="emoticon",
                        text_node=text_node,
                        match_start=match.start(),
                        match_end=match.end(),
                        matched_text=match.group(),
                    )
                )
                break

        # Check for cryptic syntax (all caps acronyms, code patterns)
        for pattern in CRYPTIC_SYNTAX_PATTERNS:
            for match in pattern.finditer(text):
                matched = match.group()
                # Filter out common words that happen to be uppercase
                if len(matched) >= 3 and matched.upper() not in COMMON_ACRONYMS:
                    results.append(
                        CrypticMatch(
                            element=parent,
                            text=text,
                            content_type="cryptic_syntax",
                            text_node=text_node,
                            match_start=match.start(),
                            match_end=match.end(),
                            matched_text=matched,
                        )
                    )
                    break
            else:
                continue
            break

    return results


def _has_title_attribute(element) -> tuple[bool, str | None]:
    """
    Check if element or its ancestors have a title attribute with meaningful content.
    Returns (has_title, title_text).
    """
    current = element
    while current and current.name != "[document]":
        title = current.get("title", "")
        if isinstance(title, str) and title.strip():
            return True, title.strip()
        current = current.parent

    return False, None


def _has_adjacent_definition(
    soup: BeautifulSoup,
    match: CrypticMatch,
    window_chars: int = 300,
) -> tuple[bool, str | None]:
    """
    Check if there's a definition in the adjacent context (before or after the cryptic content).
    Uses the match position within the text node for accurate context detection.
    For ASCII art, only checks sibling elements (not within the same text node).
    Returns (has_definition, definition_text).
    """
    if not match.text_node or not match.text_node.parent:
        return False, None

    parent = match.text_node.parent
    full_text = str(match.text_node)

    # Use the match position within the text node
    match_start = match.match_start
    match_end = match.match_end

    # For ASCII art, don't check within the same text node (the whole text node IS the ASCII art)
    # Only check sibling elements for definitions
    if match.content_type == "ascii_art":
        # Check for explicit definition elements in siblings
        prev_sibling = parent.previous_sibling
        next_sibling = parent.next_sibling

        for sibling in [prev_sibling, next_sibling]:
            # Skip whitespace-only text nodes
            while sibling and isinstance(sibling, str) and not sibling.strip():
                sibling = sibling.previous_sibling if sibling == prev_sibling else sibling.next_sibling
            if sibling and sibling.name in ["abbr", "dfn", "acronym", "span", "p", "div", "li", "dt", "dd"]:
                sibling_text = sibling.get_text(strip=True)
                if len(sibling_text) > 5:
                    if _check_definition_keywords(sibling_text):
                        return True, sibling_text
        return False, None

    # For other types (emoticon, cryptic_syntax), check within the same text node
    # Check preceding text (before the cryptic content)
    preceding = full_text[max(0, match_start - window_chars) : match_start].strip()
    # Check following text (after the cryptic content)
    following = full_text[match_end : match_end + window_chars].strip()

    # Look for definition patterns in adjacent text
    # Pattern 1: explicit definition words (signifie, désigne, représente, etc.)
    definition_patterns = [
        re.compile(DEFINITION_WORDS_PATTERN, re.IGNORECASE),
        # Pattern 2: Parenthetical definitions (text in parentheses after/before the term)
        # But exclude parentheses that are part of ASCII art (contain mostly special chars)
        re.compile(r"\(\s*[^)]{3,}\s*\)"),
        # Pattern 3: Definitions with colon or dash
        re.compile(r"[:–—]\s*[^.!?]{5,}"),
        # Pattern 4: "X (Y)" pattern where Y defines X
        re.compile(r"\S+\s*\(\s*[^)]{3,}\s*\)"),
    ]

    for pattern in definition_patterns:
        if pattern.search(preceding):
            matched = pattern.search(preceding)
            # For parentheses patterns, verify it's not just ASCII art chars
            if "(" in matched.group(0) and ")" in matched.group(0):
                # Check if the content inside parentheses is mostly special chars (ASCII art)
                inner = matched.group(0)[matched.group(0).find("(") + 1 : matched.group(0).rfind(")")]
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                if len(inner) > 0:
                    ascii_ratio = sum(1 for c in inner if c in ascii_chars) / len(inner)
                    if ascii_ratio > 0.5:  # Mostly ASCII art chars, likely not a definition
                        continue
            return True, matched.group(0).strip()
        if pattern.search(following):
            matched = pattern.search(following)
            # For parentheses patterns, verify it's not just ASCII art chars
            if "(" in matched.group(0) and ")" in matched.group(0):
                inner = matched.group(0)[matched.group(0).find("(") + 1 : matched.group(0).rfind(")")]
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                if len(inner) > 0:
                    ascii_ratio = sum(1 for c in inner if c in ascii_chars) / len(inner)
                    if ascii_ratio > 0.5:
                        continue
            return True, matched.group(0).strip()

    # Check for explicit definition elements nearby
    # Look at previous and next siblings
    prev_sibling = parent.previous_sibling
    next_sibling = parent.next_sibling

    for sibling in [prev_sibling, next_sibling]:
        # Skip whitespace-only text nodes
        while sibling and isinstance(sibling, str) and not sibling.strip():
            sibling = sibling.previous_sibling if sibling == prev_sibling else sibling.next_sibling
        if sibling and sibling.name in ["abbr", "dfn", "acronym", "span", "p", "div", "li", "dt", "dd"]:
            sibling_text = sibling.get_text(strip=True)
            if len(sibling_text) > 5:
                if _check_definition_keywords(sibling_text):
                    return True, sibling_text

    return False, None


def _has_abbr_or_dfn_nearby(soup: BeautifulSoup, match: CrypticMatch) -> tuple[bool, str | None]:
    """
    Check if there's an <abbr>, <dfn>, or <acronym> element near the cryptic content
    that could provide a definition.
    """
    if not match.text_node or not match.text_node.parent:
        return False, None

    parent = match.text_node.parent

    # Check if parent is an abbr/dfn/acronym
    if parent.name in ["abbr", "dfn", "acronym"]:
        title = parent.get("title", "")
        if isinstance(title, str) and title.strip():
            return True, title.strip()
        text = parent.get_text(strip=True)
        if len(text) > 2:
            return True, text

    # Check ancestors
    for ancestor in parent.parents:
        if ancestor.name in ["abbr", "dfn", "acronym"]:
            title = ancestor.get("title", "")
            if isinstance(title, str) and title.strip():
                return True, title.strip()
            text = ancestor.get_text(strip=True)
            if len(text) > 2:
                return True, text

    # Check nearby elements (siblings, parent's siblings)
    def check_element(elem):
        if elem and elem.name in ["abbr", "dfn", "acronym"]:
            title = elem.get("title", "")
            if isinstance(title, str) and title.strip():
                return True, title.strip()
            text = elem.get_text(strip=True)
            if len(text) > 2:
                return True, text
        return False, None

    # Check previous/next siblings of parent (skip whitespace text nodes)
    for sibling in [parent.previous_sibling, parent.next_sibling]:
        # Skip whitespace-only text nodes
        while sibling and isinstance(sibling, str) and not sibling.strip():
            sibling = sibling.previous_sibling if sibling == parent.previous_sibling else sibling.next_sibling
        if sibling:
            found, def_text = check_element(sibling)
            if found:
                return True, def_text
            # Check children
            if hasattr(sibling, "find_all"):
                for child in sibling.find_all(["abbr", "dfn", "acronym"]):
                    found, def_text = check_element(child)
                    if found:
                        return True, def_text

    return False, None


class Test1351(RGAATest):
    """
    Test 13.5.1 : Dans chaque page web, chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique)
    vérifie-t-il une de ces conditions ?

    Un attribut title est disponible ;
    Une définition est donnée par le contexte adjacent.
    """

    test_id = "13.5.1"
    criterion_id = "13.5"

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
                summary="Le DOM n'est pas disponible ; le test 13.5.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Find all cryptic content
        cryptic_matches = _find_cryptic_content(soup)

        if not cryptic_matches:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun contenu cryptique (art ASCII, émoticône, syntaxe cryptique) détecté.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, match in enumerate(cryptic_matches):
            element = match.element
            text = match.text
            content_type = match.content_type
            matched_text = match.matched_text

            # Generate selector for the element
            selector = self._get_element_selector(soup, element, element.name if element else "text", i)

            # Check condition 1: title attribute available
            has_title, title_text = _has_title_attribute(element)

            # Check condition 2: definition in adjacent context
            has_adjacent_def, adjacent_def_text = _has_adjacent_definition(soup, match)
            has_abbr_def, abbr_def_text = _has_abbr_or_dfn_nearby(soup, match)

            has_definition = has_adjacent_def or has_abbr_def
            definition_text = adjacent_def_text or abbr_def_text

            # Determine compliance
            if has_title:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:100]}...' "
                            f"dispose d'un attribut title : '{title_text[:100]}...'."
                        ),
                        recommendation="Conforme au critère 13.5.1 (condition 1 : attribut title disponible).",
                        evidence={
                            "content_type": content_type,
                            "text_preview": text[:200],
                            "matched_text": matched_text[:200],
                            "condition_met": "title_attribute",
                            "title_text": title_text,
                        },
                    )
                )
            elif has_definition:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:100]}...' "
                            f"a une définition dans le contexte adjacent : '{definition_text[:100]}...'."
                        ),
                        recommendation=(
                            "Conforme au critère 13.5.1 (condition 2 : définition dans le contexte adjacent)."
                        ),
                        evidence={
                            "content_type": content_type,
                            "text_preview": text[:200],
                            "matched_text": matched_text[:200],
                            "condition_met": "adjacent_definition",
                            "definition_text": definition_text,
                            "definition_source": "adjacent" if has_adjacent_def else "abbr_dfn",
                        },
                    )
                )
            else:
                # No title, no adjacent definition - non-compliant
                non_compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:200]}...' "
                            "ne dispose ni d'un attribut title, ni d'une définition dans le contexte adjacent."
                        ),
                        recommendation=(
                            "Ajouter un attribut title explicatif sur l'élément portant le contenu cryptique "
                            "ou sur un élément parent (lien, abbr, span, etc.), "
                            "ou fournir une définition dans le texte adjacent "
                            '(ex: via <abbr title="...">, <dfn>, ou texte explicatif).'
                        ),
                        evidence={
                            "content_type": content_type,
                            "text_preview": text[:500],
                            "matched_text": matched_text[:500],
                            "condition_met": "none",
                            "has_title": has_title,
                            "has_adjacent_definition": has_adjacent_def,
                            "has_abbr_dfn": has_abbr_def,
                        },
                    )
                )

        tested_elements = len(cryptic_matches)

        # Determine overall status
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) cryptique(s) détecté(s). "
                f"{non_compliant_count} non conforme(s) (pas de title ni définition adjacente), "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) cryptique(s) détecté(s). "
                f"Tous sont conformes au critère 13.5.1."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "total_cryptic_content": tested_elements,
                "ascii_art_count": len([m for m in cryptic_matches if m.content_type == "ascii_art"]),
                "emoticon_count": len([m for m in cryptic_matches if m.content_type == "emoticon"]),
                "cryptic_syntax_count": len([m for m in cryptic_matches if m.content_type == "cryptic_syntax"]),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "vérifier que les attributs title sont pertinents et explicatifs",
                    "vérifier que les définitions adjacentes sont claires et accessibles",
                    "vérifier la présence de contenus cryptiques non détectés automatiquement",
                    "vérifier l'usage de <abbr>, <dfn>, <acronym> pour les abréviations et termes techniques",
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

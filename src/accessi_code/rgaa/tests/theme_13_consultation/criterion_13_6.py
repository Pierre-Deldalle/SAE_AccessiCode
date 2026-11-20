from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Reuse patterns from criterion_13_5 for detecting cryptic content
# ASCII art: sequences of special characters forming images (multi-line or complex)
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
CRYPTIC_SYNTAX_PATTERNS = [
    re.compile(r"\b[A-Z]{3,}\b"),  # All caps acronyms (3+ chars)
    re.compile(r"[{}<>\[\]]"),  # Curly braces, angle brackets, square brackets
    re.compile(r"(?:^|\s)[a-z]+[;:{}\[\]]"),  # Code-like patterns
]

# Common acronyms/words that should NOT be flagged as cryptic
COMMON_ACRONYMS = {
    "THE", "AND", "FOR", "YOU", "ARE", "NOT", "BUT", "WITH", "THIS", "THAT",
    "FROM", "HAVE", "HAS", "HAD", "WILL", "WOULD", "COULD", "SHOULD",
    "HTML", "CSS", "JS", "PHP", "SQL", "API", "URL", "HTTP", "HTTPS",
    "WWW", "DOM", "AJAX", "JSON", "XML", "UTF", "ISO", "IEC", "W3C",
    "WCAG", "RGAA", "ARIA", "PDF", "DOC", "DOCX", "ODT", "EPUB", "DAISY",
    "PNG", "JPG", "JPEG", "GIF", "SVG", "WEBP", "MP3", "MP4", "AVI",
    "MOV", "ZIP", "RAR", "TAR", "GZ", "EXE", "DLL", "SYS", "INI",
    "CFG", "LOG", "TXT", "CSV", "TSV", "RSA", "AES", "SHA", "MD5",
    "SSL", "TLS", "SSH", "FTP", "SFTP", "SMTP", "POP3", "IMAP", "DNS",
    "DHCP", "IP", "TCP", "UDP", "VPN", "LAN", "WAN", "CPU", "GPU",
    "RAM", "ROM", "SSD", "HDD", "USB", "HDMI", "VGA", "DVI", "OS",
    "UI", "UX", "CI", "CD", "IDE", "SDK", "REST", "SOAP", "RPC",
    "ORM", "MVC", "MVP", "MVVM", "CRUD", "NoSQL", "DB", "DBMS",
    "AI", "ML", "DL", "NLP", "CV", "RL", "GAN", "CNN", "RNN",
    "LSTM", "GRU", "BERT", "GPT", "LLM", "RLHF", "RAG", "IoT",
    "IIoT", "OT", "IT", "DevOps", "CI/CD", "K8s", "Docker", "VM",
    "AWS", "GCP", "Azure", "VMware", "Linux", "Windows", "macOS",
    "Unix", "BSD", "GNU", "POSIX", "IEEE", "ISO", "ANSI", "ASCII",
    "Unicode", "UTF-8", "UTF-16", "UTF-32", "Base64", "Hex",
    "RGB", "RGBA", "CMYK", "HSL", "HSLA", "AVIF", "SVG", "Canvas",
    "WebGL", "WebAssembly", "WASM", "ES6", "ES2015", "ES2016",
    "ES2017", "ES2018", "ES2019", "ES2020", "ES2021", "ES2022",
    "ES2023", "TypeScript", "JavaScript", "ECMAScript", "Node.js",
    "npm", "yarn", "pnpm", "webpack", "vite", "rollup", "esbuild",
    "babel", "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt",
    "Remix", "Gatsby", "Express", "Koa", "Fastify", "NestJS",
    "Django", "Flask", "FastAPI", "Starlette", "Spring", "SpringBoot",
    "Quarkus", "Micronaut", "Vert.x", "Play", "Akka", "Hibernate",
    "JPA", "MyBatis", "JOOQ", "Liquibase", "Flyway", "JUnit",
    "Mockito", "TestNG", "Selenium", "Cypress", "Playwright",
    "Puppeteer", "Jest", "Vitest", "Mocha", "Chai", "Enzyme",
    "Testing Library", "RTL", "Storybook", "Chromatic", "Vercel",
    "Netlify", "Railway", "Render", "Heroku", "Kubernetes", "Helm",
    "Kustomize", "ArgoCD", "Flux", "Tekton", "Prometheus", "Grafana",
    "Loki", "Tempo", "Jaeger", "Zipkin", "OpenTelemetry", "ELK",
    "EFK", "Fluentd", "FluentBit", "Logstash", "Beats", "Filebeat",
    "Metricbeat", "Packetbeat", "Heartbeat", "Auditbeat",
    "Functionbeat", "Redis", "Memcached", "PostgreSQL", "MySQL",
    "MariaDB", "MongoDB", "Cassandra", "DynamoDB", "Firestore",
    "Bigtable", "Spanner", "CloudSQL", "RDS", "Aurora", "S3", "GCS",
    "Blob", "CDN", "CloudFront", "CloudFlare", "Akamai", "Fastly",
    "Varnish", "Nginx", "Apache", "Traefik", "Envoy", "HAProxy",
    "Keepalived", "LVS", "BIND", "Unbound", "PowerDNS", "CoreDNS",
    "Etcd", "Consul", "Vault", "Keycloak", "OAuth", "OIDC", "SAML",
    "LDAP", "ActiveDirectory", "Kerberos", "JWT", "JWE", "JWS",
    "JWK", "JWA", "Base64URL", "HS256", "RS256", "ES256", "PS256",
    "EdDSA", "ECDSA", "ECDH", "X25519", "X448", "AES-GCM",
    "ChaCha20", "Poly1305", "HKDF", "PBKDF2", "Argon2", "Scrypt",
    "Bcrypt", "SHA-256", "SHA-384", "SHA-512", "SHA3-256",
    "SHA3-384", "SHA3-512", "BLAKE2", "BLAKE3", "RIPEMD",
    "Whirlpool", "Tiger", "Skein", "Keccak",
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

DEFINITION_WORDS_PATTERN = (
    r"(?:c['e]est|il s'agit de|qui signifie|signifie|désigne"
    r"|représente|correspond à|est défini comme|défini comme"
    r"|veut dire|meaning)\s+[^.!?]+"
)

# Generic/non-informative alternative texts that indicate a FAIL
GENERIC_ALTERNATIVE_TEXTS = {
    "image",
    "img",
    "photo",
    "picture",
    "icône",
    "icon",
    "symbole",
    "symbol",
    "émoticône",
    "emoticon",
    "emoji",
    "smiley",
    "art ascii",
    "ascii art",
    "ascii",
    "drawing",
    "dessin",
    "figure",
    "graphic",
    "graphique",
    "schéma",
    "schema",
    "diagramme",
    "diagram",
    "illustration",
    "représentation",
    "representation",
    "contenu",
    "content",
    "élément",
    "element",
    "objet",
    "object",
    "forme",
    "shape",
    "logo",
    "pictogramme",
    "pictogram",
    "caractère",
    "character",
    "signe",
    "sign",
    "marque",
    "mark",
    "acronyme",
    "acronym",
    "abréviation",
    "abbreviation",
    "sigle",
    "code",
    "texte",
    "text",
    "inconnu",
    "unknown",
    "non défini",
    "undefined",
    "n/a",
    "na",
    "tbd",
    "à définir",
    "placeholder",
}


class CrypticMatch:
    """Represents a detected cryptic content match with position info."""

    def __init__(
        self,
        element,
        text,
        content_type,
        text_node,
        match_start=0,
        match_end=0,
        matched_text="",
        title_text=None,
        adjacent_definition=None,
        has_abbr_dfn=False,
    ):
        self.element = element
        self.text = text  # Full text of the text node
        self.content_type = content_type
        self.text_node = text_node
        self.match_start = match_start  # Position within text_node
        self.match_end = match_end  # Position within text_node
        self.matched_text = matched_text  # The actual matched cryptic text
        self.title_text = title_text
        self.adjacent_definition = adjacent_definition
        self.has_abbr_dfn = has_abbr_dfn


def _check_definition_keywords(text: str) -> bool:
    """Check if text contains definition keywords."""
    return any(kw in text.lower() for kw in DEFINITION_KEYWORDS)


def _is_generic_alternative(text: str) -> bool:
    """Check if alternative text is generic/non-informative."""
    if not text:
        return True
    text_clean = _clean_alternative_text(text)
    text_lower = text_clean.lower()
    return text_lower in GENERIC_ALTERNATIVE_TEXTS


def _clean_alternative_text(text: str) -> str:
    """Clean alternative text by stripping surrounding punctuation and whitespace."""
    if not text:
        return ""
    # Strip whitespace
    cleaned = text.strip()
    # Strip surrounding punctuation: parentheses, brackets, quotes
    cleaned = cleaned.strip("()[]{}<>\"'")
    # Strip again in case there was whitespace inside punctuation
    return cleaned.strip()


def _has_meaningful_definition(text: str) -> bool:
    """Check if the alternative text provides a meaningful definition/explanation."""
    if not text or not text.strip():
        return False

    # Clean the text first
    text_clean = _clean_alternative_text(text)
    text_lower = text_clean.lower()

    # Too short to be meaningful
    if len(text_lower) < 3:
        return False

    # Generic alternative
    if text_lower in GENERIC_ALTERNATIVE_TEXTS:
        return False

    # Contains definition keywords
    if _check_definition_keywords(text_clean):
        return True

    # For title attributes: if it's descriptive (more than just a label)
    # Check for common descriptive patterns
    descriptive_patterns = [
        r"^(un|une|le|la|des|ce|cet|cette)\s+\w+",  # "un chat", "une image", etc.
        r"\w+\s+(qui|que)\s+\w+",  # "chat qui dort", etc.
        r"représentant\s+",  # "représentant un chat"
        r"représente\s+",  # "représente un chat"
        r"montrant\s+",  # "montrant un chat"
        r"illustrant\s+",  # "illustrant un chat"
        r"dessin\s+de\s+",  # "dessin de chat"
        r"photo\s+de\s+",  # "photo de chat"
        r"image\s+de\s+",  # "image de chat"
        r"icône\s+de\s+",  # "icône de chat"
        r"symbole\s+de\s+",  # "symbole de"
        r"signifie\s+",  # "signifie"
        r"veut\s+dire\s+",  # "veut dire"
        r"est\s+un\s+",  # "est un chat"
        r"est\s+une\s+",  # "est une image"
    ]

    for pattern in descriptive_patterns:
        if re.search(pattern, text_lower):
            return True

    # If it's a reasonably long descriptive text (not just a label)
    if len(text_lower) > 10 and not text_lower.startswith(("image", "icône", "symbole", "figure", "photo", "dessin")):
        return True

    return False


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
    Returns (has_definition, definition_text).
    """
    if not match.text_node or not match.text_node.parent:
        return False, None

    parent = match.text_node.parent
    full_text = str(match.text_node)

    # Use the match position within the text node
    match_start = match.match_start
    match_end = match.match_end

    # For ASCII art, don't check within the same text node
    if match.content_type == "ascii_art":
        prev_sibling = parent.previous_sibling
        next_sibling = parent.next_sibling

        for sibling in [prev_sibling, next_sibling]:
            while sibling and isinstance(sibling, str) and not sibling.strip():
                sibling = sibling.previous_sibling if sibling == prev_sibling else sibling.next_sibling
            if sibling and sibling.name in ["abbr", "dfn", "acronym", "span", "p", "div", "li", "dt", "dd"]:
                sibling_text = sibling.get_text(strip=True)
                if len(sibling_text) > 5:
                    if _check_definition_keywords(sibling_text):
                        return True, sibling_text
        return False, None

    # For other types, check within the same text node
    preceding = full_text[max(0, match_start - window_chars) : match_start].strip()
    following = full_text[match_end : match_end + window_chars].strip()

    definition_patterns = [
        re.compile(DEFINITION_WORDS_PATTERN, re.IGNORECASE),
        re.compile(r"\(\s*[^)]{3,}\s*\)"),
        re.compile(r"[:–—]\s*[^.!?]{5,}"),
        re.compile(r"\S+\s*\(\s*[^)]{3,}\s*\)"),
    ]

    for pattern in definition_patterns:
        if pattern.search(preceding):
            matched = pattern.search(preceding)
            if "(" in matched.group(0) and ")" in matched.group(0):
                inner = matched.group(0)[matched.group(0).find("(") + 1 : matched.group(0).rfind(")")]
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                if len(inner) > 0:
                    ascii_ratio = sum(1 for c in inner if c in ascii_chars) / len(inner)
                    if ascii_ratio > 0.5:
                        continue
            return True, matched.group(0).strip()
        if pattern.search(following):
            matched = pattern.search(following)
            if "(" in matched.group(0) and ")" in matched.group(0):
                inner = matched.group(0)[matched.group(0).find("(") + 1 : matched.group(0).rfind(")")]
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                if len(inner) > 0:
                    ascii_ratio = sum(1 for c in inner if c in ascii_chars) / len(inner)
                    if ascii_ratio > 0.5:
                        continue
            return True, matched.group(0).strip()

    # Check for explicit definition elements nearby
    prev_sibling = parent.previous_sibling
    next_sibling = parent.next_sibling

    for sibling in [prev_sibling, next_sibling]:
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

    # Check nearby elements
    def check_element(elem):
        if elem and elem.name in ["abbr", "dfn", "acronym"]:
            title = elem.get("title", "")
            if isinstance(title, str) and title.strip():
                return True, title.strip()
            text = elem.get_text(strip=True)
            if len(text) > 2:
                return True, text
        return False, None

    for sibling in [parent.previous_sibling, parent.next_sibling]:
        while sibling and isinstance(sibling, str) and not sibling.strip():
            sibling = sibling.previous_sibling if sibling == parent.previous_sibling else sibling.next_sibling
        if sibling:
            found, def_text = check_element(sibling)
            if found:
                return True, def_text
            if hasattr(sibling, "find_all"):
                for child in sibling.find_all(["abbr", "dfn", "acronym"]):
                    found, def_text = check_element(child)
                    if found:
                        return True, def_text

    return False, None


def _find_cryptic_content_with_alternatives(soup: BeautifulSoup) -> list[CrypticMatch]:
    """
    Find all text nodes that may contain cryptic content AND have an alternative
    (title attribute or adjacent definition).
    """
    results = []

    for text_node in soup.find_all(string=True):
        text = str(text_node).strip()
        if not text or len(text) < 2:
            continue

        # Skip text inside script, style, noscript, template
        parent = text_node.parent
        if parent and parent.name in ["script", "style", "noscript", "template"]:
            continue

        content_type = None
        matched_text = ""
        match_start = 0
        match_end = 0

        # Check for ASCII art
        ascii_match = ASCII_ART_PATTERN.search(text)
        if ascii_match:
            lines = text.split("\n")
            if len(lines) > 1 or len(text) > 30:
                content_type = "ascii_art"
                matched_text = ascii_match.group()
                match_start = ascii_match.start()
                match_end = ascii_match.end()
            else:
                continue
        elif parent and parent.name == "pre":
            lines = text.split("\n")
            if len(lines) > 1:
                ascii_chars = set(r"|\\/\-_=+*#@%$&,.()[]{}<>^~`")
                char_count = sum(1 for c in text if c in ascii_chars)
                if char_count > 10 or (char_count > 5 and len(lines) > 2):
                    first_match = None
                    for i, c in enumerate(text):
                        if c in ascii_chars:
                            first_match = i
                            break
                    if first_match is not None:
                        content_type = "ascii_art"
                        matched_text = text[first_match : first_match + 20]
                        match_start = first_match
                        match_end = first_match + 1

        # Check for emoticons
        if content_type is None:
            for pattern in EMOTICON_PATTERNS:
                match = pattern.search(text)
                if match:
                    content_type = "emoticon"
                    matched_text = match.group()
                    match_start = match.start()
                    match_end = match.end()
                    break

        # Check for cryptic syntax
        if content_type is None:
            for pattern in CRYPTIC_SYNTAX_PATTERNS:
                for match in pattern.finditer(text):
                    matched = match.group()
                    if len(matched) >= 3 and matched.upper() not in COMMON_ACRONYMS:
                        content_type = "cryptic_syntax"
                        matched_text = matched
                        match_start = match.start()
                        match_end = match.end()
                        break
                if content_type:
                    break

        if content_type is None:
            continue

        # Check for alternatives (title or adjacent definition)
        has_title, title_text = _has_title_attribute(parent)
        has_adjacent_def, adjacent_def_text = _has_adjacent_definition(soup, CrypticMatch(
            element=parent,
            text=text,
            content_type=content_type,
            text_node=text_node,
            match_start=match_start,
            match_end=match_end,
            matched_text=matched_text,
        ))
        has_abbr_def, abbr_def_text = _has_abbr_or_dfn_nearby(soup, CrypticMatch(
            element=parent,
            text=text,
            content_type=content_type,
            text_node=text_node,
            match_start=match_start,
            match_end=match_end,
            matched_text=matched_text,
        ))

        # Only include if there's at least one alternative
        if has_title or has_adjacent_def or has_abbr_def:
            alternative_text = title_text or adjacent_def_text or abbr_def_text
            results.append(
                CrypticMatch(
                    element=parent,
                    text=text,
                    content_type=content_type,
                    text_node=text_node,
                    match_start=match_start,
                    match_end=match_end,
                    matched_text=matched_text,
                    title_text=title_text,
                    adjacent_definition=adjacent_def_text or abbr_def_text,
                    has_abbr_dfn=has_abbr_def,
                )
            )

    return results


class Test1361(RGAATest):
    """
    Test 13.6.1 : Dans chaque page web, chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique)
    ayant une alternative vérifie-t-il une de ces conditions ?

    Le contenu de l'attribut title est pertinent ;
    La définition donnée par le contexte adjacent est pertinente.
    """

    test_id = "13.6.1"
    criterion_id = "13.6"

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
                summary="Le DOM n'est pas disponible ; le test 13.6.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Find all cryptic content that HAS an alternative (title or adjacent definition)
        cryptic_matches = _find_cryptic_content_with_alternatives(soup)

        if not cryptic_matches:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun contenu cryptique (art ASCII, émoticône, syntaxe cryptique) "
                    "avec alternative détecté."
                ),
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
            alternative_text = match.title_text or match.adjacent_definition

            # Generate selector for the element
            selector = self._get_element_selector(soup, element, element.name if element else "text", i)

            # Deterministic relevance check
            is_relevant = _has_meaningful_definition(alternative_text) if alternative_text else False
            is_generic = _is_generic_alternative(alternative_text) if alternative_text else True

            if is_relevant:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:100]}...' "
                            f"a une alternative pertinente : '{alternative_text[:100]}...'."
                        ),
                        recommendation=(
                            "Conforme au critère 13.6.1 : l'alternative est pertinente."
                        ),
                        evidence={
                            "content_type": content_type,
                            "cryptic_text": matched_text[:200],
                            "alternative_text": alternative_text[:200],
                            "condition_met": "relevant_alternative",
                        },
                    )
                )
            elif is_generic or not alternative_text or not alternative_text.strip():
                non_compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:100]}...' "
                            f"a une alternative NON pertinente (générique ou vide) : '{alternative_text[:100]}...'."
                        ),
                        recommendation=(
                            "L'alternative n'est pas pertinente (générique, trompeuse ou incomplète). "
                            "Fournir une alternative qui explique clairement le sens du contenu cryptique."
                        ),
                        evidence={
                            "content_type": content_type,
                            "cryptic_text": matched_text[:200],
                            "alternative_text": alternative_text[:200] if alternative_text else "",
                            "condition_met": "irrelevant_alternative",
                        },
                    )
                )
            else:
                # Alternative exists but can't be determined automatically - needs manual review
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Contenu cryptique ({content_type}) : '{matched_text[:100]}...' "
                            f"a une alternative ('{alternative_text[:100]}...') dont la pertinence ne peut être déterminée automatiquement."
                        ),
                        recommendation=(
                            "Vérifier manuellement la pertinence de l'alternative pour ce contenu cryptique. "
                            "L'alternative doit expliquer clairement ce que représente le contenu cryptique."
                        ),
                        evidence={
                            "content_type": content_type,
                            "cryptic_text": matched_text[:200],
                            "alternative_text": alternative_text[:200],
                            "needs_manual_check": True,
                            "reason": "cannot_determine_automatically",
                        },
                    )
                )

        tested_elements = len(cryptic_matches)

        # Determine overall status (priority: FAIL > ERROR > NEEDS_REVIEW > NOT_TESTED > PASS > NOT_APPLICABLE)
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) cryptique(s) avec alternative détecté(s). "
                f"{non_compliant_count} alternative(s) non pertinente(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} pertinente(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) cryptique(s) avec alternative détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle de la pertinence, "
                f"{compliant_count} pertinente(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) cryptique(s) avec alternative détecté(s). "
                f"Toutes les alternatives sont pertinentes (conformes au critère 13.6.1)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "total_cryptic_with_alternatives": tested_elements,
                "ascii_art_count": len([m for m in cryptic_matches if m.content_type == "ascii_art"]),
                "emoticon_count": len([m for m in cryptic_matches if m.content_type == "emoticon"]),
                "cryptic_syntax_count": len([m for m in cryptic_matches if m.content_type == "cryptic_syntax"]),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "vérifier que les attributs title sont pertinents et explicatifs",
                    "vérifier que les définitions adjacentes sont claires et permettent de comprendre le contenu cryptique",
                    "vérifier l'absence d'alternatives génériques (ex: 'image', 'symbole', 'émoticône')",
                    "vérifier que l'alternative permet de comprendre le sens sans voir le contenu cryptique",
                ],
            },
        )

    def _get_context_text(self, match: CrypticMatch, window_chars: int = 200) -> str:
        """Extract context text around the cryptic content."""
        if not match.text_node:
            return ""

        full_text = str(match.text_node)
        match_start = match.match_start
        match_end = match.match_end

        if match.content_type == "ascii_art":
            # For ASCII art, get context from siblings
            parent = match.text_node.parent
            if parent:
                context_parts = []
                prev_sibling = parent.previous_sibling
                next_sibling = parent.next_sibling

                for sibling in [prev_sibling, next_sibling]:
                    while sibling and isinstance(sibling, str) and not sibling.strip():
                        sibling = sibling.previous_sibling if sibling == prev_sibling else sibling.next_sibling
                    if sibling and hasattr(sibling, "get_text"):
                        context_parts.append(sibling.get_text(strip=True))

                return " ".join(context_parts)[:window_chars * 2]

        preceding = full_text[max(0, match_start - window_chars) : match_start].strip()
        following = full_text[match_end : match_end + window_chars].strip()

        return (preceding + " " + following).strip()

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
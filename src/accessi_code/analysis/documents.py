"""
Documents bureautiques en téléchargement et versions accessibles proposées (RGAA 13.3, 13.4).

Un lien désigne un document bureautique lorsque sa cible a une extension
bureautique (PDF, Word, Excel, PowerPoint, OpenDocument, RTF, EPUB). Une version
accessible est un autre lien placé dans le même bloc (paragraphe, item de liste,
cellule…) ou désignant le même fichier sous un format web, ou dont l'intitulé
l'annonce explicitement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.links import accessible_name, link_href, link_identifier, normalize

OFFICE_FORMATS: dict[str, str] = {
    ".pdf": "PDF",
    ".doc": "Word",
    ".docx": "Word",
    ".odt": "OpenDocument texte",
    ".rtf": "RTF",
    ".xls": "Excel",
    ".xlsx": "Excel",
    ".ods": "OpenDocument tableur",
    ".ppt": "PowerPoint",
    ".pptx": "PowerPoint",
    ".odp": "OpenDocument présentation",
    ".epub": "EPUB",
}
WEB_EXTENSIONS = frozenset({"", ".html", ".htm", ".php", ".asp", ".aspx", ".txt"})

_BLOCKS = ("li", "p", "td", "th", "dd", "dt", "figure", "tr")
_ACCESSIBLE_WORDING = re.compile(
    r"\baccessible\b|version\s+(?:html|texte|web|en\s+ligne|adaptée|balisée)|format\s+(?:html|texte|accessible)"
    r"|\b(?:lire|consulter)\s+en\s+ligne\b|\bhtml\b|\bdaisy\b",
    re.IGNORECASE,
)


@dataclass
class DocumentLink:
    """Lien vers un document bureautique et versions accessibles trouvées."""

    link: Tag
    index: int
    href: str
    extension: str
    name: str
    alternatives: list[Tag] = field(default_factory=list)

    @property
    def format(self) -> str:
        return OFFICE_FORMATS[self.extension]

    @property
    def identifier(self) -> str:
        return link_identifier(self.link, self.index)


def _extension(href: str) -> str:
    return PurePosixPath(unquote(urlparse(href).path)).suffix.lower()


def _stem(href: str) -> str:
    return PurePosixPath(unquote(urlparse(href).path)).stem.lower()


def _block(link: Tag) -> Tag | None:
    parent = link.find_parent(_BLOCKS)
    return parent if isinstance(parent, Tag) else (link.parent if isinstance(link.parent, Tag) else None)


def _is_alternative(document: DocumentLink, candidate: Tag, soup: BeautifulSoup, same_block: bool) -> bool:
    href = link_href(candidate)
    if not href or href == document.href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return False
    name, _ = accessible_name(candidate, soup)
    extension = _extension(href)
    if _ACCESSIBLE_WORDING.search(name):
        return True
    if extension in WEB_EXTENSIONS and _stem(href) == _stem(document.href):
        return True
    return same_block and extension in WEB_EXTENSIONS and bool(re.search(r"\bversion\b", name, re.IGNORECASE))


def office_document_links(soup: BeautifulSoup) -> list[DocumentLink]:
    """Liens vers des documents bureautiques, avec leurs versions accessibles éventuelles."""
    links = [link for link in soup.find_all(["a", "area"]) if link_href(link)]
    documents: list[DocumentLink] = []
    for index, link in enumerate(links):
        href = link_href(link) or ""
        extension = _extension(href)
        if extension not in OFFICE_FORMATS:
            continue
        name, _ = accessible_name(link, soup)
        documents.append(DocumentLink(link, index, href, extension, normalize(name)))

    for document in documents:
        if is_accessible_version_link(document):
            continue  # le lien désigne lui-même la version accessible
        block = _block(document.link)
        neighbours = [a for a in block.find_all(["a", "area"]) if a is not document.link] if block else []
        for candidate in neighbours:
            if _is_alternative(document, candidate, soup, same_block=True):
                document.alternatives.append(candidate)
        if not document.alternatives:
            for candidate in links:
                if candidate is not document.link and candidate not in neighbours:
                    href = link_href(candidate) or ""
                    if _extension(href) in WEB_EXTENSIONS and _stem(href) == _stem(document.href):
                        document.alternatives.append(candidate)
    return documents


def is_accessible_version_link(document: DocumentLink) -> bool:
    """Le lien annonce lui-même une version accessible (« Rapport – version accessible (PDF) »)."""
    return bool(re.search(r"\baccessible\b", document.name, re.IGNORECASE))

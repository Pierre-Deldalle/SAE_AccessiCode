"""
RGAA 4.1.2 — critère 13.4 : pour chaque document bureautique ayant une version
accessible, cette version offre-t-elle la même information ?

Concerne les documents pour lesquels ``analysis/documents.py`` trouve une
version accessible. Comparer les deux contenus demande d'ouvrir le document
bureautique, ce qu'AccessiCode ne fait pas : chaque paire est à vérifier
(NEEDS_REVIEW). Aucun document avec version accessible → NOT_APPLICABLE.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.documents import office_document_links
from accessi_code.analysis.links import accessible_name, link_href
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome

EMPTY_SUMMARY = "Aucun document bureautique accompagné d'une version accessible."


class Test1341(RGAATest):
    test_id = "13.4.1"
    criterion_id = "13.4"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        outcomes = []
        for document in office_document_links(soup):
            for alternative in document.alternatives:
                name, _ = accessible_name(alternative, soup)
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        document.identifier,
                        f"Vérifier que la version accessible « {name} » donne la même information que le "
                        f"document {document.format} « {document.name or document.href} ».",
                        "Comparer les deux versions : textes, tableaux, images informatives et liens doivent "
                        "être présents dans la version accessible.",
                        href=document.href,
                        alternative_href=link_href(alternative),
                    )
                )
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="version(s) accessible(s)")

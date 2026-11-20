"""
RGAA 4.1.2 — critère 13.3 : dans chaque page web, chaque document bureautique
en téléchargement possède-t-il, si nécessaire, une version accessible ?

Documents et versions accessibles repérés par ``analysis/documents.py`` :
- une version accessible est proposée à côté du document, ou le lien annonce
  lui-même une version accessible → PASS ;
- sinon, le document doit être accessible par lui-même (PDF balisé, styles de
  titres…) : cela se vérifie en ouvrant le fichier → NEEDS_REVIEW.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.documents import is_accessible_version_link, office_document_links
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome

EMPTY_SUMMARY = "Aucun document bureautique en téléchargement."


class Test1331(RGAATest):
    test_id = "13.3.1"
    criterion_id = "13.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        outcomes = []
        for document in office_document_links(soup):
            if document.alternatives or is_accessible_version_link(document):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    document.identifier,
                    f"Le document {document.format} « {document.name or document.href} » n'a pas de version "
                    "accessible proposée : vérifier que le document est accessible par lui-même.",
                    f"Rendre le document {document.format} accessible (structure balisée, titres, alternatives "
                    "des images, ordre de lecture) ou proposer à côté une version accessible (page HTML…).",
                    href=document.href,
                    format=document.format,
                )
            )
        return build_result(self, outcomes, empty_summary=EMPTY_SUMMARY, noun="document(s) bureautique(s)")

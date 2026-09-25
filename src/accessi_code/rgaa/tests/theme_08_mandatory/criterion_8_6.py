from __future__ import annotations

from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import TitleAnalysis
from accessi_code.analysis.page import (
    extract_page_information,
    has_page_title_element,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test861(RGAATest):
    test_id = "8.6.1"
    criterion_id = "8.6"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 8.6.1 nécessite un DOM.")

        if not has_page_title_element(context.dom):
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                ("La page ne possède pas de title ; sa présence est contrôlée par 8.5.1."),
            )

        page = extract_page_information(context.dom)

        if page.title is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                "La balise title est vide.",
                findings=[
                    Finding(
                        element="title",
                        message="Le titre de page est vide.",
                        recommendation=("Rédiger un titre permettant d'identifier la page."),
                    )
                ],
                tested_elements=1,
            )

        if not page.content:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                ("Le contenu est insuffisant pour évaluer la pertinence du titre."),
                tested_elements=1,
            )

        analyzer = (
            getattr(
                services,
                "page_analyzer",
                None,
            )
            if services is not None
            else None
        )

        if analyzer is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                "La pertinence du titre nécessite une analyse sémantique.",
                tested_elements=1,
            )

        try:
            analysis = await analyzer.analyze_title(
                page.title,
                page.main_heading or "",
                page.content,
            )

            if not isinstance(
                analysis,
                TitleAnalysis,
            ):
                raise TypeError("TitleAnalysis attendu.")

        except Exception as error:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.ERROR,
                "L'analyse IA du titre a échoué.",
                tested_elements=1,
                metadata={
                    "error": str(error),
                },
            )

        evidence = {
            "title": page.title,
            "heading": page.main_heading,
            "analysis": asdict(analysis),
        }

        if analysis.confidence == "low":
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                (analysis.explanation or ("L'analyse automatique du titre n'est pas suffisamment fiable.")),
                findings=[
                    Finding(
                        element="title",
                        message=("L'analyse IA possède un niveau de confiance insuffisant."),
                        recommendation=("Vérifier manuellement la pertinence du titre de la page."),
                        evidence=evidence,
                    )
                ],
                tested_elements=1,
                metadata=evidence,
            )

        if analysis.relevant is True:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Le titre permet d'identifier la page.",
                tested_elements=1,
                metadata=evidence,
            )

        if analysis.relevant is False:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                analysis.explanation,
                findings=[
                    Finding(
                        element="title",
                        message=analysis.explanation,
                        recommendation=("Rédiger un titre pertinent permettant d'identifier la page."),
                        evidence=evidence,
                    )
                ],
                tested_elements=1,
            )

        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.NEEDS_REVIEW,
            analysis.explanation,
            tested_elements=1,
            metadata=evidence,
        )

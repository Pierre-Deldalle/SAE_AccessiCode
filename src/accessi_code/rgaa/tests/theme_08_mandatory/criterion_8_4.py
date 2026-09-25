from __future__ import annotations

from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import LanguageAnalysis
from accessi_code.analysis.page import (
    extract_page_information,
    is_valid_language_code,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test841(RGAATest):
    test_id = "8.4.1"
    criterion_id = "8.4"

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
            raise ValueError("Le test 8.4.1 nécessite un DOM.")

        page = extract_page_information(context.dom)

        # L'absence de langue appartient au critère 8.3.
        if page.lang is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NOT_APPLICABLE,
                "Aucune langue par défaut n'est déclarée.",
            )

        if not is_valid_language_code(page.lang):
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                "Le code de langue déclaré n'est pas valide.",
                findings=[
                    Finding(
                        element="html",
                        message=(f"Code de langue invalide : {page.lang}"),
                        recommendation=("Utiliser un code de langue ISO valide."),
                    )
                ],
                tested_elements=1,
            )

        if not page.content:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                ("Le code de langue est valide mais le contenu est insuffisant pour vérifier sa pertinence."),
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
                ("Le code de langue est valide, mais sa pertinence nécessite une analyse sémantique."),
                tested_elements=1,
            )

        try:
            analysis = await analyzer.analyze_language(
                page.lang,
                page.content,
            )

            if not isinstance(
                analysis,
                LanguageAnalysis,
            ):
                raise TypeError("LanguageAnalysis attendu.")

        except Exception as error:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.ERROR,
                "L'analyse IA de la langue a échoué.",
                tested_elements=1,
                metadata={
                    "error": str(error),
                },
            )

        evidence = {
            "lang": page.lang,
            "analysis": asdict(analysis),
        }
        
        if analysis.confidence == "low":
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.NEEDS_REVIEW,
                (
                    analysis.explanation
                    or (
                        "L'analyse automatique de la langue "
                        "n'est pas suffisamment fiable."
                    )
                ),
                findings=[
                    Finding(
                        element="html",
                        message=(
                            "L'analyse IA possède un niveau "
                            "de confiance insuffisant."
                        ),
                        recommendation=(
                            "Vérifier manuellement que la langue "
                            "déclarée correspond au contenu."
                        ),
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
                "Le code de langue est valide et pertinent.",
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
                        element="html",
                        message=analysis.explanation,
                        recommendation=("Déclarer la langue principale réelle du document."),
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
            findings=[
                Finding(
                    element="html",
                    message=analysis.explanation,
                    evidence=evidence,
                )
            ],
            tested_elements=1,
        )

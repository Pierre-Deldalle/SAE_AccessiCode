from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import LanguageAnalysis
from accessi_code.models.result import Finding, TestResult, TestStatus


class Criterion841:
    """RGAA 8.4.1 : vérifie la pertinence de la langue déclarée."""

    test_id = "8.4.1"
    criterion_id = "8.4"

    def __init__(
        self,
        analyzer: Callable[[str, str], LanguageAnalysis] | None = None,
    ):
        """Configure un analyseur injectable pour isoler le test du LLM."""
        self.analyzer = analyzer

    def run(
        self,
        html: str,
        *,
        analyzer: Callable[[str, str], LanguageAnalysis] | None = None,
    ) -> TestResult:
        """Extrait lang et le contenu principal, puis produit le verdict RGAA."""
        soup = BeautifulSoup(html, "html.parser")
        html_element = soup.find("html")
        lang = html_element.get("lang", "").strip() if isinstance(html_element, Tag) else ""
        content = self._main_content(soup)

        # L'absence de lang est vérifiable sans IA et constitue un échec direct.
        if not lang:
            return self._failure(
                "L'attribut lang de la page est absent ou vide.",
                {"lang": lang, "content": content},
            )
        # Sans contenu exploitable, le modèle ne doit pas inventer la langue.
        if not content:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.INCONCLUSIVE,
                "Le contenu principal est insuffisant pour identifier sa langue.",
                tested_elements=1,
                metadata={"lang": lang},
            )

        # Le paramètre local permet de remplacer l'analyseur configuré pour un appel.
        effective_analyzer = analyzer or self.analyzer
        if effective_analyzer is None:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.INCONCLUSIVE,
                "La correspondance entre lang et le contenu nécessite une analyse IA ou humaine.",
                tested_elements=1,
                metadata={"lang": lang, "content": content},
            )

        try:
            analysis = effective_analyzer(lang, content)
            if not isinstance(analysis, LanguageAnalysis):
                raise TypeError("La réponse de l'analyseur n'est pas LanguageAnalysis.")
        except Exception as error:
            return self._inconclusive(
                "L'analyse IA de la langue déclarée a échoué.",
                {"lang": lang, "content": content, "error": str(error)},
            )

        # Les entrées et la réponse IA sont conservées pour rendre le verdict vérifiable.
        evidence = {"lang": lang, "content": content, "analysis": asdict(analysis)}
        if analysis.relevant is True:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "La langue déclarée correspond au contenu principal.",
                tested_elements=1,
                metadata={"lang": lang, "detected_language": analysis.detected_language},
            )
        if analysis.relevant is False:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                analysis.explanation or "La langue déclarée ne correspond pas au contenu principal.",
                findings=[Finding(
                    "html",
                    analysis.explanation or "La langue déclarée ne correspond pas au contenu principal.",
                    "Déclarer la langue réellement utilisée dans le contenu principal.",
                    evidence,
                )],
                tested_elements=1,
            )
        return self._inconclusive(
            analysis.explanation or "L'analyse IA ne permet pas d'identifier la langue principale.",
            evidence,
        )

    @staticmethod
    def _main_content(soup: BeautifulSoup) -> str:
        """Retourne le texte de main, ou body à défaut, hors scripts et styles."""
        container = soup.find("main") or soup.find("body") or soup
        for element in container.find_all(["script", "style"]):
            element.extract()
        return container.get_text(" ", strip=True)

    def _failure(self, message: str, evidence: dict[str, Any]) -> TestResult:
        """Construit un échec déterministe avec les éléments extraits."""
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            message,
            findings=[Finding("html", message, "Ajouter un attribut lang pertinent sur html.", evidence)],
            tested_elements=1,
        )

    def _inconclusive(self, message: str, evidence: dict[str, Any]) -> TestResult:
        """Construit un résultat incertain sans le transformer en échec."""
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.INCONCLUSIVE,
            message,
            findings=[Finding("html", message, "Vérifier la langue du contenu principal.", evidence)],
            tested_elements=1,
        )

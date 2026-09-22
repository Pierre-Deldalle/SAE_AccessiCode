from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import TitleAnalysis
from accessi_code.models.result import Finding, TestResult, TestStatus


class Criterion861:
    """RGAA 8.6.1 : vérifie la pertinence du titre de la page."""

    test_id = "8.6.1"
    criterion_id = "8.6"

    def __init__(
        self,
        analyzer: Callable[[str, str, str], TitleAnalysis] | None = None,
    ):
        """Configure un analyseur injectable pour isoler le test du LLM."""
        self.analyzer = analyzer

    def run(
        self,
        html: str,
        *,
        analyzer: Callable[[str, str, str], TitleAnalysis] | None = None,
    ) -> TestResult:
        """Extrait title, h1 et contenu, puis évalue la pertinence du titre."""
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        heading = soup.find("h1")
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        content = self._page_content(soup)

        # La présence d'un title non vide est un prérequis déterministe.
        if not title:
            return self._failure(
                "La page ne possède pas de titre pertinent dans la balise title.",
                {"title": title, "heading": heading_text, "content": content},
            )
        # Le titre ne peut pas être comparé à une page sans contenu exploitable.
        if not content:
            return self._inconclusive(
                "Le contenu de la page est insuffisant pour évaluer son titre.",
                {"title": title, "heading": heading_text, "content": content},
            )

        # Le paramètre local facilite les tests et les appels avec un autre modèle.
        effective_analyzer = analyzer or self.analyzer
        if effective_analyzer is None:
            return self._inconclusive(
                "La pertinence du titre nécessite une analyse IA ou humaine.",
                {"title": title, "heading": heading_text, "content": content},
            )

        try:
            analysis = effective_analyzer(title, heading_text, content)
            if not isinstance(analysis, TitleAnalysis):
                raise TypeError("La réponse de l'analyseur n'est pas TitleAnalysis.")
        except Exception as error:
            return self._inconclusive(
                "L'analyse IA de la pertinence du titre a échoué.",
                {"title": title, "heading": heading_text, "content": content, "error": str(error)},
            )

        # On conserve les trois éléments comparés avec la réponse du modèle.
        evidence = {
            "title": title,
            "heading": heading_text,
            "content": content,
            "analysis": asdict(analysis),
        }
        if analysis.relevant is True:
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.PASS,
                "Le titre identifie de manière pertinente la page.",
                tested_elements=1,
                metadata={"title": title, "heading": heading_text},
            )
        if analysis.relevant is False:
            message = analysis.explanation or "Le titre n'est pas pertinent pour la page."
            return TestResult(
                self.test_id,
                self.criterion_id,
                TestStatus.FAIL,
                message,
                findings=[Finding(
                    "title",
                    message,
                    "Rédiger un titre qui identifie la page et correspond à son contenu principal.",
                    evidence,
                )],
                tested_elements=1,
            )
        return self._inconclusive(
            analysis.explanation or "L'analyse IA ne permet pas d'évaluer la pertinence du titre.",
            evidence,
        )

    @staticmethod
    def _page_content(soup: BeautifulSoup) -> str:
        """Retourne le texte utile de la page sans title, scripts ni styles."""
        container = soup.find("main") or soup.body or soup
        for element in container.find_all(["script", "style", "title"]):
            element.extract()
        return container.get_text(" ", strip=True)

    def _failure(self, message: str, evidence: dict[str, Any]) -> TestResult:
        """Construit un échec déterministe concernant la balise title."""
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.FAIL,
            message,
            findings=[Finding("title", message, "Ajouter un title pertinent pour la page.", evidence)],
            tested_elements=1,
        )

    def _inconclusive(self, message: str, evidence: dict[str, Any]) -> TestResult:
        """Construit un résultat incertain sans conclure à une non-conformité."""
        return TestResult(
            self.test_id,
            self.criterion_id,
            TestStatus.INCONCLUSIVE,
            message,
            findings=[Finding("title", message, "Vérifier la pertinence du titre par rapport à la page.", evidence)],
            tested_elements=1,
        )

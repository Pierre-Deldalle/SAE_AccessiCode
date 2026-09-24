from __future__ import annotations

import asyncio
import re
from typing import Any

import aiohttp

from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.json_utils import parse_ai_json
from accessi_code.ai.prompts.page import (
    LANGUAGE_PROMPT,
    TITLE_PROMPT,
)
from accessi_code.ai.schemas import (
    AIConfidence,
    LanguageAnalysis,
    TitleAnalysis,
)


class OllamaPageAnalyzer:
    """
    Analyseur sémantique des informations générales d'une page.
    """

    def __init__(
        self,
        llm: OllamaLLM,
    ):
        self.llm = llm

    async def analyze_language(
        self,
        lang: str,
        content: str,
    ) -> LanguageAnalysis:
        """
        Compare une langue déclarée au contenu principal.
        """
        prompt = LANGUAGE_PROMPT.format(
            lang=lang,
            content=content,
        )

        data = await self._generate_json(
            prompt
        )

        relevant = self._get_relevant(
            data
        )

        return LanguageAnalysis(
            relevant=relevant,
            detected_language=str(
                data.get(
                    "detected_language",
                    "",
                )
            ),
            explanation=self._get_explanation(
                data.get("explanation"),
                fallback=(
                    "La correspondance entre la langue déclarée "
                    "et le contenu n'a pas pu être déterminée."
                ),
            ),
            uncertainties=self._get_strings(
                data.get("uncertainties")
            ),
            confidence=self._get_confidence(
                data.get("confidence")
            ),
        )

    async def analyze_title(
        self,
        title: str,
        heading: str,
        content: str,
    ) -> TitleAnalysis:
        """
        Analyse la pertinence d'un titre par rapport à la page.
        """
        prompt = TITLE_PROMPT.format(
            title=title,
            heading=heading,
            content=content,
        )

        data = await self._generate_json(
            prompt
        )

        relevant = self._get_relevant(
            data
        )

        return TitleAnalysis(
            relevant=relevant,
            explanation=self._get_explanation(
                data.get("explanation"),
                fallback=(
                    "La pertinence du titre n'a pas pu être déterminée."
                ),
            ),
            contradictions=self._get_strings(
                data.get("contradictions")
            ),
            uncertainties=self._get_strings(
                data.get("uncertainties")
            ),
            confidence=self._get_confidence(
                data.get("confidence")
            ),
        )

    async def _generate_json(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Demande une réponse JSON au LLM.

        Une deuxième tentative ajoute une consigne de format plus stricte.
        """
        strict_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT : retourne un unique objet JSON valide "
            "sans Markdown ni texte supplémentaire."
        )

        last_error: Exception | None = None

        for candidate in (
            prompt,
            strict_prompt,
        ):
            try:
                response = (
                    await self._generate_with_retry(
                        candidate
                    )
                )

                return parse_ai_json(
                    response
                )

            except ValueError as error:
                last_error = error

        raise ValueError(
            "Réponse JSON LLM inexploitable : "
            f"{last_error}"
        )

    async def _generate_with_retry(
        self,
        prompt: str,
    ) -> str:
        """
        Effectue une seconde tentative en cas d'erreur réseau transitoire.
        """
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                return await self.llm.generate(
                    prompt,
                    format="json",
                    max_tokens=600,
                    temperature=0,
                )

            except (
                aiohttp.ClientError,
                OSError,
                asyncio.TimeoutError,
            ) as error:
                last_error = error

                if attempt == 0:
                    await asyncio.sleep(0.5)

        raise RuntimeError(
            "La connexion avec Ollama a été interrompue : "
            f"{last_error}"
        ) from last_error

    @staticmethod
    def _get_relevant(
        data: dict[str, Any],
    ) -> bool | None:
        relevant = data.get("relevant")

        if relevant not in {
            True,
            False,
            None,
        }:
            raise ValueError(
                "Le champ relevant doit être true, false ou null."
            )

        return relevant

    @staticmethod
    def _get_strings(
        value: Any,
    ) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            str(item)
            for item in value
        ]

    @staticmethod
    def _get_explanation(
        value: Any,
        *,
        fallback: str,
    ) -> str:
        if not isinstance(value, str):
            return fallback

        explanation = " ".join(
            value.split()
        ).strip()

        if not explanation:
            return fallback

        # Écarte certaines générations répétitives clairement corrompues.
        if re.search(
            r"(.{3,40})\1{2,}",
            explanation,
            flags=re.IGNORECASE,
        ):
            return fallback

        return explanation[:500]

    @staticmethod
    def _get_confidence(
        value: Any,
    ) -> AIConfidence:
        if value in {
            "low",
            "medium",
            "high",
        }:
            return value

        return "low"
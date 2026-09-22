"""Analyseur LLM des informations sémantiques d'une page HTML."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import aiohttp
from json_repair import repair_json

from accessi_code.ai.prompts.page import LANGUAGE_PROMPT, TITLE_PROMPT
from accessi_code.ai.schemas import LanguageAnalysis, TitleAnalysis
from accessi_code.ollama_client.llm import OllamaLLM


class OllamaPageAnalyzer:
    """Interroge le LLM pour les comparaisons sémantiques de la page."""

    def __init__(self, llm: OllamaLLM):
        """Conserve le client LLM partagé par le service d'audit."""
        self.llm = llm

    async def analyze_language(self, lang: str, content: str) -> LanguageAnalysis:
        """Analyse la cohérence entre le code lang et le contenu principal."""
        data = await self._generate_json(LANGUAGE_PROMPT.format(lang=lang, content=content))
        relevant = self._relevant(data)
        return LanguageAnalysis(
            relevant=relevant,
            detected_language=str(data.get("detected_language", "")),
            explanation=self._explanation(
                data.get("explanation"),
                "La langue déclarée correspond au contenu principal."
                if relevant is True
                else "La langue déclarée ne correspond pas au contenu principal.",
            ),
            uncertainties=self._strings(data.get("uncertainties", [])),
            confidence=self._confidence(data.get("confidence")),
        )

    async def analyze_title(self, title: str, heading: str, content: str) -> TitleAnalysis:
        """Analyse la pertinence du title par rapport au h1 et au contenu."""
        data = await self._generate_json(
            TITLE_PROMPT.format(title=title, heading=heading, content=content)
        )
        relevant = self._relevant(data)
        return TitleAnalysis(
            relevant=relevant,
            explanation=self._explanation(
                data.get("explanation"),
                f"Le titre « {title} » est trop générique par rapport au contenu de la page."
                if relevant is False
                else "La pertinence du titre ne peut pas être déterminée.",
            ),
            contradictions=self._strings(data.get("contradictions", [])),
            uncertainties=self._strings(data.get("uncertainties", [])),
            confidence=self._confidence(data.get("confidence")),
        )

    async def _generate_json(self, prompt: str) -> dict[str, Any]:
        """Demande un JSON au LLM et réessaie avec une consigne plus stricte."""
        strict_prompt = (
            f"{prompt}\n\nRéponds avec un seul objet JSON complet sur une seule ligne. "
            "N'ajoute aucun commentaire ni markdown."
        )
        last_error: Exception | None = None
        for candidate in (prompt, strict_prompt):
            try:
                response = await self._generate_with_retry(candidate)
                return self._json_object(response)
            except (json.JSONDecodeError, ValueError) as error:
                # Une réponse mal formatée peut être récupérée au second essai.
                last_error = error
        raise ValueError(f"Réponse JSON LLM inexploitable : {last_error}")

    async def _generate_with_retry(self, prompt: str) -> str:
        """Relance une génération après une coupure réseau transitoire."""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await self.llm.generate(
                    prompt, format="json", max_tokens=600, temperature=0
                )
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == 0:
                    await asyncio.sleep(0.5)
        raise RuntimeError(
            "La connexion avec Ollama a été interrompue pendant l'analyse. "
            f"Vérifiez que le modèle est disponible puis réessayez : {last_error}"
        ) from last_error

    @staticmethod
    def _json_object(value: str) -> dict[str, Any]:
        """Transforme la réponse texte du modèle en objet JSON exploitable."""
        text = value.strip()
        if text.startswith("```"):
            # Certains modèles ajoutent encore une enveloppe Markdown.
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            # Ignore les phrases éventuelles placées avant ou après le JSON.
            text = text[start:end + 1]
        if not text:
            raise ValueError("La réponse IA est vide ou ne contient aucun objet JSON.")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            # Le modèle peut interrompre une chaîne JSON ; json_repair tente
            # alors de fermer les chaînes et les structures incomplètes.
            try:
                parsed = json.loads(repair_json(text))
            except (json.JSONDecodeError, TypeError, ValueError):
                raise error
        if not isinstance(parsed, dict):
            raise ValueError("La réponse IA n'est pas un objet JSON.")
        return parsed

    @staticmethod
    def _relevant(data: dict[str, Any]) -> bool | None:
        """Valide le verdict tri-state attendu par les critères RGAA."""
        relevant = data.get("relevant")
        if relevant not in {True, False, None}:
            raise ValueError("Le champ relevant doit être true, false ou null.")
        return relevant

    @staticmethod
    def _strings(value: Any) -> list[str]:
        """Normalise une liste produite par le modèle en liste de chaînes."""
        return [str(item) for item in value] if isinstance(value, list) else []

    @staticmethod
    def _explanation(value: Any, fallback: str) -> str:
        """Retourne une explication lisible et écarte les sorties répétitives."""
        if not isinstance(value, str):
            return fallback
        explanation = " ".join(value.split()).strip()
        # Les répétitions de caractères ou de mots signalent une génération
        # corrompue ; elles ne doivent pas polluer le résumé du rapport.
        if not explanation or re.search(r"(.{3,40})\1{2,}", explanation, re.IGNORECASE):
            return fallback
        if any(ord(character) < 32 and character not in "\n\t" for character in explanation):
            return fallback
        return explanation[:500]

    @staticmethod
    def _confidence(value: Any) -> str:
        """Retourne un niveau de confiance connu, ou low par défaut."""
        return value if value in {"low", "medium", "high"} else "low"

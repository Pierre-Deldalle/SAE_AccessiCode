"""Chaînage Qwen (vision) puis Gemma (comparaison de description)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import asdict
from typing import Any

import aiohttp
from json_repair import repair_json

from accessi_code.ai.prompts.images import (
    DETAILED_DESCRIPTION_PROMPT,
    IMAGE_INFORMATION_PROMPT,
)
from accessi_code.ai.schemas import DescriptionAnalysis, VisualObservation
from accessi_code.analysis.images import DetailedDescription, ImageInfo
from accessi_code.ollama_client.llm import OllamaLLM
from accessi_code.ollama_client.vlm import OllamaVLM


def _json_object(value: str) -> dict[str, Any]:
    """Extrait un objet JSON malgré le texte parasite ou les petites erreurs."""
    text = value.strip()
    # Certains modèles entourent encore leur réponse JSON de balises Markdown.
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # On isole l'objet pour ignorer une éventuelle phrase avant ou après le JSON.
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Répare uniquement les erreurs de syntaxe ; le contenu métier reste
        # celui produit par le modèle et sera validé par l'appelant.
        parsed = json.loads(repair_json(text))
    if not isinstance(parsed, dict):
        raise ValueError("La réponse IA n'est pas un objet JSON.")
    return parsed


class OllamaImageAnalyzer:
    """Analyse une image et compare chaque description à ses observations."""

    def __init__(self, vlm: OllamaVLM, llm: OllamaLLM):
        self.vlm = vlm
        self.llm = llm
        # Le résultat visuel est réutilisé pour toutes les descriptions d'une
        # même image afin d'éviter plusieurs appels coûteux à Qwen.
        self._visual_cache: dict[str, VisualObservation] = {}

    @staticmethod
    async def _image_input(image: ImageInfo) -> str | bytes:
        # Priorité aux données déjà extraites du HTML, puis au fichier local,
        # et enfin à une URL distante référencée par le document.
        if image.image_data:
            return image.image_data
        if image.image_path and Path(image.image_path).is_file():
            return image.image_path
        if urlparse(image.src).scheme in {"http", "https"}:
            async with aiohttp.ClientSession() as session:
                async with session.get(image.src, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Impossible de charger l'image ({response.status}).")
                    return await response.read()
        raise FileNotFoundError(f"Image HTML introuvable : {image.src}")

    async def analyze(self, image: ImageInfo, description: DetailedDescription) -> DescriptionAnalysis:
        image_input = await self._image_input(image)
        # Qwen décrit le contenu visuel ; Gemma juge ensuite chaque description
        # dans le contexte de la page et des observations de Qwen.
        visual = await self._get_visual_observation(image, image_input)
        prompt = DETAILED_DESCRIPTION_PROMPT.format(
            image_role=visual.summary,
            description=description.content,
            context=image.context_text,
            visual_observations=json.dumps(asdict(visual), ensure_ascii=False),
        )
        data = await self._generate_text_json(prompt)
        # Le champ peut être null : l'IA ne doit pas inventer un verdict quand
        # l'image, la description ou le contexte ne suffisent pas à conclure.
        relevant = data.get("relevant")
        if relevant not in {True, False, None}:
            raise ValueError("Le champ relevant doit être true, false ou null.")
        confidence = data.get("confidence", "low")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        return DescriptionAnalysis(
            relevant=relevant,
            explanation=str(data.get("explanation", "")),
            missing_information=[str(item) for item in data.get("missing_information", [])],
            contradictions=[str(item) for item in data.get("contradictions", [])],
            uncertainties=[str(item) for item in data.get("uncertainties", [])],
            confidence=confidence,
        )

    async def _get_visual_observation(
        self,
        image: ImageInfo,
        image_input: str | bytes,
    ) -> VisualObservation:
        """Analyse une image une seule fois, même si elle a plusieurs descriptions."""
        cache_key = image.image_path or image.src or str(id(image_input))
        cached = self._visual_cache.get(cache_key)
        if cached is not None:
            return cached

        # Une image peut avoir plusieurs descriptions (figcaption, ARIA, lien) :
        # l'analyse visuelle reste identique et ne doit être faite qu'une fois.
        visual_data = await self._generate_visual_json(image_input)
        visual = VisualObservation(
            summary=str(visual_data.get("summary", "")),
            important_information=[str(item) for item in visual_data.get("important_information", [])],
            uncertainties=[str(item) for item in visual_data.get("uncertainties", [])],
        )
        self._visual_cache[cache_key] = visual
        return visual

    async def _generate_visual_json(self, image_input: str | bytes) -> dict[str, Any]:
        strict_prompt = (
            f"{IMAGE_INFORMATION_PROMPT}\n\n"
            "Réponds avec un seul objet JSON complet sur une seule ligne. "
            "N'ajoute aucun commentaire ni markdown."
        )
        last_error: Exception | None = None
        # Une seconde consigne stricte récupère les réponses mal formatées sans
        # relancer l'analyse avec une autre image ou un autre contexte.
        for prompt in (IMAGE_INFORMATION_PROMPT, strict_prompt):
            try:
                response = await self.vlm.generate(
                    prompt, image=image_input, format="json", max_tokens=800, temperature=0
                )
                return _json_object(response)
            except (json.JSONDecodeError, ValueError) as error:
                last_error = error
        raise ValueError(f"Réponse JSON VLM inexploitable : {last_error}")

    async def _generate_text_json(self, prompt: str) -> dict[str, Any]:
        strict_prompt = (
            f"{prompt}\n\n"
            "Réponds avec un seul objet JSON complet sur une seule ligne. "
            "N'ajoute aucun commentaire ni markdown."
        )
        last_error: Exception | None = None
        # Même stratégie pour Gemma : on tente d'abord le prompt métier, puis
        # une consigne de format si la réponse JSON est inexploitable.
        for candidate in (prompt, strict_prompt):
            try:
                response = await self.llm.generate(
                    candidate, format="json", max_tokens=800, temperature=0
                )
                return _json_object(response)
            except (json.JSONDecodeError, ValueError) as error:
                last_error = error
        raise ValueError(f"Réponse JSON LLM inexploitable : {last_error}")
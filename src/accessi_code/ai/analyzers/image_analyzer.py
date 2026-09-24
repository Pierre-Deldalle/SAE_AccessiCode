from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp

from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.clients.vlm import OllamaVLM
from accessi_code.ai.json_utils import parse_ai_json
from accessi_code.ai.prompts.images import (
    DETAILED_DESCRIPTION_PROMPT,
    IMAGE_INFORMATION_PROMPT,
    IMAGE_INFORMATION_ROLE_PROMPT,
)
from accessi_code.ai.schemas import (
    DescriptionAnalysis,
    ImageRoleAnalysis,
    VisualObservation,
)
from accessi_code.analysis.images import (
    DetailedDescription,
    ImageInfo,
)


class OllamaImageAnalyzer:
    """
    Service d'analyse sémantique et visuelle des images.

    Le VLM observe le contenu de l'image.
    Le LLM interprète ensuite ces observations dans le contexte HTML.
    """

    def __init__(
        self,
        vlm: OllamaVLM,
        llm: OllamaLLM,
    ):
        self.vlm = vlm
        self.llm = llm

        # Une même image ne doit être analysée visuellement qu'une seule fois.
        self._visual_cache: dict[str, VisualObservation] = {}

    async def analyze_information_role(
        self,
        image: ImageInfo,
    ) -> ImageRoleAnalysis:
        """
        Détermine si une image semble porteuse d'information.

        Le VLM décrit d'abord l'image. Le LLM utilise ensuite ces observations
        et le contexte HTML pour déterminer son rôle informationnel.

        Aucun verdict RGAA n'est produit ici.
        """
        image_input = await self._get_image_input(
            image
        )

        visual = await self._get_visual_observation(
            image,
            image_input,
        )

        prompt = IMAGE_INFORMATION_ROLE_PROMPT.format(
            element_html=image.element_html,
            context=image.context_text,
            visual_observations=json.dumps(
                asdict(visual),
                ensure_ascii=False,
            ),
        )

        data = await self._generate_text_json(
            prompt
        )

        information_bearing = data.get(
            "information_bearing"
        )

        if information_bearing not in {
            True,
            False,
            None,
        }:
            raise ValueError(
                "Le champ information_bearing doit être "
                "true, false ou null."
            )

        confidence = data.get(
            "confidence",
            "low",
        )

        if confidence not in {
            "low",
            "medium",
            "high",
        }:
            confidence = "low"

        return ImageRoleAnalysis(
            information_bearing=information_bearing,
            explanation=str(
                data.get(
                    "explanation",
                    "",
                )
            ),
            uncertainties=self._get_strings(
                data.get(
                    "uncertainties"
                )
            ),
            confidence=confidence,
        )

    async def analyze(
        self,
        image: ImageInfo,
        description: DetailedDescription,
    ) -> DescriptionAnalysis:
        """
        Compare une description détaillée avec le contenu de l'image.
        """
        image_input = await self._get_image_input(
            image
        )

        visual = await self._get_visual_observation(
            image,
            image_input,
        )

        prompt = DETAILED_DESCRIPTION_PROMPT.format(
            image_role=visual.summary,
            description=description.content,
            context=image.context_text,
            visual_observations=json.dumps(
                asdict(visual),
                ensure_ascii=False,
            ),
        )

        data = await self._generate_text_json(
            prompt
        )

        relevant = data.get(
            "relevant"
        )

        if relevant not in {
            True,
            False,
            None,
        }:
            raise ValueError(
                "Le champ relevant doit être true, false ou null."
            )

        confidence = data.get(
            "confidence",
            "low",
        )

        if confidence not in {
            "low",
            "medium",
            "high",
        }:
            confidence = "low"

        return DescriptionAnalysis(
            relevant=relevant,
            explanation=str(
                data.get(
                    "explanation",
                    "",
                )
            ),
            missing_information=self._get_strings(
                data.get(
                    "missing_information"
                )
            ),
            contradictions=self._get_strings(
                data.get(
                    "contradictions"
                )
            ),
            uncertainties=self._get_strings(
                data.get(
                    "uncertainties"
                )
            ),
            confidence=confidence,
        )

    async def _get_image_input(
        self,
        image: ImageInfo,
    ) -> str | bytes:
        """
        Retourne l'image sous une forme exploitable par le VLM.

        Priorité :
        - données déjà extraites du HTML ;
        - fichier local ;
        - ressource HTTP/HTTPS.
        """
        if image.image_data:
            return image.image_data

        if image.image_path:
            path = Path(
                image.image_path
            )

            if path.is_file():
                return str(path)

        parsed_url = urlparse(
            image.src
        )

        if parsed_url.scheme in {
            "http",
            "https",
        }:
            timeout = aiohttp.ClientTimeout(
                total=30
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:
                async with session.get(
                    image.src
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(
                            "Impossible de charger l'image "
                            f"({response.status})."
                        )

                    return await response.read()

        raise FileNotFoundError(
            "Image HTML introuvable : "
            f"{image.src}"
        )

    async def _get_visual_observation(
        self,
        image: ImageInfo,
        image_input: str | bytes,
    ) -> VisualObservation:
        """
        Analyse visuellement une image une seule fois.
        """
        cache_key = (
            image.image_path
            or image.src
            or str(id(image_input))
        )

        cached = self._visual_cache.get(
            cache_key
        )

        if cached is not None:
            return cached

        data = await self._generate_visual_json(
            image_input
        )

        visual = VisualObservation(
            summary=str(
                data.get(
                    "summary",
                    "",
                )
            ),
            important_information=self._get_strings(
                data.get(
                    "important_information"
                )
            ),
            uncertainties=self._get_strings(
                data.get(
                    "uncertainties"
                )
            ),
        )

        self._visual_cache[
            cache_key
        ] = visual

        return visual

    async def _generate_visual_json(
        self,
        image_input: str | bytes,
    ) -> dict[str, Any]:
        """
        Demande au VLM une observation structurée de l'image.
        """
        strict_prompt = (
            f"{IMAGE_INFORMATION_PROMPT}\n\n"
            "IMPORTANT : retourne un unique objet JSON valide "
            "sans Markdown ni texte supplémentaire."
        )

        last_error: Exception | None = None

        for prompt in (
            IMAGE_INFORMATION_PROMPT,
            strict_prompt,
        ):
            try:
                response = await self._generate_vlm_with_retry(
                    prompt,
                    image_input,
                )

                return parse_ai_json(
                    response
                )

            except ValueError as error:
                last_error = error

        raise ValueError(
            "Réponse JSON VLM inexploitable : "
            f"{last_error}"
        )

    async def _generate_text_json(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Demande au LLM une analyse structurée.
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
                response = await self._generate_llm_with_retry(
                    candidate
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

    async def _generate_vlm_with_retry(
        self,
        prompt: str,
        image_input: str | bytes,
    ) -> str:
        """
        Réessaie une fois en cas d'erreur réseau transitoire.
        """
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                return await self.vlm.generate(
                    prompt,
                    image=image_input,
                    format="json",
                    max_tokens=800,
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
            "La connexion avec Ollama a été interrompue "
            "pendant l'analyse de l'image : "
            f"{last_error}"
        ) from last_error

    async def _generate_llm_with_retry(
        self,
        prompt: str,
    ) -> str:
        """
        Réessaie une fois en cas d'erreur réseau transitoire.
        """
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                return await self.llm.generate(
                    prompt,
                    format="json",
                    max_tokens=800,
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
            "La connexion avec Ollama a été interrompue "
            "pendant l'analyse textuelle : "
            f"{last_error}"
        ) from last_error

    @staticmethod
    def _get_strings(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            str(item)
            for item in value
        ]
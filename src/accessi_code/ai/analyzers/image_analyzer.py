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
    IMAGE_ELEMENT_ROLE_PROMPT,
    IMAGE_INFORMATION_PROMPT,
    IMAGE_INFORMATION_ROLE_PROMPT,
    IMAGE_MAP_AREA_ROLE_PROMPT,
)
from accessi_code.ai.schemas import (
    DescriptionAnalysis,
    ImageRoleAnalysis,
    VisualObservation,
)
from accessi_code.analysis.images import (
    DetailedDescription,
    ImageInfo,
    ImageMapAreaInfo,
)


class OllamaImageAnalyzer:
    def __init__(
        self,
        vlm: OllamaVLM,
        llm: OllamaLLM,
    ):
        self.vlm = vlm
        self.llm = llm

        self._visual_cache: dict[
            str,
            VisualObservation,
        ] = {}

    async def analyze_information_role(
        self,
        image: ImageInfo,
    ) -> ImageRoleAnalysis:
        image_input = await self._get_image_input(image)

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

        data = await self._generate_text_json(prompt)

        return self._build_role_analysis(data)

    async def analyze_element_information_role(
        self,
        element_html: str,
        context: str,
    ) -> ImageRoleAnalysis:
        """
        Analyse un role=img lorsque nous n'avons pas de fichier image
        directement exploitable.
        """
        prompt = IMAGE_ELEMENT_ROLE_PROMPT.format(
            element_html=element_html,
            context=context,
        )

        data = await self._generate_text_json(prompt)

        return self._build_role_analysis(data)

    async def analyze_area_information_role(
        self,
        area: ImageMapAreaInfo,
    ) -> ImageRoleAnalysis:
        visual_payload: dict[str, Any] = {
            "available": False,
        }

        if area.image is not None:
            try:
                image_input = await self._get_image_input(area.image)

                visual = await self._get_visual_observation(
                    area.image,
                    image_input,
                )

                visual_payload = {
                    "available": True,
                    **asdict(visual),
                }

            except Exception as error:
                visual_payload = {
                    "available": False,
                    "error": str(error),
                }

        prompt = IMAGE_MAP_AREA_ROLE_PROMPT.format(
            area_html=area.element_html,
            href=area.href or "",
            shape=area.shape or "",
            coords=area.coords or "",
            context=area.context_text,
            visual_observations=json.dumps(
                visual_payload,
                ensure_ascii=False,
            ),
        )

        data = await self._generate_text_json(prompt)

        return self._build_role_analysis(data)

    async def analyze(
        self,
        image: ImageInfo,
        description: DetailedDescription,
    ) -> DescriptionAnalysis:
        image_input = await self._get_image_input(image)

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

        data = await self._generate_text_json(prompt)

        is_detailed = data.get("is_detailed_description")

        if is_detailed not in {
            True,
            False,
            None,
        }:
            raise ValueError("is_detailed_description doit être true, false ou null.")

        relevant = data.get("relevant")

        if relevant not in {
            True,
            False,
            None,
        }:
            raise ValueError("relevant doit être true, false ou null.")

        if is_detailed is False:
            relevant = None

        return DescriptionAnalysis(
            relevant=relevant,
            explanation=str(
                data.get(
                    "explanation",
                    "",
                )
            ),
            is_detailed_description=is_detailed,
            missing_information=self._get_strings(data.get("missing_information")),
            contradictions=self._get_strings(data.get("contradictions")),
            uncertainties=self._get_strings(data.get("uncertainties")),
            confidence=self._get_confidence(data.get("confidence")),
        )

    async def _get_image_input(
        self,
        image: ImageInfo,
    ) -> str | bytes:
        if image.image_data:
            return image.image_data

        if image.image_path:
            path = Path(image.image_path)

            if path.is_file():
                return str(path)

        parsed_url = urlparse(image.src)

        if parsed_url.scheme in {
            "http",
            "https",
        }:
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(image.src) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Impossible de charger l'image ({response.status}).")

                    return await response.read()

        raise FileNotFoundError(f"Image HTML introuvable : {image.src}")

    async def _get_visual_observation(
        self,
        image: ImageInfo,
        image_input: str | bytes,
    ) -> VisualObservation:
        cache_key = image.image_path or image.src or str(id(image_input))

        cached = self._visual_cache.get(cache_key)

        if cached is not None:
            return cached

        data = await self._generate_visual_json(image_input)

        visual = VisualObservation(
            summary=str(
                data.get(
                    "summary",
                    "",
                )
            ),
            important_information=self._get_strings(data.get("important_information")),
            uncertainties=self._get_strings(data.get("uncertainties")),
        )

        self._visual_cache[cache_key] = visual

        return visual

    async def _generate_visual_json(
        self,
        image_input: str | bytes,
    ) -> dict[str, Any]:
        strict_prompt = f"{IMAGE_INFORMATION_PROMPT}\n\nIMPORTANT : retourne uniquement un objet JSON valide."

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

                return parse_ai_json(response)

            except ValueError as error:
                last_error = error

        raise ValueError(f"Réponse JSON VLM inexploitable : {last_error}")

    async def _generate_text_json(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        strict_prompt = f"{prompt}\n\nIMPORTANT : retourne uniquement un objet JSON valide."

        last_error: Exception | None = None

        for candidate in (
            prompt,
            strict_prompt,
        ):
            try:
                response = await self._generate_llm_with_retry(candidate)

                return parse_ai_json(response)

            except ValueError as error:
                last_error = error

        raise ValueError(f"Réponse JSON LLM inexploitable : {last_error}")

    async def _generate_vlm_with_retry(
        self,
        prompt: str,
        image_input: str | bytes,
    ) -> str:
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
            f"La connexion avec Ollama a été interrompue pendant l'analyse visuelle : {last_error}"
        ) from last_error

    async def _generate_llm_with_retry(
        self,
        prompt: str,
    ) -> str:
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
            f"La connexion avec Ollama a été interrompue pendant l'analyse textuelle : {last_error}"
        ) from last_error

    @staticmethod
    def _build_role_analysis(
        data: dict[str, Any],
    ) -> ImageRoleAnalysis:
        information_bearing = data.get("information_bearing")

        if information_bearing not in {
            True,
            False,
            None,
        }:
            raise ValueError("information_bearing doit être true, false ou null.")

        return ImageRoleAnalysis(
            information_bearing=information_bearing,
            explanation=str(
                data.get(
                    "explanation",
                    "",
                )
            ),
            uncertainties=OllamaImageAnalyzer._get_strings(data.get("uncertainties")),
            confidence=OllamaImageAnalyzer._get_confidence(data.get("confidence")),
        )

    @staticmethod
    def _get_strings(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [str(item) for item in value]

    @staticmethod
    def _get_confidence(
        value: Any,
    ) -> str:
        if value in {
            "low",
            "medium",
            "high",
        }:
            return value

        return "low"

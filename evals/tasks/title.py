from __future__ import annotations

from dataclasses import asdict
from typing import Any

from accessi_code.ai.analyzers.page_analyzer import (
    OllamaPageAnalyzer,
)
from evals.models.case import EvalCase
from evals.tasks.base import EvalTask


class TitleEvalTask(EvalTask):
    """
    Évalue la qualité de
    OllamaPageAnalyzer.analyze_title().
    """

    name = "title"
    decision_key = "relevant"

    def __init__(
        self,
        page_analyzer: OllamaPageAnalyzer,
    ):
        self.page_analyzer = page_analyzer

    async def execute(
        self,
        case: EvalCase,
        *,
        prompt_template: str | None = None,
    ) -> dict[str, Any]:
        title = self._get_string(
            case,
            "title",
        )

        heading = self._get_string(
            case,
            "heading",
        )

        content = self._get_string(
            case,
            "content",
        )

        analysis = await self.page_analyzer.analyze_title(
            title=title,
            heading=heading,
            content=content,
            prompt_template=prompt_template,
        )

        return asdict(analysis)

    @staticmethod
    def _get_string(
        case: EvalCase,
        key: str,
    ) -> str:
        if key not in case.input_data:
            raise ValueError(f"Le cas {case.id!r} ne possède pas le champ d'entrée {key!r}.")

        value = case.input_data[key]

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(f"Le champ {key!r} du cas {case.id!r} doit être une chaîne.")

        return value
    
    def validate_prompt_template(
        self,
        prompt_template: str,
    ) -> None:
        super().validate_prompt_template(
            prompt_template
        )

        try:
            prompt_template.format(
                title="TITLE",
                heading="HEADING",
                content="CONTENT",
            )

        except (
            KeyError,
            IndexError,
            ValueError,
        ) as error:
            raise ValueError(
                "Le prompt title est invalide. "
                "Il doit notamment supporter les variables "
                "{title}, {heading} et {content}, "
                "et les accolades JSON doivent être échappées "
                "avec {{ et }}."
            ) from error

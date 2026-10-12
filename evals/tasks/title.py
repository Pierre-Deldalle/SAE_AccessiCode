from __future__ import annotations

from dataclasses import asdict
from typing import Any

from accessi_code.ai.analyzers.page_analyzer import OllamaPageAnalyzer

from evals.models.case import EvalCase
from evals.tasks.base import EvalTask


class TitleEvalTask(EvalTask):
    """
    Évalue la qualité de OllamaPageAnalyzer.analyze_title().
    """

    name = "title"

    def __init__(
        self,
        page_analyzer: OllamaPageAnalyzer,
    ):
        self.page_analyzer = page_analyzer

    async def execute(
        self,
        case: EvalCase,
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
        )

        return asdict(analysis)

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        """
        Première métrique volontairement simple :

        on vérifie uniquement si le champ relevant correspond
        au verdict humain attendu.
        """
        if "relevant" not in case.expected:
            raise ValueError(
                f"Le cas {case.id!r} ne possède pas de valeur attendue pour 'relevant'."
            )

        expected_relevant = case.expected["relevant"]

        if expected_relevant not in {
            True,
            False,
            None,
        }:
            raise ValueError(
                f"La valeur expected.relevant du cas {case.id!r} "
                "doit être true, false ou null."
            )

        actual_relevant = actual.get("relevant")

        if actual_relevant == expected_relevant:
            return 1.0

        return 0.0

    @staticmethod
    def _get_string(
        case: EvalCase,
        key: str,
    ) -> str:
        if key not in case.input_data:
            raise ValueError(
                f"Le cas {case.id!r} ne possède pas le champ d'entrée {key!r}."
            )

        value = case.input_data[key]

        if not isinstance(value, str):
            raise ValueError(
                f"Le champ {key!r} du cas {case.id!r} doit être une chaîne."
            )

        return value
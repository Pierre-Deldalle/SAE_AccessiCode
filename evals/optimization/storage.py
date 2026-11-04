from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.optimization.models import (
    CandidateEvaluation,
    GeneratedPromptCandidate,
)


class PromptCandidateStore:
    def __init__(
        self,
        root_directory: Path,
    ):
        self.root_directory = (
            root_directory
        )

    def create_run_directory(
        self,
        *,
        task_name: str,
        run_id: str | None = None,
    ) -> tuple[str, Path]:
        if run_id is None:
            run_id = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

        directory = (
            self.root_directory
            / task_name
            / "generated"
            / run_id
        )

        directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        return (
            run_id,
            directory,
        )

    def save_candidates(
        self,
        *,
        directory: Path,
        task_name: str,
        candidates: list[
            GeneratedPromptCandidate
        ],
    ) -> dict[str, Path]:
        paths: dict[str, Path] = {}

        manifest: dict[str, Any] = {
            "task": task_name,
            "candidates": [],
        }

        for candidate in candidates:
            prompt_path = (
                directory
                / f"{candidate.name}.txt"
            )

            metadata_path = (
                directory
                / f"{candidate.name}.json"
            )

            prompt_path.write_text(
                candidate.template,
                encoding="utf-8",
            )

            metadata_path.write_text(
                json.dumps(
                    {
                        "name": candidate.name,
                        "rationale": (
                            candidate.rationale
                        ),
                        "prompt_file": (
                            prompt_path.name
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            paths[
                candidate.name
            ] = prompt_path

            manifest[
                "candidates"
            ].append(
                {
                    "name": candidate.name,
                    "rationale": (
                        candidate.rationale
                    ),
                    "prompt_file": (
                        prompt_path.name
                    ),
                }
            )

        (
            directory
            / "manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return paths

    @staticmethod
    def save_evaluations(
        *,
        directory: Path,
        evaluations: list[
            CandidateEvaluation
        ],
    ) -> None:
        payload = []

        for evaluation in evaluations:
            payload.append(
                {
                    "candidate": (
                        evaluation.candidate.name
                    ),
                    "rationale": (
                        evaluation.candidate.rationale
                    ),
                    "prompt_file": (
                        evaluation.prompt_path.name
                    ),
                    "train": {
                        "report": asdict(
                            evaluation.train_report
                        ),
                        "comparison": asdict(
                            evaluation.train_comparison
                        ),
                    },
                    "validation": {
                        "report": asdict(
                            evaluation.validation_report
                        ),
                        "comparison": asdict(
                            evaluation.validation_comparison
                        ),
                    },
                }
            )

        (
            directory
            / "evaluation.json"
        ).write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    
    @staticmethod
    def save_raw_candidates(
        *,
        directory: Path,
        candidates: list[
            GeneratedPromptCandidate
        ],
    ) -> None:
        raw_directory = (
            directory
            / "raw"
        )

        raw_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for candidate in candidates:
            (
                raw_directory
                / f"{candidate.name}.txt"
            ).write_text(
                candidate.template,
                encoding="utf-8",
            )

            (
                raw_directory
                / f"{candidate.name}.json"
            ).write_text(
                json.dumps(
                    {
                        "name": candidate.name,
                        "rationale": (
                            candidate.rationale
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
    
    @staticmethod
    def save_rejections(
        *,
        directory: Path,
        rejections,
    ) -> None:
        (
            directory
            / "rejections.json"
        ).write_text(
            json.dumps(
                [
                    {
                        "candidate": (
                            rejection.candidate_name
                        ),
                        "reason": (
                            rejection.reason
                        ),
                    }
                    for rejection in rejections
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    
    @staticmethod
    def save_generation_failure(
        *,
        directory: Path,
        raw_response: str,
        parsed_data: dict | None,
        rejection_reasons: list[str],
    ) -> None:
        (
            directory
            / "optimizer_raw_response.txt"
        ).write_text(
            raw_response,
            encoding="utf-8",
        )

        if parsed_data is not None:
            (
                directory
                / "optimizer_parsed_response.json"
            ).write_text(
                json.dumps(
                    parsed_data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        (
            directory
            / "generation_failure.json"
        ).write_text(
            json.dumps(
                {
                    "rejection_reasons": (
                        rejection_reasons
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    
    @staticmethod
    def save_optimization_context(
        *,
        directory: Path,
        context: dict,
    ) -> None:
        (
            directory
            / "optimization_context.json"
        ).write_text(
            json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
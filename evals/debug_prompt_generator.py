from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from accessi_code.config import settings
from evals.optimization.generator import (
    PromptCandidateGenerator,
    PromptGenerationError,
)
from accessi_code.ai.clients.llm import OllamaLLM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Teste uniquement la génération "
            "de prompts à partir d'un contexte "
            "d'optimisation déjà calculé."
        )
    )

    parser.add_argument(
        "context",
        type=Path,
        help=(
            "Chemin vers "
            "optimization_context.json."
        ),
    )

    parser.add_argument(
        "--candidates",
        type=int,
        default=1,
        help=(
            "Nombre de prompts candidats "
            "à générer."
        ),
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.candidates < 1:
        raise SystemExit(
            "--candidates doit être "
            "supérieur ou égal à 1."
        )

    context_path = (
        args.context.resolve()
    )

    if not context_path.exists():
        raise SystemExit(
            f"Fichier introuvable : "
            f"{context_path}"
        )

    optimization_context = json.loads(
        context_path.read_text(
            encoding="utf-8"
        )
    )

    optimizer_llm = OllamaLLM(
        model=settings.VLM_MODEL,
        host=settings.OLLAMA_HOST,
    )

    generator = PromptCandidateGenerator(
        llm=optimizer_llm
    )

    print(
        "Génération du prompt candidat..."
    )

    try:
        candidates = (
            await generator.generate(
                optimization_context=(
                    optimization_context
                ),
                candidate_count=(
                    args.candidates
                ),
            )
        )

    except PromptGenerationError as error:
        failure_directory = (
            context_path.parent
            / "generator_debug"
        )

        failure_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            failure_directory
            / "raw_response.txt"
        ).write_text(
            error.raw_response,
            encoding="utf-8",
        )

        if (
            error.parsed_data
            is not None
        ):
            (
                failure_directory
                / "parsed_response.json"
            ).write_text(
                json.dumps(
                    error.parsed_data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        print()
        print(
            "ÉCHEC DE LA GÉNÉRATION"
        )

        print(
            str(error)
        )

        print()
        print(
            "Réponse sauvegardée dans : "
            f"{failure_directory}"
        )

        return

    print()
    print(
        f"{len(candidates)} "
        "candidat(s) généré(s)."
    )

    for candidate in candidates:
        output_path = (
            context_path.parent
            / (
                f"debug_"
                f"{candidate.name}.txt"
            )
        )

        output_path.write_text(
            candidate.template,
            encoding="utf-8",
        )

        print()
        print(
            f"{candidate.name} :"
        )

        print(
            candidate.template
        )

        print()
        print(
            f"Sauvegardé dans : "
            f"{output_path}"
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
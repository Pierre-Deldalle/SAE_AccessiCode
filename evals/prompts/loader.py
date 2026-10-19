from __future__ import annotations

from pathlib import Path

from evals.models.prompt_variant import PromptVariant


def load_prompt_variant(
    path: Path,
) -> PromptVariant:
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt candidat introuvable : {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Le chemin n'est pas un fichier : {path}"
        )

    template = path.read_text(
        encoding="utf-8",
    ).strip()

    if not template:
        raise ValueError(
            f"Le prompt candidat {path.name!r} est vide."
        )

    return PromptVariant(
        name=path.stem,
        template=template,
        path=path,
    )


def load_prompt_variants(
    directory: Path,
) -> list[PromptVariant]:
    if not directory.exists():
        raise FileNotFoundError(
            f"Dossier de prompts introuvable : {directory}"
        )

    variants = [
        load_prompt_variant(path)
        for path in sorted(
            directory.glob("*.txt")
        )
    ]

    if not variants:
        raise ValueError(
            f"Aucun prompt candidat trouvé dans {directory}."
        )

    return variants

import pytest

from evals.prompts.loader import (
    load_prompt_variant,
    load_prompt_variants,
)


def test_load_prompt_variant(tmp_path):
    prompt_path = tmp_path / "candidate_001.txt"

    prompt_path.write_text(
        "Voici un prompt avec {title}.",
        encoding="utf-8",
    )

    variant = load_prompt_variant(
        prompt_path
    )

    assert variant.name == "candidate_001"
    assert variant.template == "Voici un prompt avec {title}."
    assert variant.path == prompt_path


def test_load_prompt_variant_strips_whitespace(tmp_path):
    prompt_path = tmp_path / "candidate_001.txt"

    prompt_path.write_text(
        "\n\nPrompt candidat.\n\n",
        encoding="utf-8",
    )

    variant = load_prompt_variant(
        prompt_path
    )

    assert variant.template == "Prompt candidat."


def test_load_prompt_variant_rejects_missing_file(tmp_path):
    prompt_path = tmp_path / "missing.txt"

    with pytest.raises(
        FileNotFoundError,
        match="introuvable",
    ):
        load_prompt_variant(
            prompt_path
        )


def test_load_prompt_variant_rejects_directory(tmp_path):
    directory = tmp_path / "candidate"

    directory.mkdir()

    with pytest.raises(
        ValueError,
        match="n'est pas un fichier",
    ):
        load_prompt_variant(
            directory
        )


def test_load_prompt_variant_rejects_empty_prompt(tmp_path):
    prompt_path = tmp_path / "candidate_001.txt"

    prompt_path.write_text(
        "   \n   ",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="est vide",
    ):
        load_prompt_variant(
            prompt_path
        )


def test_load_prompt_variants_loads_txt_files_in_sorted_order(
    tmp_path,
):
    (tmp_path / "candidate_002.txt").write_text(
        "Prompt 2",
        encoding="utf-8",
    )

    (tmp_path / "candidate_001.txt").write_text(
        "Prompt 1",
        encoding="utf-8",
    )

    # Ce fichier ne doit pas être chargé.
    (tmp_path / "notes.md").write_text(
        "Notes",
        encoding="utf-8",
    )

    variants = load_prompt_variants(
        tmp_path
    )

    assert [
        variant.name
        for variant in variants
    ] == [
        "candidate_001",
        "candidate_002",
    ]


def test_load_prompt_variants_rejects_missing_directory(
    tmp_path,
):
    directory = tmp_path / "missing"

    with pytest.raises(
        FileNotFoundError,
        match="Dossier de prompts introuvable",
    ):
        load_prompt_variants(
            directory
        )


def test_load_prompt_variants_rejects_directory_without_txt(
    tmp_path,
):
    (tmp_path / "README.md").write_text(
        "Aucun candidat.",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Aucun prompt candidat",
    ):
        load_prompt_variants(
            tmp_path
        )
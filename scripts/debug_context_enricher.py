"""Teste l'enrichissement du contexte avec les styles calculés."""

import asyncio
from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.input.context_enricher import ContextEnricher
from accessi_code.models.capabilities import Capability


async def main() -> None:
    site_root = Path("test_files/color_site")

    input_files = sorted(path for path in site_root.rglob("*") if path.is_file())

    builder = AuditContextBuilder(
        workspace_root=Path("workspace"),
    )

    context = builder.build(
        input_files=input_files,
        site_root=site_root,
    )

    enricher = ContextEnricher()
    report = await enricher.enrich(context)

    print("\n=== CONTEXTE ===")
    print("Audit ID :", context.audit_id)
    print("HTML :", context.html_path)
    print("Fichiers CSS :", len(context.css_files))
    print(
        "CSS source disponible :",
        context.has_capability(Capability.CSS_SOURCE),
    )

    print("\n=== ENRICHISSEMENT ===")
    print("Observations :", report.total)
    print("Candidates exploitables :", report.usable_count)
    print("À vérifier :", report.review_count)

    if report.error:
        print("Erreur :", report.error)

    print("\n=== OBSERVATIONS ===")

    for observation in report.observations:
        print(f"\nÉlément : {observation.element}")
        print(f"Texte : {observation.text[:80]}")
        print(f"Couleur : {observation.color}")
        print(f"Fond : {observation.background_color}")

        if observation in report.review_observations:
            print("Statut technique : observation à vérifier")
        else:
            print("Statut technique : candidate exploitable")

    print("\n=== CAPACITÉ RGAA ===")
    print(
        "COMPUTED_STYLES :",
        context.has_capability(Capability.COMPUTED_STYLES),
    )


if __name__ == "__main__":
    asyncio.run(main())

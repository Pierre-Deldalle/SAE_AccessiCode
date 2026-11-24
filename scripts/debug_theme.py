"""
Exécute les tests RGAA d'un seul thème sur un site de test_files et affiche,
pour chaque observation, l'élément, le fichier et la ligne, l'extrait HTML, le message et la
recommandation.

Exemples :
    python -m scripts.debug_theme --theme 2 --site site_non_conforme --no-ai
    python -m scripts.debug_theme --theme 2 --site site_demo_rgaa
"""

from __future__ import annotations

import argparse
import asyncio

from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.runner import TestRunner
from scripts.debug_context import build_debug_context
from scripts.debug_rgaa import build_services


async def run(theme: str, site: str, use_ai: bool) -> None:
    context = build_debug_context(site)
    services = build_services(use_ai=use_ai)
    tests = [test for test in build_default_registry() if test.criterion_id.split(".")[0] == theme]
    if not tests:
        print(f"Aucun test enregistré pour le thème {theme}.")
        return

    print(f"Thème {theme} — site {site} — IA {'activée' if use_ai else 'désactivée'}")
    # Le runner, comme lors d'un vrai audit : il vérifie les capacités et indique le fichier des observations.
    for result in await TestRunner(TestRegistry(tests), services).run_all(context):
        print(f"\n{result.test_id} → {result.status.value} : {result.summary}")
        for finding in result.findings:
            where = f"{finding.file or '?'}, ligne {finding.line}" if finding.line is not None else "ligne inconnue"
            print(f"  - {finding.element} ({where})")
            if finding.snippet:
                print(f"    Extrait        : {finding.snippet}")
            print(f"    Message        : {finding.message}")
            if finding.recommendation:
                print(f"    Recommandation : {finding.recommendation}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exécute les tests RGAA d'un thème sur un site de test_files.")
    parser.add_argument("--theme", required=True, help="Numéro du thème (par exemple 2).")
    parser.add_argument("--site", default="site_demo_rgaa", help="Dossier de test_files (défaut : site_demo_rgaa).")
    parser.add_argument("--no-ai", action="store_true", help="Exécute les tests sans les services Ollama.")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.theme, arguments.site, use_ai=not arguments.no_ai))


if __name__ == "__main__":
    main()

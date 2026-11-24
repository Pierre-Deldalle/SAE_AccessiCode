"""Exécute une thématique RGAA sur un site de test et affiche ses observations."""

import argparse
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.themes import THEMES_BY_NUMBER, filter_registry_by_themes
from accessi_code.service.audit_service import AuditService
from scripts.debug_rgaa import build_services, print_finding


async def run_debug(*, theme: int, site: Path, use_ai: bool) -> None:
    files = sorted(path for path in site.rglob("*") if path.is_file())
    registry = filter_registry_by_themes(build_default_registry(), {theme})
    services = build_services(use_ai=use_ai)

    with TemporaryDirectory(prefix="accessicode-debug-") as workspace:
        context = AuditContextBuilder(Path(workspace)).build(files, site_root=site)
        result = await AuditService(registry=registry, services=services).audit(context)

    print(f"{THEMES_BY_NUMBER[theme].label} — {result.status.value} ({result.statistics.total_tests} tests)")
    for criterion in result.criteria:
        print(f"\nCritère {criterion.criterion_id} — {criterion.status.value}")
        for test in criterion.tests:
            print(f"  {test.test_id} — {test.status.value}")
            for finding in test.findings:
                line = str(finding.line) if finding.line is not None else "inconnue"
                print(f"      Source : {finding.file or 'fichier inconnu'}, ligne {line}")
                if finding.snippet is not None:
                    print(f"      Extrait : {finding.snippet}")
                print_finding(finding)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", type=int, choices=THEMES_BY_NUMBER, required=True)
    parser.add_argument("--site", default="site_demo_rgaa", help="Dossier du site dans test_files.")
    parser.add_argument("--no-ai", action="store_true", help="Exécuter les tests sans les services Ollama.")
    args = parser.parse_args()
    site = Path("test_files") / args.site
    if not (site / "index.html").is_file():
        parser.error(f"Fichier principal introuvable : {site / 'index.html'}")
    asyncio.run(run_debug(theme=args.theme, site=site, use_ai=not args.no_ai))


if __name__ == "__main__":
    main()

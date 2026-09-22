"""Orchestration assistée par IA du test RGAA 1.7.1."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from accessi_code.analysis.images import ImageInfo, extract_images, get_images_for_criterion_1_7
from accessi_code.ai.schemas import DescriptionAnalysis
from accessi_code.models.result import Finding, TestResult as Result, TestStatus as ResultStatus


class Criterion17:
    """Exécute le test 1.7.1 pour chaque description détaillée trouvée."""

    test_id = "1.7.1"
    criterion_id = "1.7"

    def __init__(self, analyzer: Callable[[ImageInfo, Any], DescriptionAnalysis] | None = None):
        # L'analyseur est injectable pour séparer le moteur RGAA des modèles
        # Ollama et permettre des tests rapides avec un faux analyseur.
        self.analyzer = analyzer

    def run(
        self,
        html: str,
        *,
        analyzer: Callable[[ImageInfo, Any], DescriptionAnalysis] | None = None,
        base_dir: str | None = None,
    ) -> Result:
        # L'extraction HTML et la sélection du périmètre restent déterministes;
        # l'IA intervient seulement pour juger la pertinence des descriptions.
        images = get_images_for_criterion_1_7(extract_images(html, base_dir=base_dir))
        if not images:
            return Result(self.test_id, self.criterion_id, ResultStatus.NOT_APPLICABLE, "Aucune image avec description détaillée détectée.")

        effective_analyzer = analyzer or self.analyzer
        findings: list[Finding] = []
        passed = 0
        failed = 0
        inconclusive = 0
        for image in images:
            for description in image.descriptions:
                # Chaque source est évaluée séparément et reste identifiable
                # dans les preuves, même si plusieurs sources concernent la même image.
                evidence = {"src": image.src, "description_source": description.source, "description_reference": description.reference, "description": description.content}
                if not description.available:
                    # Une description absente ou inaccessible ne peut pas être
                    # déclarée pertinente par défaut.
                    inconclusive += 1
                    findings.append(Finding(f"img[index={image.index}]", "Description détaillée inaccessible ou vide.", "Rendre la description accessible puis vérifier sa pertinence.", {**evidence, "error": description.error}))
                    continue
                if effective_analyzer is None:
                    # Sans service IA configuré, on signale l'absence d'analyse
                    # plutôt que de fabriquer un verdict de conformité.
                    inconclusive += 1
                    findings.append(Finding(f"img[index={image.index}]", "La pertinence nécessite une analyse IA ou humaine.", "Comparer la description à l'image et à son contexte.", evidence))
                    continue
                try:
                    analysis = effective_analyzer(image, description)
                    # Le moteur n'accepte que le schéma structuré prévu pour
                    # distinguer un verdict, une incertitude et ses preuves.
                    if not isinstance(analysis, DescriptionAnalysis):
                        raise TypeError("La réponse de l'analyseur n'est pas DescriptionAnalysis.")
                except Exception as error:
                    inconclusive += 1
                    findings.append(Finding(f"img[index={image.index}]", "L'analyse IA de pertinence a échoué.", "Rendre l'image accessible au modèle puis relancer l'analyse.", {**evidence, "error": str(error)}))
                    continue
                evidence["analysis"] = analysis.__dict__
                if analysis.relevant is True:
                    passed += 1
                elif analysis.relevant is False:
                    # Un seul verdict négatif suffit à rendre le test non conforme.
                    failed += 1
                    findings.append(Finding(f"img[index={image.index}]", analysis.explanation or "La description détaillée n'est pas pertinente.", "Compléter la description avec les informations importantes de l'image.", evidence))
                else:
                    inconclusive += 1
                    findings.append(Finding(f"img[index={image.index}]", analysis.explanation or "La réponse IA ne permet pas de déterminer la pertinence.", "Fournir une image et une description exploitables puis relancer l'analyse.", evidence))

        # L'incertitude ne devient jamais un échec automatique, mais empêche
        # aussi de déclarer le test conforme tant qu'une description reste à analyser.
        status = ResultStatus.FAIL if failed else ResultStatus.INCONCLUSIVE if inconclusive else ResultStatus.PASS
        return Result(
            self.test_id, self.criterion_id, status,
            f"{len(images)} image(s) analysée(s), {passed} description(s) pertinente(s), {failed} non pertinente(s), {inconclusive} indisponible(s).",
            findings, len(images), {"images_with_descriptions": len(images)},
        )
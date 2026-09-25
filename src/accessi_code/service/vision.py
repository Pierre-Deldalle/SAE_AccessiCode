"""Service d'audit d'accessibilité d'une interface rendue en image."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from json_repair import repair_json

from ..ai.prompts.images import IMAGE_AUDIT_PROMPT
from ..ollama_client.vlm import OllamaVLM

VLM_TESTS = (
    # Cette liste impose le même périmètre de critères que le tableau LLM.
    ("1.1.1", "Alternative textuelle des images (attribut non visible)"),
    ("1.1.2", "Pertinence de l'alternative des images (contenu visuel)"),
    ("1.1.3", "Alternative des images contenant du texte"),
    ("1.7.1", "Description détaillée des images complexes"),
    ("5.1.1", "Lisibilité et structure apparente des tableaux"),
    ("8.1.1", "Type de document HTML (non visible dans une capture)"),
    ("8.4.1", "Langue apparente du contenu visible"),
    ("8.6.1", "Titre visible pertinent pour identifier la page"),
    ("11.1.1", "Présence et lisibilité des champs de formulaire"),
)


def _json_object(value: str) -> dict[str, Any]:
    """Extrait un objet JSON même si le modèle ajoute du texte parasite."""
    text = value.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Les modèles peuvent produire un JSON presque valide ; la réparation
        # évite de perdre tout le rapport pour une erreur de ponctuation.
        result = json.loads(repair_json(text))
    if not isinstance(result, dict):
        raise ValueError("La réponse IA n'est pas un objet JSON.")
    return result


class VisionAuditService:
    """Orchestre un audit vision autonome, comme l'audit LLM HTML."""

    def __init__(self, vlm_client: OllamaVLM):
        self.vlm = vlm_client

    @staticmethod
    def _audit_prompt() -> str:
        # Le catalogue est injecté dans le prompt pour obtenir un résultat
        # séparé et comparable pour chaque critère du tableau.
        criteria = "\n".join(f"- {test_id} : {description}" for test_id, description in VLM_TESTS)
        return (
            f"{IMAGE_AUDIT_PROMPT}\n\n"
            "Évalue séparément chacun des critères suivants et retourne une "
            "entrée dans tests pour chacun, même si le critère est INCONCLUSIF.\n"
            f"{criteria}\n"
            "Pour chaque entrée de tests, utilise test_id, status, "
            "tested_elements, summary et issues_found. Pour les critères "
            "visuels, compte les éléments visibles et fais remonter les "
            "anomalies de contraste, de lisibilité ou de structure dans "
            "findings avec le test_id concerné. Pour 8.4.1, déduis la langue "
            "apparente en lisant le texte visible, sans inventer la valeur "
            "de l'attribut lang."
        )

    @staticmethod
    def _number(value: Any) -> int:
        try:
            return max(0, int(value))
        except TypeError, ValueError:
            return 0

    async def audit_image(self, image: str | Path | bytes | bytearray) -> dict[str, Any]:
        # Le format JSON réduit le travail de parsing et rend la réponse
        # directement exploitable par l'interface Gradio.
        response = await self.vlm.generate(
            prompt=self._audit_prompt(),
            image=image,
            format="json",
            max_tokens=1500,
            temperature=0,
        )
        data = _json_object(response)
        # Toute valeur inattendue est ramenée à un statut prudent.
        status = data.get("status", "INCONCLUSIF")
        if status not in {"CONFORME", "NON_CONFORME", "INCONCLUSIF"}:
            status = "INCONCLUSIF"

        # On normalise les anomalies avant de les exposer au reste de l'app.
        findings = data.get("findings", [])
        if not isinstance(findings, list):
            findings = []
        normalized_findings = [
            {
                "test_id": str(finding.get("test_id", "")),
                "element": str(finding.get("element", "élément visible")),
                "issue": finding.get("issue"),
                "recommendation": finding.get("recommendation"),
                "confidence": finding.get("confidence", "low")
                if finding.get("confidence") in {"low", "medium", "high"}
                else "low",
            }
            for finding in findings
            if isinstance(finding, dict)
        ]
        recommendations = data.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        # Le modèle peut oublier un test : le dictionnaire permet de retrouver
        # rapidement ceux présents et de compléter les autres ci-dessous.
        raw_tests = data.get("tests", [])
        tests_by_id = (
            {test.get("test_id"): test for test in raw_tests if isinstance(test, dict) and test.get("test_id")}
            if isinstance(raw_tests, list)
            else {}
        )
        tests = []
        for test_id, description in VLM_TESTS:
            test = tests_by_id.get(test_id, {})
            # Un critère absent de la réponse reste visible dans le tableau,
            # mais avec un statut INCONCLUSIF plutôt qu'un verdict inventé.
            test_status = test.get("status", "INCONCLUSIF")
            if test_status not in {"CONFORME", "NON_CONFORME", "INCONCLUSIF"}:
                test_status = "INCONCLUSIF"
            tests.append(
                {
                    "test_id": test_id,
                    "status": test_status,
                    "tested_elements": self._number(test.get("tested_elements", 0)),
                    "summary": str(test.get("summary", f"{description} non vérifiable depuis l'image.")),
                    "issues_found": self._number(test.get("issues_found", 0)),
                }
            )

        # Les compteurs sont convertis en entiers pour éviter les valeurs
        # invalides ou négatives dans le rapport et le Dataframe.
        elements_analyzed = self._number(data.get("elements_analyzed", 0))

        return {
            "image": Path(image).name if isinstance(image, (str, Path)) else None,
            "audit_summary": {
                "status": status,
                "elements_analyzed": elements_analyzed,
                "issues_found": len(normalized_findings),
            },
            "tests": tests,
            "summary": str(data.get("summary", "")),
            "findings": normalized_findings,
            "recommendations": [str(item) for item in recommendations],
        }

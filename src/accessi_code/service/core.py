"""Service d'audit LLM complémentaire aux contrôles DOM déterministes."""

import json
from typing import Any, Dict

from json_repair import repair_json

from ..config import settings
from ..ollama_client.llm import OllamaLLM
from .utils import extract_images_and_context

# Ce prompt ne remplace pas les critères DOM : il intervient surtout lorsque
# une image ne possède pas d'alternative détectable automatiquement.
SYSTEM_SINGLE_IMAGE_PROMPT = """Tu es un expert en accessibilité web RGAA / WCAG.
Analyse la balise d'image HTML fournie et réponds EXCLUSIVEMENT avec un objet JSON valide suivant ce modèle :

{
  "image_id": "img_1",
  "src": "nom_image.jpg",
  "rgpa_wcag_status": "NON_CONFORME",
  "suggested_code": "<img src='nom_image.jpg' alt='Description courte'>",
  "recommendations": "Problème : L'attribut alt est absent. Solution : Ajouter un attribut alt décrivant le contenu de l'image."
}

Consignes :
- "rgpa_wcag_status" doit être "CONFORME" ou "NON_CONFORME".
- Dans "recommendations", indique toujours le problème puis la solution.
"""


class AuditService:
    """Orchestre l'analyse textuelle des images qui nécessitent le LLM."""

    def __init__(self, llm_client: OllamaLLM = None):
        # Le client est injectable pour les tests et pour éviter de dépendre
        # d'Ollama dans les contrôles unitaires.
        self.llm = llm_client or OllamaLLM(host=settings.OLLAMA_HOST, model=settings.LLM_MODEL)

    async def _audit_single_image(self, img_data: dict) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_SINGLE_IMAGE_PROMPT},
            {"role": "user", "content": f"Analyse cette image :\n{json.dumps(img_data, ensure_ascii=False)}"},
        ]

        try:
            # L'endpoint chat est utilisé sans format forcé, puis la réponse
            # est nettoyée et réparée ci-dessous si nécessaire.
            response_str = await self.llm.chat(messages=messages, temperature=0.1)

            clean_resp = (response_str or "").strip()

            # Une réponse vide ne doit pas interrompre tout le rapport d'audit.
            if not clean_resp:
                return {
                    "image_id": img_data.get("image_id", "img_1"),
                    "src": img_data.get("src", ""),
                    "rgpa_wcag_status": "NON_CONFORME",
                    "suggested_code": f"<img src='{img_data.get('src')}' alt='Description requise'>",
                    "recommendations": "Problème : Absence d'attribut alt valide. Solution : Ajouter un attribut alt renseigné avec une alternative textuelle concise.",
                }

            # Le modèle peut entourer le JSON d'une phrase ou de balises Markdown.
            start_idx = clean_resp.find("{")
            end_idx = clean_resp.rfind("}")
            if start_idx != -1 and end_idx != -1:
                clean_resp = clean_resp[start_idx : end_idx + 1]

            try:
                parsed = json.loads(clean_resp)
            except json.JSONDecodeError:
                parsed = json.loads(repair_json(clean_resp))

            return {
                "image_id": img_data.get("image_id", "img_1"),
                "src": img_data.get("src", ""),
                "rgpa_wcag_status": parsed.get("rgpa_wcag_status", "NON_CONFORME"),
                "suggested_code": parsed.get("suggested_code", f"<img src='{img_data.get('src')}' alt='...'>"),
                "recommendations": parsed.get(
                    "recommendations", "Problème : Absence d'alternative textuelle. Solution : Ajouter un attribut alt."
                ),
            }

        except Exception:
            return {
                "image_id": img_data.get("image_id", "img_1"),
                "src": img_data.get("src", ""),
                "rgpa_wcag_status": "NON_CONFORME",
                "suggested_code": f"<img src='{img_data.get('src')}' alt='Description requise'>",
                "recommendations": "Problème : Balise img mal configurée ou absente d'alternative. Solution : Ajouter un attribut alt approprié.",
            }

    async def audit_html_content(self, html_content: str) -> Dict[str, Any]:
        images_data = extract_images_and_context(html_content)

        if not images_data:
            return {
                "audit_summary": {"total_images": 0, "issues_found": 0},
                "evaluations": [],
                "message": "Aucune image n'a été trouvée dans le code HTML.",
            }

        evaluations = []
        issues_count = 0

        for img in images_data:
            # L'existence de l'alternative est un contrôle déterministe :
            # inutile de consommer une inférence LLM pour ce cas. Cette étape
            # évite aussi que le modèle contredise à tort le résultat DOM.
            alt = img.get("alt")
            if isinstance(alt, str) and alt.strip():
                evaluations.append(
                    {
                        "image_id": img.get("image_id", "img_1"),
                        "src": img.get("src", ""),
                        "rgpa_wcag_status": "CONFORME",
                        "suggested_code": None,
                        "recommendations": "Alternative textuelle présente ; aucune analyse LLM supplémentaire nécessaire.",
                    }
                )
                continue

            eval_result = await self._audit_single_image(img)
            evaluations.append(eval_result)
            # Le compteur concerne uniquement les résultats réellement produits
            # comme non conformes par l'audit général.
            if eval_result.get("rgpa_wcag_status") != "CONFORME":
                issues_count += 1

        return {
            "audit_summary": {"total_images": len(images_data), "issues_found": issues_count},
            "evaluations": evaluations,
        }

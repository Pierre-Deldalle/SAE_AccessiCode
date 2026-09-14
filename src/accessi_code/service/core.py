import json
from typing import Dict, Any
from json_repair import repair_json
from ..ollama_client.llm import OllamaLLM
from .utils import extract_images_and_context
from ..config import settings

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
    def __init__(self, llm_client: OllamaLLM = None):
        self.llm = llm_client or OllamaLLM(host=settings.OLLAMA_HOST, model=settings.LLM_MODEL)

    async def _audit_single_image(self, img_data: dict) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_SINGLE_IMAGE_PROMPT},
            {"role": "user", "content": f"Analyse cette image :\n{json.dumps(img_data, ensure_ascii=False)}"}
        ]
        
        try:
            # On retire format="json" qui fait planter l'inférence de Gemma sur /api/chat
            response_str = await self.llm.chat(
                messages=messages,
                temperature=0.1
            )
            
            clean_resp = (response_str or "").strip()
            
            # Si le modèle renvoie du vide, on applique un secours manuel propre
            if not clean_resp:
                return {
                    "image_id": img_data.get("image_id", "img_1"),
                    "src": img_data.get("src", ""),
                    "rgpa_wcag_status": "NON_CONFORME",
                    "suggested_code": f"<img src='{img_data.get('src')}' alt='Description requise'>",
                    "recommendations": "Problème : Absence d'attribut alt valide. Solution : Ajouter un attribut alt renseigné avec une alternative textuelle concise."
                }

            # Extraction du JSON dans le texte
            start_idx = clean_resp.find('{')
            end_idx = clean_resp.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean_resp = clean_resp[start_idx:end_idx + 1]

            try:
                parsed = json.loads(clean_resp)
            except json.JSONDecodeError:
                parsed = json.loads(repair_json(clean_resp))

            return {
                "image_id": img_data.get("image_id", "img_1"),
                "src": img_data.get("src", ""),
                "rgpa_wcag_status": parsed.get("rgpa_wcag_status", "NON_CONFORME"),
                "suggested_code": parsed.get("suggested_code", f"<img src='{img_data.get('src')}' alt='...'>"),
                "recommendations": parsed.get("recommendations", "Problème : Absence d'alternative textuelle. Solution : Ajouter un attribut alt.")
            }

        except Exception as e:
            return {
                "image_id": img_data.get("image_id", "img_1"),
                "src": img_data.get("src", ""),
                "rgpa_wcag_status": "NON_CONFORME",
                "suggested_code": f"<img src='{img_data.get('src')}' alt='Description requise'>",
                "recommendations": "Problème : Balise img mal configurée ou absente d'alternative. Solution : Ajouter un attribut alt approprié."
            }

    async def audit_html_content(self, html_content: str) -> Dict[str, Any]:
        images_data = extract_images_and_context(html_content)

        if not images_data:
            return {
                "audit_summary": {"total_images": 0, "issues_found": 0},
                "evaluations": [],
                "message": "Aucune image n'a été trouvée dans le code HTML."
            }

        evaluations = []
        issues_count = 0

        for img in images_data:
            eval_result = await self._audit_single_image(img)
            evaluations.append(eval_result)
            if eval_result.get("rgpa_wcag_status") != "CONFORME":
                issues_count += 1

        return {
            "audit_summary": {
                "total_images": len(images_data),
                "issues_found": issues_count
            },
            "evaluations": evaluations
        }
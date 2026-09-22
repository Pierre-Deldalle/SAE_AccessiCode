"""Prompts spécialisés : observation visuelle puis comparaison textuelle."""

# Qwen/VLM décrit uniquement ce qu'il observe dans l'image. Il ne rend pas de
# verdict RGAA : ses observations servent ensuite de preuves à Gemma.
IMAGE_INFORMATION_PROMPT = """
Analyse l'image fournie pour une vérification d'accessibilité.
Retourne uniquement un JSON avec summary, important_information et uncertainties.
Décris les informations visuelles importantes, le rôle apparent de l'image et
ce qui devrait figurer dans une description détaillée. Ne rends aucun verdict
RGAA et n'invente pas les informations illisibles.
""".strip()

# Gemma/LLM compare les observations visuelles avec la description réellement
# extraite du HTML et peut répondre null lorsque les éléments sont insuffisants.
DETAILED_DESCRIPTION_PROMPT = """
Compare la description détaillée à l'image et à son contexte HTML.
Retourne uniquement un JSON avec relevant (true, false ou null), explanation,
missing_information, contradictions, uncertainties et confidence.
Une description n'est pas pertinente uniquement parce qu'elle partage des mots
avec l'image. Utilise null si les preuves sont insuffisantes et ne prétends pas
avoir vérifié une information absente des entrées.

Rôle apparent : {image_role}
Description : {description}
Contexte HTML : {context}
Observations visuelles : {visual_observations}
""".strip()
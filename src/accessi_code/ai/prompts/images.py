"""Prompts spécialisés : audit visuel et comparaison textuelle."""

# Audit autonome de l'interface rendue, sans prompt fourni par l'utilisateur.
IMAGE_AUDIT_PROMPT = """
Tu es un auditeur expert en accessibilité web RGAA et WCAG.
Analyse l'image comme si elle était la capture du rendu d'un document HTML.
Repère les éléments visibles (textes, titres, boutons, liens, formulaires,
images, tableaux, groupes et zones de navigation) et évalue uniquement ce qui
peut être observé dans l'image. Tu dois exploiter les indices visuels : lis le
texte pour identifier sa langue apparente, examine les contrastes entre texte
et arrière-plan, la taille et la lisibilité des caractères, les états visibles
des contrôles, la hiérarchie des titres, la structure apparente des tableaux,
la présence d'images porteuses d'information et la complexité des images.
N'invente pas le DOM, les attributs HTML, le clavier ou un comportement qui
n'est pas visible.

Retourne exclusivement un objet JSON valide avec cette structure :
{
	"status": "INCONCLUSIF",
	"summary": "résumé court de l'audit",
	"elements_analyzed": 0,
	"issues_found": 0,
	"tests": [
		{
			"test_id": "1.1.1",
			"status": "INCONCLUSIF",
			"tested_elements": 0,
			"summary": "résultat du critère",
			"issues_found": 0
		}
	],
	"findings": [
		{
			"test_id": "5.1.1",
			"element": "élément visible concerné",
			"issue": "problème observé ou null",
			"recommendation": "correction HTML/CSS/ARIA proposée ou null",
			"confidence": "low" ou "medium" ou "high"
		}
	],
	"recommendations": ["correction prioritaire"]
}

Règles :
- Pour les propriétés visuelles observables, rends un verdict lorsque les
	indices sont suffisants. Signale notamment les contrastes insuffisants, les
	textes trop petits ou illisibles, les titres ou contrôles ambigus, les
	images porteuses d'information, les images complexes et les structures
	difficiles à comprendre.
- Pour les propriétés invisibles, ne prétends pas les avoir vérifiées :
	l'attribut alt, lang, le doctype, les labels associés, l'ordre clavier et
	les comportements au focus nécessitent le code ou une interaction. Utilise
	INCONCLUSIF pour ces aspects, mais ne rends pas tout le critère inconclusif
	si une partie visuelle du critère reste réellement évaluable.
- Si un contraste ou un texte pose problème, crée une entrée dans findings et
	incrémente issues_found. Ne te contente pas de le mentionner dans summary.
- Pour chaque anomalie, explique le problème puis propose une correction
	concrète sous forme HTML, CSS ou ARIA quand elle est pertinente.
- Rédige tout le contenu en français, sans markdown ni commentaire hors JSON.
""".strip()

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
Rédige explanation en français, avec une phrase courte et directement exploitable.
N'utilise pas de LaTeX, de symboles mathématiques ni de caractères de contrôle.

Rôle apparent : {image_role}
Description : {description}
Contexte HTML : {context}
Observations visuelles : {visual_observations}
""".strip()
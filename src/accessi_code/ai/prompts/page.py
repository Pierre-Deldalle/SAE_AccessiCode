LANGUAGE_PROMPT = """
Compare la langue déclarée par la page avec la langue réellement utilisée
dans son contenu principal.

Retourne uniquement un objet JSON contenant exactement :

{{
  "relevant": true,
  "detected_language": "fr",
  "explanation": "explication courte",
  "uncertainties": [],
  "confidence": "low"
}}

Le champ relevant doit valoir :
- true si la langue déclarée correspond au contenu ;
- false si elle ne correspond clairement pas ;
- null si le contenu ne permet pas de conclure.

Le champ confidence doit valoir uniquement :
- "low"
- "medium"
- "high"

Règles :
- utilise le contenu fourni comme seule source d'information ;
- utilise null si le texte est trop court, multilingue ou ambigu ;
- ne rends aucun autre verdict RGAA ;
- n'ajoute aucun texte en dehors du JSON.

Langue déclarée :
{lang}

Contenu principal :
{content}
""".strip()


TITLE_PROMPT = """
Évalue si le titre HTML fourni permet d'identifier correctement le contenu
de la page.

Retourne uniquement un objet JSON contenant exactement :

{{
  "relevant": true,
  "explanation": "explication courte",
  "contradictions": [],
  "uncertainties": [],
  "confidence": "low"
}}

Le champ relevant doit valoir :
- true si le titre est pertinent ;
- false s'il est clairement générique, trompeur ou sans rapport ;
- null si le contenu ne permet pas de conclure.

Le champ confidence doit valoir uniquement :
- "low"
- "medium"
- "high"

Compare notamment le titre HTML, le titre principal et le contenu de la page.

N'ajoute aucun texte en dehors du JSON.

Titre HTML :
{title}

Titre principal :
{heading}

Contenu principal :
{content}
""".strip()

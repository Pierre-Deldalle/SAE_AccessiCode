IMAGE_INFORMATION_PROMPT = """
Analyse uniquement le contenu visuel de l'image fournie dans le cadre
d'une vérification d'accessibilité numérique.

Retourne uniquement un objet JSON contenant exactement les champs suivants :

{
  "summary": "description générale du contenu et du rôle apparent de l'image",
  "important_information": ["information importante 1", "information importante 2"],
  "uncertainties": ["élément impossible à identifier avec certitude"]
}

Règles :
- décris uniquement les éléments réellement observables ;
- n'invente aucune information invisible ou illisible ;
- indique dans uncertainties tout élément incertain ;
- ne rends aucun verdict de conformité RGAA ;
- ne propose aucune correction HTML ;
- n'ajoute aucun commentaire en dehors du JSON.
""".strip()


DETAILED_DESCRIPTION_PROMPT = """
Compare une description détaillée d'image avec les observations visuelles
et le contexte HTML fournis.

Retourne uniquement un objet JSON contenant exactement les champs suivants :

{
  "relevant": true,
  "explanation": "explication courte",
  "missing_information": [],
  "contradictions": [],
  "uncertainties": [],
  "confidence": "low"
}

Le champ relevant doit valoir :
- true si la description est pertinente ;
- false si elle est clairement insuffisante ou contradictoire ;
- null si les informations disponibles ne permettent pas de conclure.

Le champ confidence doit valoir uniquement :
- "low"
- "medium"
- "high"

Règles :
- une description n'est pas pertinente uniquement parce qu'elle partage
  des mots avec l'image ;
- ne prétends jamais avoir observé une information absente des données ;
- utilise null lorsque les preuves sont insuffisantes ;
- rédige explanation en français ;
- n'ajoute aucun texte en dehors du JSON.

Rôle apparent de l'image :
{image_role}

Description détaillée :
{description}

Contexte HTML :
{context}

Observations visuelles :
{visual_observations}
""".strip()


IMAGE_INFORMATION_ROLE_PROMPT = """
Détermine si l'image analysée semble porteuse d'information dans le contexte
de la page web.

Une image est porteuse d'information lorsqu'elle transmet une information
nécessaire ou utile à la compréhension du contenu ou à l'utilisation
de la page.

Une image purement décorative, qui pourrait être retirée sans perte
d'information ou de fonctionnalité, n'est pas considérée comme porteuse
d'information.

Retourne uniquement un objet JSON sous cette forme :

{
  "information_bearing": true,
  "explanation": "explication courte",
  "uncertainties": [],
  "confidence": "low"
}

Le champ information_bearing doit valoir :
- true si l'image semble clairement porteuse d'information ;
- false si elle semble clairement décorative ;
- null si les informations disponibles ne permettent pas de conclure.

Le champ confidence doit valoir uniquement :
- "low"
- "medium"
- "high"

Important :
- utilise à la fois les observations visuelles et le contexte de la page ;
- la présence ou l'absence d'un attribut alt ne doit pas servir à déterminer
  si l'image est porteuse d'information ;
- n'invente aucune information absente ;
- utilise null en cas de doute ;
- ne rends aucun verdict RGAA ;
- n'ajoute aucun texte en dehors du JSON.

Élément HTML :
{element_html}

Contexte textuel :
{context}

Observations visuelles :
{visual_observations}
""".strip()
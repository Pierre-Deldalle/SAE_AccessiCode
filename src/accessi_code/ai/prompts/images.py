IMAGE_INFORMATION_PROMPT = """
Observe uniquement l'image fournie.

Décris de manière factuelle :
- ce qui est représenté ;
- les textes visibles ;
- les informations, valeurs, relations, actions ou données importantes ;
- les éléments que tu ne peux pas déterminer avec certitude.

Ne juge pas la conformité RGAA.

Retourne uniquement ce JSON :

{{
    "summary": "description synthétique",
    "important_information": [
        "information importante"
    ],
    "uncertainties": [
        "incertitude éventuelle"
    ]
}}
"""


IMAGE_INFORMATION_ROLE_PROMPT = """
Tu dois déterminer le rôle informationnel d'une image dans le contexte
d'une page web.

Une image est porteuse d'information si elle véhicule une information
nécessaire à la compréhension du contenu auquel elle est associée.
Une illustration purement décorative qui n'apporte aucune information
nécessaire n'est pas porteuse d'information.

IMPORTANT :
- ne déduis jamais le rôle de l'image de la présence ou de l'absence
  d'un attribut alt ;
- ne rends aucun verdict de conformité RGAA ;
- utilise l'observation visuelle, l'élément HTML et le contexte ;
- retourne null si les informations ne permettent pas de conclure.

Élément HTML :
{element_html}

Contexte :
{context}

Observation visuelle :
{visual_observations}

Retourne uniquement :

{{
    "information_bearing": true,
    "explanation": "explication",
    "uncertainties": [],
    "confidence": "high"
}}

information_bearing doit être true, false ou null.
confidence doit être "low", "medium" ou "high".
"""


IMAGE_ELEMENT_ROLE_PROMPT = """
Tu dois déterminer si un élément HTML possédant role="img" semble
porter une information nécessaire à la compréhension du contenu.

Tu ne disposes pas nécessairement de l'image rendue.

Base-toi uniquement sur :
- le code de l'élément ;
- son contenu ;
- ses attributs ;
- le contexte textuel environnant.

Ne déduis jamais le rôle informationnel uniquement de la présence
d'une alternative textuelle.
Ne rends aucun verdict RGAA.
Retourne null si tu ne peux pas conclure.

Élément :
{element_html}

Contexte :
{context}

Retourne uniquement :

{{
    "information_bearing": true,
    "explanation": "explication",
    "uncertainties": [],
    "confidence": "medium"
}}
"""


IMAGE_MAP_AREA_ROLE_PROMPT = """
Une zone <area> appartient à une image réactive.

Détermine si cette zone semble porter une information ou une fonction
nécessaire pour l'utilisateur.

Ne juge pas la présence de son alternative textuelle et ne rends pas
de verdict RGAA.

Zone :
{area_html}

Destination :
{href}

Forme :
{shape}

Coordonnées :
{coords}

Contexte :
{context}

Observation de l'image associée :
{visual_observations}

Retourne uniquement :

{{
    "information_bearing": true,
    "explanation": "explication",
    "uncertainties": [],
    "confidence": "medium"
}}

information_bearing doit être true, false ou null.
"""


DETAILED_DESCRIPTION_PROMPT = """
Tu dois analyser un texte candidat à une description détaillée d'une image.

Une description détaillée doit restituer les informations importantes
portées par l'image lorsqu'une alternative courte ne suffit pas.

Tu dois déterminer séparément :
1. si le texte constitue réellement une description détaillée ;
2. si, lorsqu'il s'agit bien d'une description détaillée, elle est
   pertinente par rapport à l'image.

Rôle visuel synthétique :
{image_role}

Description candidate :
{description}

Contexte :
{context}

Observations visuelles :
{visual_observations}

Ne rends aucun verdict RGAA.

Retourne uniquement :

{{
    "is_detailed_description": true,
    "relevant": true,
    "explanation": "explication",
    "missing_information": [],
    "contradictions": [],
    "uncertainties": [],
    "confidence": "high"
}}

is_detailed_description doit être true, false ou null.
relevant doit être true, false ou null.
Si is_detailed_description vaut false, relevant doit être null.
"""

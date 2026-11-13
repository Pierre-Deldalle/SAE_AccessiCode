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


IMAGE_PROFILE_PROMPT = """
Tu établis le profil d'une image d'une page web. Ce profil sert ensuite à
plusieurs critères RGAA ; tu ne rends toi-même aucun verdict de conformité.

Définitions :
- information_bearing : l'image véhicule une information nécessaire à la
  compréhension du contenu (une image dans un lien ou un bouton est porteuse
  d'information). Une image purement décorative ne l'est pas ;
- is_captcha : l'image sert à distinguer un humain d'un robot (CAPTCHA, image-test) ;
- contains_text : l'image contient du texte lisible qui transmet une information ;
- text_content : ce texte, recopié tel quel (chaîne vide sinon) ;
- text_replaceable : le même rendu pourrait être obtenu avec du texte mis en forme
  en CSS (false pour un logo, une marque, un texte faisant partie d'une photo,
  d'un CAPTCHA ou d'un effet graphique impossible à reproduire en CSS ; null si
  l'image ne contient pas de texte) ;
- needs_detailed_description : l'image est complexe (graphique, schéma, carte,
  infographie, tableau en image) et son information ne peut pas tenir dans
  une alternative courte.

IMPORTANT :
- ne déduis jamais le rôle de l'image de la présence ou du contenu de l'attribut alt ;
- utilise l'observation visuelle, l'élément HTML et le contexte ;
- utilise null pour tout champ que tu ne peux pas déterminer.

Élément HTML :
{element_html}

Contexte :
{context}

Observation visuelle :
{visual_observations}

Retourne uniquement :

{{
    "information_bearing": true,
    "is_captcha": false,
    "contains_text": false,
    "text_content": "",
    "text_replaceable": null,
    "needs_detailed_description": false,
    "explanation": "explication courte",
    "uncertainties": [],
    "confidence": "high"
}}

confidence doit être "low", "medium" ou "high".
"""


ALTERNATIVE_RULES = {
    "alternative": (
        "RGAA 1.3 : l'alternative textuelle d'une image porteuse d'information doit être pertinente "
        "(elle transmet la même information que l'image, ou sa fonction si l'image est dans un lien "
        "ou un bouton) et courte et concise (une description longue relève d'une description détaillée)."
    ),
    "captcha": (
        "RGAA 1.4 : l'alternative textuelle d'un CAPTCHA ou d'une image-test doit permettre d'identifier "
        "la nature et la fonction de l'image (par exemple « Code de sécurité à recopier »), sans "
        "nécessairement en donner le contenu."
    ),
}


ALTERNATIVE_RELEVANCE_PROMPT = """
Tu compares l'alternative textuelle d'une image à son contenu.

{rule}

Élément HTML :
{element_html}

Alternative textuelle à évaluer :
{alternative}

Contexte :
{context}

Observation visuelle :
{visual_observations}

Indique :
- relevant : true si l'alternative est pertinente selon la règle, false si elle ne l'est
  clairement pas (générique, nom de fichier, contenu différent de l'image…), null si tu ne
  peux pas conclure ;
- concise : true si l'alternative est courte et concise, false si elle est trop longue,
  null si tu ne peux pas conclure ;
- missing_information : les informations de l'image absentes de l'alternative.

Utilise null si l'observation visuelle n'est pas disponible et que le HTML ne suffit pas.

Retourne uniquement :

{{
    "relevant": true,
    "concise": true,
    "explanation": "explication courte",
    "missing_information": [],
    "uncertainties": [],
    "confidence": "high"
}}

confidence doit être "low", "medium" ou "high".
"""

"""
Prompts d'analyse des informations transmises par une caractéristique sensorielle.

- "color" : RGAA 3.1 (information donnée uniquement par la couleur) ;
- "shape_size_position" : RGAA 10.9 et 10.10 (information donnée uniquement
  par la forme, la taille ou la position, et pertinence de l'alternative).
"""

from __future__ import annotations

SENSORY_RULES: dict[str, str] = {
    "color": (
        "RGAA 3.1 : une information ne doit pas être donnée uniquement par la couleur. "
        "Exemples non conformes : « les champs en rouge sont obligatoires », un lien distingué du texte "
        "uniquement par sa couleur, une légende de graphique reposant uniquement sur des couleurs. "
        "Conforme si un autre moyen transmet aussi l'information (texte, symbole, motif, soulignement)."
    ),
    "shape_size_position": (
        "RGAA 10.9 et 10.10 : une information ne doit pas être donnée uniquement par la forme, la taille "
        "ou la position. Exemples non conformes : « cliquez sur le bouton rond », « voir la colonne de "
        "droite », « les éléments en gros caractères sont importants ». Conforme si un autre moyen "
        "(texte explicite, intitulé, titre de section) transmet aussi l'information, et si ce moyen est pertinent.\n\n"
        'Ajoute un champ "suggestion" à chaque résultat. Si conveys_information vaut true et confidence vaut medium '
        "ou high, propose une correction quand relies_only_on_sensory vaut true ou quand relies_only_on_sensory "
        "et alternative_relevant valent tous les deux false. Donne le texte exact à écrire, en 120 caractères "
        "maximum. Pour une image, il peut s'agir d'une légende ou d'une description. Reprends les noms, libellés "
        "et faits fournis. Par exemple, si le bouton concerné porte le libellé « Payer », propose « Sélectionnez "
        "Payer pour valider. » Retourne null dans les autres cas ou si les données ne suffisent pas."
    ),
}


SENSORY_BATCH_PROMPT = """
Tu analyses des passages d'une page web pour appliquer la règle suivante :

{rule}

Pour chaque élément fourni, indique :
- conveys_information : la caractéristique sensorielle sert-elle à transmettre une information
  (et pas seulement à décorer) ? true, false ou null ;
- relies_only_on_sensory : l'information repose-t-elle UNIQUEMENT sur cette caractéristique ?
  true, false ou null (null si conveys_information n'est pas true) ;
- alternative_relevant : si un autre moyen transmet aussi l'information, est-il pertinent ?
  true, false ou null (null s'il n'y a pas d'autre moyen) ;
- characteristics : les caractéristiques utilisées ("couleur", "forme", "taille", "position").

Règles :
- appuie-toi uniquement sur le texte, le HTML et le contexte fournis ;
- utilise null si tu ne peux pas conclure ;
- confidence vaut "low", "medium" ou "high" ;
- retourne un résultat pour chaque id fourni ;
- n'ajoute aucun texte en dehors du JSON.

Éléments (JSON) :
{items}

Retourne uniquement :

{{
  "results": [
    {{
      "id": 0,
      "conveys_information": true,
      "relies_only_on_sensory": false,
      "alternative_relevant": true,
      "characteristics": ["position"],
      "explanation": "explication courte",
      "uncertainties": [],
      "confidence": "high"
    }}
  ]
}}
""".strip()


SENSORY_IMAGE_PROMPT = """
Tu analyses une image d'une page web pour appliquer la règle suivante :

{rule}

Élément HTML :
{element_html}

Contexte :
{context}

Observation visuelle de l'image :
{visual_observations}

Indique :
- conveys_information : l'image transmet-elle une information par cette caractéristique
  (couleur, ou forme / taille / position) ? true, false ou null ;
- relies_only_on_sensory : cette information repose-t-elle UNIQUEMENT sur la caractéristique,
  sans texte, symbole ou motif équivalent dans l'image ou son alternative ? true, false ou null ;
- alternative_relevant : si un autre moyen existe, est-il pertinent ? true, false ou null ;
- characteristics : les caractéristiques utilisées.

Utilise null si tu ne peux pas conclure. confidence vaut "low", "medium" ou "high".

Retourne uniquement :

{{
  "conveys_information": true,
  "relies_only_on_sensory": true,
  "alternative_relevant": null,
  "characteristics": ["couleur"],
  "explanation": "explication courte",
  "uncertainties": [],
  "confidence": "medium"
}}
""".strip()

"""
Prompts d'analyse de la structuration de l'information (thème 9).

- "heading" : RGAA 9.1.3, passage de texte qui a l'apparence ou le rôle d'un titre ;
- "list" : RGAA 9.3, suite d'éléments présentée comme une liste ;
- "quote" : RGAA 9.4, citation ;
- "caption" : RGAA 1.9, légende d'image.

La hiérarchie des titres (RGAA 9.1.1) a son propre prompt.
"""

from __future__ import annotations

STRUCTURE_RULES: dict[str, str] = {
    "caption": (
        "RGAA 1.9 : une légende d'image est un texte adjacent à l'image qui la présente, la décrit "
        "brièvement ou la crédite (par exemple « Figure 2 : évolution des ventes », « Photo : J. Martin »). "
        "Une image légendée doit être reliée à sa légende avec figure et figcaption."
    ),
    "heading": (
        "RGAA 9.1 : chaque passage de texte constituant un titre doit être structuré avec une balise "
        'h1 à h6 ou role="heading". Un passage constitue un titre s\'il introduit une section de '
        "contenu (texte court, mis en valeur, suivi du contenu qu'il annonce)."
    ),
    "list": (
        "RGAA 9.3 : chaque liste doit être correctement structurée (ul, ol, dl ou rôles list/listitem). "
        "Un passage constitue une liste s'il présente une suite d'éléments de même nature "
        "(puces, tirets, numéros, retours à la ligne répétés)."
    ),
    "quote": (
        "RGAA 9.4 : chaque citation doit être correctement indiquée (q pour une citation courte, "
        "blockquote pour un bloc). Un passage constitue une citation s'il reproduit les propos ou "
        "l'écrit d'une autre personne ou source."
    ),
}


STRUCTURE_BATCH_PROMPT = """
Tu analyses des passages d'une page web qui ne sont pas balisés sémantiquement.

{rule}

Pour chaque élément fourni, indique should_be_marked :
- true si le passage est réellement de cette nature et devrait être balisé comme tel ;
- false s'il ne l'est pas (texte courant, mise en valeur simple, etc.) ;
- null si tu ne peux pas conclure.

Règles :
- appuie-toi uniquement sur le texte, le HTML et le contexte fournis ;
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
      "should_be_marked": true,
      "explanation": "explication courte",
      "uncertainties": [],
      "confidence": "high"
    }}
  ]
}}
""".strip()


HEADING_HIERARCHY_PROMPT = """
Tu évalues la hiérarchie des titres d'une page web.

RGAA 9.1.1 : la hiérarchie entre les titres (h1 à h6, role="heading" avec aria-level) doit être
pertinente, c'est-à-dire refléter l'organisation réelle du contenu. Un saut de niveau (par exemple
h2 suivi de h4) n'est pas automatiquement une erreur : il faut juger si la structure obtenue
reste cohérente avec le contenu.

Plan des titres de la page (niveau, texte), dans l'ordre du document :
{outline}

Points à examiner en priorité :
{suspicious}

Indique :
- relevant : true si la hiérarchie est pertinente, false si elle ne reflète clairement pas
  l'organisation du contenu, null si tu ne peux pas conclure ;
- problems : les titres concernés et le problème, sous la forme « niveau – texte : problème ».

confidence vaut "low", "medium" ou "high". N'ajoute aucun texte en dehors du JSON.

Retourne uniquement :

{{
  "relevant": true,
  "explanation": "explication courte",
  "problems": [],
  "uncertainties": [],
  "confidence": "high"
}}
""".strip()

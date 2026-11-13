"""
Prompts de jugement de pertinence d'un texte.

Un seul modèle de prompt, paramétré par type d'élément. Chaque type
reprend la règle du RGAA 4.1.2 qu'il sert à appliquer : le modèle juge
uniquement le sens, la décision RGAA reste dans le test.

Pour ajouter un type : ajouter une entrée dans ``RELEVANCE_KINDS``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelevanceKind:
    """Description d'un type de texte à juger."""

    # Nom lisible de l'élément jugé.
    subject: str
    # Règle RGAA appliquée (critère et formulation).
    rule: str
    # Ce qui rend le texte pertinent.
    relevant_when: str
    # Exemples de textes non pertinents.
    not_relevant_examples: str


RELEVANCE_KINDS: dict[str, RelevanceKind] = {
    "frame_title": RelevanceKind(
        subject="titre de cadre (attribut title d'un iframe ou d'un frame)",
        rule="RGAA 2.2 : le titre de chaque cadre doit être pertinent.",
        relevant_when="il décrit le contenu ou la fonction du cadre (par exemple « Carte d'accès au magasin »).",
        not_relevant_examples=(
            "« iframe », « cadre », « frame1 », un nom de fichier, un titre sans rapport avec la source."
        ),
    ),
    "heading": RelevanceKind(
        subject="titre de section (h1 à h6 ou role=heading)",
        rule="RGAA 9.1 : le contenu de chaque titre doit être pertinent.",
        relevant_when="il décrit correctement le contenu de la section qu'il introduit.",
        not_relevant_examples="« Titre », « Section 1 », « Lorem ipsum », un titre sans rapport avec la section.",
    ),
    "link": RelevanceKind(
        subject="intitulé de lien (nom accessible), éventuellement complété par son contexte",
        rule=(
            "RGAA 6.1 : chaque lien doit être explicite, par son intitulé seul ou par son intitulé "
            "associé à son contexte (phrase, paragraphe, item de liste, cellule et en-tête de tableau, "
            "titre de la section)."
        ),
        relevant_when=(
            "l'intitulé, seul ou avec le contexte fourni, permet de comprendre la destination ou la fonction."
        ),
        not_relevant_examples=(
            "« cliquez ici », « en savoir plus », « lire la suite », « ici » sans contexte explicite."
        ),
    ),
    "sitemap_link": RelevanceKind(
        subject="lien de la page « plan du site »",
        rule="RGAA 12.3 : les liens du plan du site doivent être cohérents avec la page qu'ils désignent.",
        relevant_when="l'intitulé correspond au titre ou au contenu principal de la page cible fournie.",
        not_relevant_examples="un intitulé qui désigne une autre page que la page cible, un intitulé générique.",
    ),
    "form_label": RelevanceKind(
        subject="étiquette de champ de formulaire",
        rule="RGAA 11.2 : chaque étiquette associée à un champ de formulaire doit être pertinente.",
        relevant_when="elle indique clairement la donnée attendue dans ce champ (en tenant compte du type de champ).",
        not_relevant_examples="« Champ 1 », « Texte », « Saisir », une étiquette sans rapport avec la donnée attendue.",
    ),
    "fieldset_legend": RelevanceKind(
        subject="légende d'un regroupement de champs (legend, aria-label ou aria-labelledby du groupe)",
        rule="RGAA 11.7 : chaque légende associée à un regroupement de champs de même nature doit être pertinente.",
        relevant_when="elle décrit la nature commune des champs du groupe (par exemple « Adresse de livraison »).",
        not_relevant_examples="« Groupe », « Formulaire », « Informations » quand elle ne distingue pas le groupe.",
    ),
    "button": RelevanceKind(
        subject="intitulé de bouton",
        rule="RGAA 11.9 : l'intitulé de chaque bouton doit être pertinent.",
        relevant_when="il indique l'action déclenchée par le bouton.",
        not_relevant_examples=(
            "« Bouton », « OK » quand l'action n'est pas déductible, « Cliquez », une icône décrite."
        ),
    ),
    "component_name": RelevanceKind(
        subject="nom accessible d'un composant d'interface géré par script",
        rule="RGAA 7.1 : chaque composant d'interface doit avoir un nom pertinent.",
        relevant_when="le nom indique la fonction du composant (par exemple « Ouvrir le menu »).",
        not_relevant_examples=(
            "« div », « composant », « icon », un nom de classe CSS, un nom sans rapport avec l'action."
        ),
    ),
    "table_title": RelevanceKind(
        subject="titre de tableau de données",
        rule="RGAA 5.5 : chaque titre de tableau de données doit être pertinent.",
        relevant_when="il identifie le contenu du tableau (en-têtes et premières lignes fournis en contexte).",
        not_relevant_examples="« Tableau », « Tableau 1 », « Données », un titre sans rapport avec le contenu.",
    ),
    "table_summary": RelevanceKind(
        subject="résumé de tableau de données complexe",
        rule="RGAA 5.2 : chaque résumé de tableau complexe doit être pertinent.",
        relevant_when="il explique l'organisation du tableau (structure des en-têtes, sens de lecture, contenu).",
        not_relevant_examples="« Tableau », « Résumé », la simple répétition du titre sans expliquer la structure.",
    ),
    "media_title": RelevanceKind(
        subject="texte identifiant un média temporel (vidéo ou son)",
        rule="RGAA 4.7 : chaque média temporel doit être clairement identifiable.",
        relevant_when="le texte adjacent identifie clairement le contenu du média (titre, sujet).",
        not_relevant_examples="« Vidéo », « Lecteur », un texte sans rapport avec le média.",
    ),
    "script_alternative": RelevanceKind(
        subject="alternative à un contenu ou une fonctionnalité de script",
        rule="RGAA 7.2 : chaque alternative à un script doit être pertinente.",
        relevant_when="elle donne accès au même contenu ou à la même fonctionnalité que le script.",
        not_relevant_examples="« Activez JavaScript » seul, un texte sans rapport avec la fonctionnalité.",
    ),
}


RELEVANCE_BATCH_PROMPT = """
Tu évalues la pertinence de plusieurs textes extraits d'une page web.

Type d'élément : {subject}
Règle appliquée : {rule}
Un texte est pertinent quand {relevant_when}
Exemples de textes non pertinents : {not_relevant_examples}

Règles :
- juge uniquement le sens du texte, à partir des informations fournies ;
- ne déduis rien de la présence ou de l'absence d'attributs HTML ;
- utilise null si les informations ne permettent pas de conclure ;
- confidence vaut "low", "medium" ou "high" ;
- retourne un résultat pour chaque id fourni, dans le même ordre ;
- n'ajoute aucun texte en dehors du JSON.

Éléments à évaluer (JSON) :
{items}

Retourne uniquement :

{{
  "results": [
    {{
      "id": 0,
      "relevant": true,
      "explanation": "explication courte",
      "problems": [],
      "uncertainties": [],
      "confidence": "high"
    }}
  ]
}}
""".strip()

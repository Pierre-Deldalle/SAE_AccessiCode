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
    # Longueur maximale du texte jugé (les contenus longs, comme un tableau linéarisé, en ont besoin).
    text_limit: int = 300
    # Texte à proposer lorsque l'élément n'est pas pertinent ; vide : aucune proposition demandée.
    suggestion: str = ""


RELEVANCE_KINDS: dict[str, RelevanceKind] = {
    "frame_title": RelevanceKind(
        subject="titre de cadre (attribut title d'un iframe ou d'un frame)",
        rule="RGAA 2.2 : le titre de chaque cadre doit être pertinent.",
        relevant_when="il décrit le contenu ou la fonction du cadre (par exemple « Carte d'accès au magasin »).",
        not_relevant_examples=(
            "« iframe », « cadre », « frame1 », un nom de fichier, un titre sans rapport avec la source."
        ),
        suggestion="un titre de cadre court qui décrit son contenu ou sa fonction",
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
        subject="nom accessible et rôle d'un composant d'interface géré par script",
        rule="RGAA 7.1.3 : chaque composant d'interface doit avoir un nom pertinent et un rôle pertinent.",
        relevant_when=(
            "le nom indique la fonction du composant (par exemple « Ouvrir le menu ») et le rôle fourni "
            "(« role ») correspond à son comportement (button pour une action, tab pour un onglet, "
            "checkbox pour une case à cocher…)."
        ),
        not_relevant_examples=(
            "« div », « composant », « icon », un nom de classe CSS, un nom sans rapport avec l'action, "
            "un rôle link sur un composant qui ouvre un panneau, un rôle button sur un onglet."
        ),
    ),
    "table_title": RelevanceKind(
        subject="titre de tableau de données",
        rule="RGAA 5.5 : chaque titre de tableau de données doit être pertinent.",
        relevant_when="il identifie le contenu du tableau (en-têtes et premières lignes fournis en contexte).",
        not_relevant_examples="« Tableau », « Tableau 1 », « Données », un titre sans rapport avec le contenu.",
        suggestion="un titre de tableau court qui identifie son contenu",
    ),
    "table_summary": RelevanceKind(
        subject="résumé de tableau de données complexe",
        rule="RGAA 5.2 : chaque résumé de tableau complexe doit être pertinent.",
        relevant_when="il explique l'organisation du tableau (structure des en-têtes, sens de lecture, contenu).",
        not_relevant_examples="« Tableau », « Résumé », la simple répétition du titre sans expliquer la structure.",
        suggestion="un résumé court qui explique l'organisation du tableau (en-têtes, sens de lecture)",
    ),
    "layout_table_linearized": RelevanceKind(
        subject=(
            "contenu d'un tableau de mise en forme, lu dans l'ordre du code source "
            "(une cellule par ligne, de gauche à droite puis de haut en bas)"
        ),
        rule="RGAA 5.3 : pour chaque tableau de mise en forme, le contenu linéarisé doit rester compréhensible.",
        relevant_when=(
            "lu dans cet ordre, le contenu garde un sens et un ordre logiques : les phrases ne sont pas coupées "
            "entre plusieurs cellules et chaque étiquette reste à côté de la valeur qu'elle décrit."
        ),
        not_relevant_examples=(
            "des étiquettes toutes lues avant leurs valeurs, une phrase répartie sur plusieurs colonnes lue "
            "dans le désordre, des colonnes qui n'ont de sens que lues de haut en bas."
        ),
        text_limit=1500,
    ),
    "media_title": RelevanceKind(
        subject="texte identifiant un média temporel (vidéo ou son)",
        rule="RGAA 4.7 : chaque média temporel doit être clairement identifiable.",
        relevant_when="le texte adjacent identifie clairement le contenu du média (titre, sujet).",
        not_relevant_examples="« Vidéo », « Lecteur », un texte sans rapport avec le média.",
    ),
    # ---- Formulaires (thème 11) : questions de classement ----
    "label_consistency": RelevanceKind(
        subject="ensemble d'étiquettes de champs ayant la même fonction (même page ou ensemble de pages)",
        rule="RGAA 11.3 : chaque étiquette associée à un champ ayant la même fonction doit être cohérente.",
        relevant_when=(
            "les étiquettes fournies désignent clairement la même donnée de manière cohérente "
            "(« Courriel » et « Adresse e-mail » sont cohérentes ; « Nom » et « Identifiant » ne le sont pas)."
        ),
        not_relevant_examples="deux étiquettes qui laissent croire à des données différentes pour la même fonction.",
    ),
    "field_grouping": RelevanceKind(
        subject="liste des champs d'un formulaire qui ne sont dans aucun regroupement (fieldset ou role=group)",
        rule=(
            "RGAA 11.5 : les champs de même nature (adresse, identité, date en plusieurs champs, choix "
            "multiples d'une même question) doivent être regroupés avec fieldset ou role=group."
        ),
        relevant_when=(
            "aucun ensemble de champs de même nature n'a besoin d'être regroupé (champs indépendants). "
            "Indique dans problems les groupes de champs qui devraient être regroupés."
        ),
        not_relevant_examples="« Jour », « Mois », « Année » d'une même date non regroupés ; rue, code postal, ville.",
    ),
    "option_grouping": RelevanceKind(
        subject="options d'une liste de choix (select) sans optgroup",
        rule=(
            "RGAA 11.8 : les items de même nature d'une liste de choix doivent être "
            "regroupés avec optgroup, si nécessaire."
        ),
        relevant_when="les options ne forment pas plusieurs catégories distinctes (aucun regroupement nécessaire).",
        not_relevant_examples="des villes de plusieurs pays mélangées, des produits de plusieurs gammes.",
    ),
    "optgroup_label": RelevanceKind(
        subject="attribut label d'un groupe d'options (optgroup)",
        rule="RGAA 11.8 : le label de chaque optgroup doit être pertinent.",
        relevant_when="il décrit la catégorie commune des options du groupe (fournies en contexte).",
        not_relevant_examples="« Groupe 1 », « Options », un label sans rapport avec les options.",
    ),
    "error_identification": RelevanceKind(
        subject="message d'erreur affiché pour un champ de formulaire",
        rule="RGAA 11.10 : le message d'erreur doit identifier nommément le champ concerné.",
        relevant_when=(
            "le message permet de savoir sans ambiguïté quel champ est en erreur (étiquette fournie en contexte)."
        ),
        not_relevant_examples="« Erreur », « Champ invalide », « Veuillez corriger le formulaire ».",
    ),
    "format_instruction": RelevanceKind(
        subject="texte associé à un champ dont la saisie impose un type ou un format",
        rule=(
            "RGAA 11.10 : pour un champ dont le type ou le format est imposé, une instruction visible "
            "dans l'étiquette ou le texte associé indique ce type ou ce format."
        ),
        relevant_when=(
            "le texte indique clairement le type ou le format attendu pour ce champ (type, pattern et étiquette "
            "fournis en contexte), ou le format est évident pour un champ courant (e-mail clairement étiqueté)."
        ),
        not_relevant_examples=(
            "« Date » sans format alors que jj/mm/aaaa est exigé ; « Code » pour un pattern de 5 chiffres."
        ),
    ),
    "error_suggestion_format": RelevanceKind(
        subject="message d'erreur de saisie",
        rule="RGAA 11.11 : le message d'erreur suggère, si nécessaire, le type et le format de données attendus.",
        relevant_when="le message indique le type ou le format attendu, ou aucune suggestion n'est nécessaire.",
        not_relevant_examples="« Date invalide » sans indiquer le format attendu.",
    ),
    "error_suggestion_example": RelevanceKind(
        subject="message d'erreur de saisie",
        rule="RGAA 11.11 : le message d'erreur suggère, si nécessaire, des exemples de valeurs attendues.",
        relevant_when="le message propose un exemple de valeur attendue, ou aucun exemple n'est nécessaire.",
        not_relevant_examples="« Numéro invalide » pour un format complexe sans exemple.",
    ),
    "transaction_scope": RelevanceKind(
        subject="formulaire (intitulé, champs et boutons fournis)",
        rule=(
            "RGAA 11.12 : sont concernés les formulaires qui ont des conséquences financières ou juridiques, "
            "qui modifient ou suppriment des données de l'utilisateur, ou qui transmettent des réponses à un test."
        ),
        relevant_when=(
            "le formulaire entre dans ce périmètre (paiement, commande, contrat, suppression de compte, examen…). "
            "Un formulaire de contact ou de recherche n'y entre pas."
        ),
        not_relevant_examples="formulaire de recherche, d'inscription à une lettre d'information, de contact.",
    ),
    "sensitive_data_modification": RelevanceKind(
        subject="formulaire (intitulé, champs et boutons fournis)",
        rule=(
            "RGAA 11.12.2 : sont concernés les formulaires qui modifient ou suppriment des données "
            "financières, juridiques ou personnelles."
        ),
        relevant_when="le formulaire modifie ou supprime des données financières, juridiques ou personnelles.",
        not_relevant_examples="paiement ponctuel sans modification de données enregistrées, recherche, contact.",
    ),
    "user_data_field": RelevanceKind(
        subject="champ de formulaire",
        rule=(
            "RGAA 11.13 : les champs qui recueillent une information concernant l'utilisateur lui-même "
            "(nom, e-mail, adresse, téléphone, date de naissance…) doivent identifier leur finalité (autocomplete)."
        ),
        relevant_when="le champ demande une information concernant l'utilisateur lui-même.",
        not_relevant_examples="champ de recherche, message libre, nom d'un tiers, quantité commandée.",
    ),
    "autocomplete_value": RelevanceKind(
        subject="valeur de l'attribut autocomplete d'un champ",
        rule="RGAA 11.13 : la valeur autocomplete doit correspondre à l'information attendue dans le champ.",
        relevant_when="la valeur (fournie dans autocomplete) correspond à la donnée demandée par l'étiquette.",
        not_relevant_examples='autocomplete="email" sur un champ « Téléphone », « given-name » sur « Nom de famille ».',
    ),
    "captcha_alternative": RelevanceKind(
        subject="moyen proposé à la place d'un CAPTCHA graphique (lien, bouton, CAPTCHA audio…)",
        rule=(
            "RGAA 1.5 : pour chaque CAPTCHA, il existe une autre forme de CAPTCHA non graphique, ou une "
            "autre solution d'accès à la fonctionnalité protégée par le CAPTCHA."
        ),
        relevant_when=(
            "il permet réellement d'accéder à la fonctionnalité sans voir l'image (CAPTCHA audio, "
            "contact par un autre canal, validation humaine…)."
        ),
        not_relevant_examples="« Recharger l'image », « Nouvelle image », un lien sans rapport avec le CAPTCHA.",
    ),
    "text_language": RelevanceKind(
        subject="langue d'un passage de texte",
        rule=(
            "RGAA 8.7 : chaque texte écrit dans une langue différente de la langue par défaut doit être "
            "signalé par un attribut lang sur l'élément ou un parent. La langue déclarée pour le passage "
            "est fournie dans « declared_language » ; les parties déjà balisées avec leur propre langue "
            "sont remplacées par [passage balisé]."
        ),
        relevant_when=(
            "tout le texte est dans la langue déclarée, ou les seuls mots d'une autre langue sont des noms "
            "propres, des termes passés dans l'usage courant (« week-end », « e-mail ») ou des mots sans "
            "équivalent. Si un passage est dans une autre langue, cite-le dans « problems »."
        ),
        not_relevant_examples=(
            "« Please contact us » dans un passage déclaré en français, une citation en allemand non balisée, "
            "un paragraphe entier dans une autre langue."
        ),
        text_limit=1500,
    ),
    "language_change": RelevanceKind(
        subject="code de langue d'un changement de langue",
        rule=(
            "RGAA 8.8 : le code de langue de chaque changement de langue (attribut lang, fourni dans "
            "« declared_language ») doit être pertinent."
        ),
        relevant_when="le code correspond à la langue du texte (en pour de l'anglais, de pour de l'allemand…).",
        not_relevant_examples='lang="en" sur un texte en espagnol, lang="fr" sur un texte en anglais.',
    ),
    "script_alternative": RelevanceKind(
        subject="alternative à un contenu ou une fonctionnalité de script",
        rule="RGAA 7.2 : chaque alternative à un script doit être pertinente.",
        relevant_when="elle donne accès au même contenu ou à la même fonctionnalité que le script.",
        not_relevant_examples="« Activez JavaScript » seul, un texte sans rapport avec la fonctionnalité.",
    ),
    # ---- Consultation (thème 13) ----
    "cryptic_context": RelevanceKind(
        subject=(
            "contenu cryptique (émoticône, art ASCII ou syntaxe de type SMS, nature fournie dans « kind ») "
            "et texte qui l'entoure"
        ),
        rule=(
            "RGAA 13.5 : chaque contenu cryptique doit avoir une alternative ; sans attribut title, "
            "une définition doit être donnée par le contexte adjacent."
        ),
        relevant_when=(
            "le texte qui entoure le contenu en donne le sens (par exemple « Merci :) » où le contenu "
            "n'ajoute qu'une nuance, ou une légende qui décrit un dessin en art ASCII)."
        ),
        not_relevant_examples=(
            "« @+ » seul en fin de message sans explication, un dessin en art ASCII sans légende, "
            "une émoticône qui porte seule une information (« Résultat : :( »)."
        ),
    ),
    "cryptic_alternative": RelevanceKind(
        subject="alternative (attribut title ou aria-label) d'un contenu cryptique fourni dans « cryptic_content »",
        rule="RGAA 13.6 : l'alternative de chaque contenu cryptique doit être pertinente.",
        relevant_when="elle donne le sens du contenu cryptique (« sourire » pour :-), « à plus tard » pour @+).",
        not_relevant_examples="« émoticône », « image », « art ASCII », un texte sans rapport avec le contenu.",
    ),
    "gesture_alternative": RelevanceKind(
        subject=(
            "fonctionnalité déclenchée par un geste complexe (type fourni dans « gesture » : contact multipoint "
            "ou suivi de trajectoire), décrite par l'extrait de code ; le contexte liste les contrôles de la page"
        ),
        rule=(
            "RGAA 13.10 : chaque fonctionnalité utilisable par un geste complexe doit aussi être utilisable "
            "par un contact en un point unique de l'écran (bouton, lien…), sauf si le geste est essentiel."
        ),
        relevant_when=(
            "un contrôle de la page permet la même action en un seul contact (boutons « Zoom + / Zoom - » pour "
            "un pincement, flèches « Suivant / Précédent » pour un balayage), ou le geste est essentiel "
            "(signature manuscrite, dessin à main levée)."
        ),
        not_relevant_examples=(
            "un carrousel qui ne change de diapositive que par balayage, un zoom de carte uniquement au pincement."
        ),
    ),
    "motion_alternative": RelevanceKind(
        subject=(
            "fonctionnalité déclenchée par un mouvement de l'appareil ou vers l'appareil (type fourni dans "
            "« motion »), décrite par l'extrait de code ; le contexte liste les contrôles de la page"
        ),
        rule=(
            "RGAA 13.12.1 et 13.12.2 : chaque fonctionnalité déclenchée par un mouvement de l'appareil ou vers "
            "l'appareil doit pouvoir être accomplie avec des composants d'interface, sauf si le mouvement est "
            "essentiel."
        ),
        relevant_when=(
            "un contrôle de la page permet la même action (bouton « Annuler » pour « secouer pour annuler », "
            "flèches pour un défilement par inclinaison), ou le mouvement est essentiel (podomètre, niveau à bulle)."
        ),
        not_relevant_examples=(
            "« secouer pour annuler » sans bouton d'annulation, une navigation par inclinaison seule."
        ),
    ),
    "motion_disable": RelevanceKind(
        subject=(
            "fonctionnalité déclenchée par un mouvement de l'appareil ou vers l'appareil, décrite par l'extrait "
            "de code ; « disable_code » indique si le code retire l'écoute du capteur ; le contexte liste "
            "les contrôles de la page"
        ),
        rule=(
            "RGAA 13.12.3 : l'utilisateur doit pouvoir désactiver la détection du mouvement pour éviter un "
            "déclenchement accidentel, sauf si le mouvement est essentiel."
        ),
        relevant_when=(
            "un contrôle de la page permet de désactiver la détection (case « Désactiver le secouement », "
            "interrupteur des capteurs), ou le mouvement est essentiel à la fonctionnalité."
        ),
        not_relevant_examples="aucun contrôle de désactivation, un réglage sans rapport avec le mouvement.",
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
- n'ajoute aucun texte en dehors du JSON.{suggestion_rule}

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
      "confidence": "high"{suggestion_field}
    }}
  ]
}}
""".strip()

# Ajoutés au prompt uniquement pour les types qui demandent une proposition (RelevanceKind.suggestion) :
# le prompt des autres types reste inchangé.
SUGGESTION_RULE = (
    "\n- si relevant vaut false, propose dans suggestion {suggestion}, déduit uniquement des informations "
    "fournies (source, contexte) ; sinon, ou si les informations ne suffisent pas, suggestion vaut null."
)
SUGGESTION_FIELD = ',\n      "suggestion": null'


def suggestion_parts(kind: RelevanceKind) -> dict[str, str]:
    """Consigne et champ JSON de la proposition, vides si le type n'en demande pas."""
    if not kind.suggestion:
        return {"suggestion_rule": "", "suggestion_field": ""}
    return {
        "suggestion_rule": SUGGESTION_RULE.format(suggestion=kind.suggestion),
        "suggestion_field": SUGGESTION_FIELD,
    }

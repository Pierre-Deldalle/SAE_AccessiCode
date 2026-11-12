# Comprendre les résultats

Après une analyse, AccessiCode affiche un tableau récapitulatif contenant les contrôles exécutés et leurs résultats.

## Tableau des résultats

| Colonne | Signification |
| --- | --- |
| **Critère** | Identifiant du contrôle RGAA concerné. |
| **Statut** | Conclusion obtenue pour le contrôle. |
| **Éléments testés** | Nombre d'éléments examinés. |
| **Résumé** | Explication courte du résultat. |
| **Anomalies** | Nombre d'observations nécessitant une attention particulière. |

Un rapport détaillé peut compléter ce tableau avec les éléments concernés, les preuves disponibles et, lorsque cela est possible, une recommandation.

## Signification des statuts

### `pass`

Le contrôle exécuté n'a détecté aucune anomalie dans les éléments examinés.

Cela ne signifie pas que la page entière est conforme au RGAA.

### `fail`

Une ou plusieurs anomalies ont été détectées.

Les éléments concernés doivent être examinés afin de confirmer le problème et d'appliquer, si nécessaire, une correction.

### `needs_review`

AccessiCode ne dispose pas de suffisamment d'informations ou de certitude pour conclure automatiquement.

Une vérification humaine est nécessaire.

### `not_applicable`

Aucun élément correspondant au contrôle n'a été trouvé dans la page.

Le contrôle ne s'applique donc pas au contenu analysé.

### `not_tested`

Le contrôle n'a pas été exécuté.

Cela peut notamment arriver lorsqu'une information ou un service nécessaire à l'analyse n'est pas disponible.

### `error`

Une erreur technique a empêché le contrôle d'aboutir.

Il est alors nécessaire de consulter les informations associées au résultat afin d'identifier la cause du problème.

## Vérifier les résultats

Une attention particulière doit être portée aux résultats `fail`, `needs_review` et `error`.

Pour un résultat `fail` ou `needs_review` :

1. repérez l'élément concerné dans la page ou dans son code ;
2. vérifiez l'observation dans son contexte réel ;
3. effectuez si nécessaire une vérification au clavier ou avec une technologie d'assistance ;
4. appliquez la correction appropriée ;
5. relancez AccessiCode ;
6. vérifiez manuellement que le problème est réellement résolu.

## Pourquoi une vérification humaine reste nécessaire

Certaines questions d'accessibilité ne peuvent pas être déterminées uniquement à partir du code source.

Une vérification humaine peut notamment être nécessaire pour évaluer :

- la pertinence réelle d'un texte alternatif ;
- la compréhension d'un intitulé ou d'une consigne ;
- la cohérence d'un message d'erreur ;
- l'ordre de navigation au clavier ;
- la visibilité du focus ;
- le comportement des menus ou fenêtres interactives ;
- les changements dynamiques de contenu ;
- les informations transmises uniquement par la couleur ;
- le comportement avec différentes technologies d'assistance.

Les résultats d'AccessiCode doivent donc être considérés comme une aide à l'analyse et non comme une preuve suffisante de conformité.
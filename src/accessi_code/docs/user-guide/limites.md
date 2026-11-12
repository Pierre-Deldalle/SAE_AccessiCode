# Limites d'AccessiCode

AccessiCode est conçu comme un outil d'assistance à l'analyse de l'accessibilité.

Il possède volontairement plusieurs limites qu'il est important de connaître avant d'interpréter ses résultats.

## Couverture partielle du RGAA

AccessiCode ne couvre actuellement qu'une partie des critères et tests du RGAA.

Un contrôle non implémenté n'est pas vérifié automatiquement.

L'absence d'anomalie dans AccessiCode ne signifie donc pas qu'une page est conforme à l'ensemble du référentiel.

## Analyse principalement basée sur les données fournies

La qualité d'une analyse dépend directement des informations transmises à l'application.

Un fichier HTML incomplet, un extrait très court ou une ressource manquante peut rendre certains contrôles impossibles ou moins fiables.

## Interactions complexes

L'analyse d'un document HTML ne permet pas toujours de reproduire toutes les interactions possibles d'un site réel.

Certaines fonctionnalités peuvent dépendre :

- de JavaScript ;
- d'un état de l'application ;
- d'une action de l'utilisateur ;
- de données chargées dynamiquement ;
- d'une authentification ;
- d'un changement de page ou de contexte.

Ces situations peuvent nécessiter une analyse manuelle supplémentaire.

## Analyse par intelligence artificielle

Certaines décisions peuvent être confiées à une intelligence artificielle lorsque le contrôle nécessite une interprétation sémantique ou visuelle.

Ces analyses sont probabilistes.

Une intelligence artificielle peut notamment :

- se tromper ;
- mal interpréter un contexte ;
- produire une réponse trop prudente ;
- produire au contraire une conclusion trop catégorique ;
- manquer une information importante.

Les conclusions importantes doivent donc être vérifiées par une personne.

## Analyse d'une image seule

Une image analysée indépendamment d'une page ne fournit pas son contexte complet.

Une même image peut avoir des usages différents selon :

- le texte qui l'entoure ;
- sa fonction ;
- la présence d'une légende ;
- la présence d'une alternative textuelle ;
- l'action proposée à l'utilisateur.

Une analyse isolée doit donc être interprétée avec prudence.

## Ressources externes

Une ressource absente ou inaccessible peut empêcher certains contrôles d'aboutir.

Cela peut produire :

- un résultat incomplet ;
- `not_tested` ;
- `needs_review` ;
- `error`.

## AccessiCode n'est pas un outil de certification

AccessiCode ne délivre aucune certification de conformité.

Les résultats doivent être utilisés pour :

- repérer des anomalies potentielles ;
- accélérer certaines vérifications ;
- aider à prioriser les corrections ;
- compléter le travail d'un développeur ou d'un auditeur.

Ils ne constituent pas, à eux seuls, une preuve de conformité au RGAA.
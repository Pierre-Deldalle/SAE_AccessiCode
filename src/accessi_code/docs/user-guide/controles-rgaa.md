# Contrôles RGAA disponibles

AccessiCode ne couvre actuellement qu'une partie du **RGAA (Référentiel général d'amélioration de l'accessibilité)**.

La présence d'un contrôle dans AccessiCode signifie uniquement que l'application possède un mécanisme permettant d'analyser certains aspects du critère concerné.

Elle ne garantit pas que l'intégralité du critère RGAA puisse être vérifiée automatiquement.

## Contrôles actuellement intégrés

AccessiCode dispose actuellement de 12 contrôles internes.

| Référence | Sujet général |
| --- | --- |
| `1.1.1` | Alternatives textuelles associées aux images. |
| `1.1.2` | Alternatives textuelles associées aux images. |
| `1.1.3` | Alternatives textuelles associées aux images. |
| `1.7.1` | Description détaillée des images lorsque celle-ci est nécessaire. |
| `5.1.1` | Informations associées aux tableaux. |
| `8.1.1` | Conformité du document HTML. |
| `8.1.2` | Conformité du document HTML. |
| `8.1.3` | Conformité du document HTML. |
| `8.4.1` | Langue déclarée dans le document. |
| `8.5.1` | Présence d'une langue par défaut. |
| `8.6.1` | Pertinence du titre de la page. |
| `11.1.1` | Étiquetage des champs de formulaire. |

## Couverture actuelle par thème

### Images

AccessiCode peut analyser plusieurs aspects liés aux images, notamment les alternatives textuelles et certaines situations nécessitant une description détaillée.

Certaines vérifications peuvent nécessiter une interprétation du contenu ou de l'image et ne peuvent donc pas toujours être réalisées avec certitude automatiquement.

### Tableaux

Un contrôle concernant les informations associées aux tableaux est actuellement disponible.

La présence d'un seul contrôle sur ce thème ne signifie pas que l'ensemble des exigences RGAA concernant les tableaux est couvert.

### Éléments obligatoires d'un document HTML

Plusieurs contrôles portent sur la structure générale du document HTML, sa langue et son titre.

Ils permettent notamment d'examiner certains éléments nécessaires à l'identification et à l'interprétation correcte de la page.

### Formulaires

AccessiCode possède actuellement un contrôle portant sur la présence d'une étiquette associée aux champs de formulaire.

D'autres aspects importants de l'accessibilité des formulaires ne sont pas nécessairement couverts.

## Une couverture volontairement partielle

Le RGAA contient de nombreux critères et tests.

AccessiCode ne doit donc pas être utilisé comme un outil capable de certifier à lui seul la conformité complète d'un site.

Un contrôle absent d'AccessiCode doit être vérifié par d'autres moyens.

La liste des contrôles disponibles évoluera avec les futures versions de l'application.


# Vérification humaine

AccessiCode automatise une partie de l'analyse, mais certaines décisions d'accessibilité nécessitent une interprétation humaine.

La vérification humaine constitue donc une étape essentielle du processus.

## Quand effectuer une vérification humaine ?

Une vérification est particulièrement importante lorsqu'AccessiCode retourne :

- `fail` ;
- `needs_review` ;
- un résultat produit à partir d'une interprétation par intelligence artificielle ;
- une observation qui semble incohérente avec la page réellement affichée.

Même un résultat `pass` ne doit pas être interprété comme une garantie de conformité de l'ensemble de la page.

## Procédure recommandée

Lorsqu'une anomalie est signalée :

1. repérez l'élément concerné dans le code et dans la page affichée ;
2. vérifiez que l'observation correspond au contexte réel de l'utilisateur ;
3. reproduisez si nécessaire l'interaction concernée ;
4. effectuez les vérifications manuelles adaptées ;
5. appliquez la correction nécessaire ;
6. relancez AccessiCode ;
7. vérifiez à nouveau manuellement le résultat.

## Éléments difficiles à automatiser

Une revue humaine peut notamment être nécessaire pour évaluer :

- la pertinence réelle d'un texte alternatif ;
- la compréhension d'un intitulé ;
- la clarté d'une consigne ;
- la pertinence d'un message d'erreur ;
- la cohérence d'une information avec son contexte ;
- l'ordre de navigation au clavier ;
- la visibilité du focus ;
- les changements dynamiques de contenu ;
- le comportement des menus, fenêtres et autres composants interactifs ;
- les contrastes ;
- les informations transmises uniquement par la couleur ;
- le comportement de la page avec différentes technologies d'assistance.

## Tester au clavier

Lorsque cela est pertinent, utilisez uniquement le clavier pour parcourir la page.

Vérifiez notamment que les éléments interactifs peuvent être atteints et utilisés dans un ordre cohérent.

## Technologies d'assistance

Lorsque les moyens disponibles le permettent, complétez l'analyse avec des outils utilisés réellement par les personnes concernées, par exemple un lecteur d'écran.

AccessiCode peut aider à repérer certains problèmes dans le code, mais il ne reproduit pas l'expérience complète d'une personne utilisant une technologie d'assistance.

## Après une correction

Une modification du code peut corriger une anomalie tout en en créant une autre.

Après une correction :

1. relancez l'analyse ;
2. vérifiez le contrôle initial ;
3. examinez les autres résultats ;
4. effectuez une dernière vérification manuelle.


--- FILE: docs/limites.md ---

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
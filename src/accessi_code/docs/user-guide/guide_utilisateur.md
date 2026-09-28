---
title: "Guide utilisateur - AccessiCode"
author: "Équipe AccessiCode"
lang: fr-FR
---

# Guide utilisateur

## 1. À quoi sert AccessiCode ?

AccessiCode aide à repérer des problèmes d’accessibilité dans une page Web.
L’accessibilité désigne la possibilité, pour toutes les personnes, y compris
celles qui utilisent un lecteur d’écran ou une autre aide technique, de
consulter et d’utiliser un site.

L’application analyse le code HTML et des captures du site fourni et présente les résultats de
contrôles du RGAA (Référentiel général d’amélioration de
l’accessibilité). Elle utilise des règles automatiques et, pour certaines
observations, une analyse par intelligence artificielle.

AccessiCode est un outil d’aide au diagnostic. Il ne délivre pas de
certification et ne remplace pas un audit humain complet.

## 2. Avant de commencer

L’application est destinée en priorité aux développeurs, mais aussi aux personnes qui souhaitent obtenir
un premier état des lieux d’une page HTML. Il est utile de disposer de :

- la page HTML à analyser, ou de son contenu à copier-coller ;
- ses images et les fichiers associés si l’analyse est faite à partir d’un
  fichier HTML ;

Le service d’intelligence artificielle doit également être disponible pour les analyses qui en dépendent. Si ce service n’est pas accessible, l’analyse peut échouer ou demander une vérification manuelle.

## 3. Démarrer une analyse HTML

1. Ouvrez AccessiCode.
2. Dans l’onglet **LLM - Audit HTML**, collez le code HTML dans le champ
   **Code HTML à analyser**, ou chargez un fichier `.html`.
3. Si vous utilisez un fichier, joignez aussi les fichiers nécessaires à son
   affichage lorsque l’interface le permet, notamment les images.
4. Cliquez sur **Lancer l’audit LLM**.
5. Attendez l’affichage du tableau des résultats et du rapport détaillé.

Un seul des deux modes d’entrée est nécessaire : le fichier HTML est utilisé en priorité lorsqu’il est fourni ; sinon, le contenu collé est analysé.

### Conseils pour obtenir un résultat exploitable

- Utilisez le HTML réellement livré au navigateur, plutôt qu’un extrait très court qui ne contient pas les éléments à contrôler.
- Vérifiez que le fichier possède bien l’extension `.html`.
- Analysez une page à la fois lorsque vous cherchez à comprendre une
  anomalie précise.

## 4. Analyser une image seule

L’onglet **VLM - Audit d’image** permet d’obtenir une première analyse d’une
image sans fournir toute une page HTML.

1. Ouvrez l’onglet **VLM - Audit d’image**.
2. Chargez une image dans le champ **Image à analyser**.
3. Cliquez sur **Lancer l’audit VLM**.
4. Consultez le tableau et la réponse détaillée.

## 5. Comprendre les résultats

Le tableau présente une ligne par contrôle exécuté :

| Colonne         | Signification                          |
| --------------- | -------------------------------------- |
| Critère         | Identifiant du contrôle RGAA concerné. |
| Statut          | Conclusion automatique du contrôle.    |
| Éléments testés | Nombre d’éléments examinés.            |
| Résumé          | Explication courte du résultat.        |
| Anomalies       | Nombre d’observations à examiner.      |

Le rapport détaillé complète le tableau avec les éléments concernés, les
preuves disponibles et, lorsque c’est possible, une recommandation.

### Les statuts

- **`pass`** : aucune anomalie n’a été détectée par ce contrôle.
- **`fail`** : une ou plusieurs anomalies ont été détectées ; elles doivent
  être corrigées ou confirmées.
- **`needs_review`** : l’outil ne peut pas conclure de façon fiable ; une
  personne doit vérifier le résultat.
- **`not_applicable`** : aucun élément correspondant au contrôle n’a été
  trouvé dans la page analysée.
- **`not_tested`** : le contrôle n’a pas été exécuté.
- **`error`** : une erreur a empêché le contrôle d’aboutir.

Un résultat `pass` signifie seulement que le contrôle automatique n’a pas
trouvé de problème dans les éléments examinés. Il ne signifie pas que la page est entièrement accessible.

## 6. Périmètre des contrôles actuels

L’audit HTML utilise actuellement les contrôles suivants :

| Critère | Sujet contrôlé                                                         |
| ------- | ---------------------------------------------------------------------- |
| 1.1     | Alternatives textuelles des images.                                    |
| 1.7     | Présence et pertinence des descriptions détaillées lorsque nécessaire. |
| 5.1     | Informations associées aux tableaux.                                   |
| 8.1     | Conformité générale du type de document HTML.                          |
| 8.4     | Cohérence de la langue déclarée dans le document.                      |
| 8.5     | Présence d’une langue par défaut.                                      |
| 8.6     | Pertinence du titre de la page.                                        |
| 11.1    | Présence d’une étiquette pour les champs de formulaire.                |

Ces critères regroupent actuellement 12 contrôles internes. La couverture
est partielle : les autres critères RGAA ne sont pas nécessairement analysés.
La liste peut évoluer avec les versions de l’application.

## 7. Vérification humaine indispensable

L’intelligence artificielle peut se tromper, manquer un élément ou interpréter incorrectement son contexte. Toute anomalie importante doit être vérifiée dans la page réelle, avec ses interactions et ses contenus.

Pour chaque résultat `fail` ou `needs_review` :

1. repérez l’élément signalé dans le code ou dans la page affichée ;
2. vérifiez que l’observation correspond bien au contenu visible et au contexte de l’utilisateur ;
3. contrôlez le résultat au clavier et si possible, avec un lecteur d’écran ;
4. appliquez la correction adaptée ;
5. relancez l’analyse, puis validez manuellement la correction.

Une revue humaine doit notamment vérifier :

- la pertinence réelle des textes alternatifs, et pas seulement leur
  présence ;
- la compréhension des intitulés, des consignes et des messages d’erreur ;
- l’ordre de navigation au clavier et la visibilité du focus ;
- les changements de contenu, les menus, les fenêtres et les formulaires ;
- les contrastes, les tailles de texte et les informations transmises par la couleur ;
- le comportement sur différents navigateurs, tailles d’écran et appareils d’assistance.

## 8. Limites de l’outil

AccessiCode présente plusieurs limites à garder à l’esprit :

- il analyse principalement le HTML fourni et ne reproduit pas toutes les interactions d’un site complet ;
- les conclusions produites par l’IA sont probabilistes et peuvent être incomplètes ou incorrectes ;
- une image seule ne fournit pas le contexte éditorial de la page ;
- une ressource absente, un fichier invalide ou un service IA indisponible peut produire une erreur ou un résultat incomplet.

Les résultats doivent donc être utilisés comme une aide pour prioriser les vérifications et les corrections, jamais comme une preuve suffisante de conformité.

## 9. Résoudre les problèmes courants

### « Veuillez coller du HTML ou charger un fichier .html. »

Ajoutez du contenu dans le champ HTML ou chargez un fichier dont le nom se termine par `.html`.

### L’analyse renvoie `error`

Vérifiez que le fichier est lisible, que ses ressources sont disponibles et que le service d’intelligence artificielle est démarré. Relancez ensuite l’analyse avec une page plus simple pour isoler le problème.

### Le tableau est vide

Consultez le rapport détaillé et vérifiez le message affiché. Aucun résultat ne peut être produit si l’entrée est vide, si le fichier n’est pas reconnu ou si l’analyse a échoué avant l’exécution des contrôles.

### Le résultat paraît incorrect

Comparez l’observation avec la page réellement affichée. Notez le contexte, effectuez la vérification humaine décrite au chapitre 7 et ne corrigez pas le code uniquement sur la base d’une suggestion de l’IA.

## 10. Glossaire

- **Accessibilité** : capacité d’un service à être utilisé par des personnes
  ayant des besoins et des moyens d’accès différents.
- **HTML** : langage utilisé pour structurer le contenu d’une page Web.
- **RGAA** : référentiel français proposant des critères et des tests pour évaluer l’accessibilité d’un site.
- **Critère** : règle générale du RGAA, pouvant regrouper plusieurs tests.
- **Audit** : examen structuré destiné à repérer des écarts et à guider les corrections.
- **IA** : intelligence artificielle utilisée ici pour compléter certains contrôles et formuler des observations.

## 11. Résumé du parcours recommandé

1. Préparez le HTML et ses ressources.
2. Lancez l’audit HTML.
3. Traitez d’abord les résultats `fail` et `error`.
4. Vérifiez manuellement les résultats `needs_review`.
5. Corrigez la page et relancez l’analyse.
6. Complétez avec une revue humaine de l’ensemble des parcours et des critères non couverts.

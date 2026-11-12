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
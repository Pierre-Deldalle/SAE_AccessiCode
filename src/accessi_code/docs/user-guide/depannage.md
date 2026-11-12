# Dépannage

Cette page présente quelques problèmes courants pouvant être rencontrés lors de l'utilisation d'AccessiCode.

## « Veuillez coller du HTML ou charger un fichier .html. »

Aucune entrée valide n'a été fournie.

Pour lancer l'analyse :

- collez du code HTML dans le champ prévu ;
- ou chargez un fichier dont le nom se termine par `.html`.

Un seul des deux modes d'entrée est nécessaire.

---

## Mon fichier HTML n'est pas accepté

Vérifiez que :

- le fichier possède bien l'extension `.html` ;
- le fichier est lisible ;
- son contenu correspond bien à une page HTML.

Essayez si nécessaire avec une page HTML plus simple afin de déterminer si le problème provient du fichier.

---

## L'analyse renvoie `error`

Le statut `error` signifie qu'un problème technique a empêché le contrôle d'aboutir.

Vérifiez notamment :

- que le fichier fourni est valide ;
- que les ressources nécessaires sont disponibles ;
- que le service d'intelligence artificielle est accessible lorsque le contrôle en dépend.

Essayez ensuite de relancer l'analyse.

Si l'erreur apparaît uniquement sur une page particulière, testez une page plus simple afin d'isoler l'élément responsable.

---

## Certains contrôles ne sont pas exécutés

Un résultat `not_tested` peut apparaître lorsqu'un contrôle ne peut pas être exécuté.

Cela peut notamment être lié à :

- une information manquante ;
- une ressource indisponible ;
- un service nécessaire non accessible ;
- une condition d'exécution non satisfaite.

Consultez les informations associées au contrôle avant de conclure à une anomalie de la page.

---

## Le tableau des résultats est vide

Vérifiez d'abord les messages affichés par l'application.

Aucun résultat ne peut être produit si :

- l'entrée est vide ;
- le fichier n'est pas reconnu ;
- l'analyse échoue avant l'exécution des contrôles.

Essayez de relancer l'analyse avec une page HTML simple et valide.

---

## Le résultat semble incorrect

AccessiCode peut se tromper, notamment lorsqu'une interprétation du contexte est nécessaire.

Dans ce cas :

1. consultez l'élément concerné dans la page réelle ;
2. comparez le résultat avec le code HTML ;
3. vérifiez manuellement le critère concerné ;
4. ne modifiez pas le code uniquement sur la base d'une suggestion automatique.

Consultez également la page **Vérification humaine**.

---

## Une analyse retourne `needs_review`

Ce statut est normal lorsque l'application ne dispose pas d'assez d'éléments pour produire une conclusion suffisamment fiable.

Il ne s'agit pas nécessairement d'un problème technique.

Effectuez manuellement le contrôle indiqué.

---

## L'analyse d'une image semble manquer de contexte

Une image seule ne permet pas toujours de déterminer son rôle dans une page.

Pour obtenir une analyse plus représentative, utilisez lorsque cela est possible l'image dans le contexte complet de la page HTML.

---

## Le service d'intelligence artificielle n'est pas disponible

Certains contrôles peuvent dépendre du service d'intelligence artificielle.

Si ce service est indisponible, certaines analyses peuvent :

- échouer ;
- ne pas être exécutées ;
- demander une vérification humaine.

Ce problème concerne le fonctionnement d'AccessiCode et ne signifie pas nécessairement que la page analysée présente une anomalie d'accessibilité.
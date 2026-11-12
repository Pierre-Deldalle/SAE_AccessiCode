# Prise en main

Cette page explique comment lancer une première analyse avec AccessiCode.

## Audit d'une page HTML

AccessiCode permet d'analyser le contenu HTML d'une page Web.

### 1. Ouvrir l'audit HTML

Dans l'application, ouvrez l'onglet **LLM - Audit HTML**.

### 2. Fournir le HTML à analyser

Deux méthodes sont disponibles :

- coller directement le code HTML dans le champ **Code HTML à analyser** ;
- charger un fichier possédant l'extension `.html`.

Un seul mode d'entrée est nécessaire.

Lorsqu'un fichier HTML est fourni, celui-ci est utilisé en priorité.

Si l'analyse nécessite des ressources associées à la page, notamment des images, ajoutez-les également lorsque l'interface le permet.

### 3. Lancer l'analyse

Cliquez sur **Lancer l'audit LLM**.

AccessiCode analyse alors la page et exécute les contrôles actuellement disponibles.

Le temps nécessaire dépend du contenu de la page et des contrôles faisant appel aux services d'intelligence artificielle.

### 4. Consulter les résultats

À la fin de l'analyse, AccessiCode affiche :

- un tableau récapitulatif ;
- le statut de chaque contrôle ;
- le nombre d'éléments examinés ;
- les anomalies éventuellement détectées ;
- un rapport plus détaillé lorsque des informations supplémentaires sont disponibles.

Consultez la page **Comprendre les résultats** pour connaître la signification des différents statuts.

---

## Audit d'une image

AccessiCode peut également effectuer une première analyse d'une image indépendamment d'une page HTML complète.

### 1. Ouvrir l'audit d'image

Ouvrez l'onglet **VLM - Audit d'image**.

### 2. Ajouter une image

Chargez l'image dans le champ **Image à analyser**.

### 3. Lancer l'analyse

Cliquez sur **Lancer l'audit VLM**.

### 4. Examiner le résultat

Consultez le tableau et les informations détaillées retournées par AccessiCode.

Une image analysée seule ne fournit cependant pas tout le contexte éditorial de la page dans laquelle elle est normalement utilisée.

---

## Conseils pour obtenir une analyse exploitable

Pour améliorer la qualité des résultats :

- utilisez de préférence le HTML réellement fourni au navigateur ;
- évitez les extraits extrêmement courts qui ne contiennent pas les éléments nécessaires au contrôle ;
- vérifiez que les fichiers HTML possèdent bien l'extension `.html` ;
- fournissez les ressources associées lorsqu'elles sont nécessaires à l'analyse ;
- analysez une page à la fois lorsque vous cherchez à identifier une anomalie précise.

## Service d'intelligence artificielle

Certains contrôles dépendent d'un service d'intelligence artificielle.

Si celui-ci n'est pas disponible, certains contrôles peuvent :

- échouer ;
- ne pas être exécutés ;
- ou demander une vérification humaine.

Un problème concernant le service d'intelligence artificielle ne signifie donc pas nécessairement que la page analysée contient une erreur d'accessibilité.
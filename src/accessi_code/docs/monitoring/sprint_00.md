#### Sprint 0 : Développement d'un prototype du système d'audit fonctionnel de bout en bout
**User Stories :**
- US 0.0.1 : En tant que développeur, je peux déposer des fichiers de code / screenshots dans un dossier qui seront ensuite automatiquement analysés pour réaliser l'audit
DoR : Avoir l'architecture du projet prête pour accueillir les fichiers et savoir où aller les chercher
DoD : Le programme peut lire des fichiers présents dans le dossier et en extraire les informations utiles.

- US 0.0.2 : En tant que développeur, je construit 5 premiers tests à réaliser pour alimenter le moteur de tests du système d'audit, en suivant l'ordre des tests RGAA, qui mixeront algorithmes et IA pour faire leurs vérifications de façon optimisé
DoR : Connaître les étapes des tests qui doivent être faites par algorithme ou IA (d'après le document rédigé à cet effet) et avoir préparer le moteur de tests en connaissant comment il gère les tests
DoD : Les 5 tests sont créés ainsi que leurs tests unitaires respectifs, et tous les tests unitaires passent avec succès

- US 0.0.3 : En tant que développeur, je construit un moteur de tests capable de récupérer toutes les informations nécessaires à l'audit, puis de lancer tous les tests individuellement avant de construire une réponse exploitable à partir des résultats
DoR : Savoir comment les informations vont être récupérées (quel format ?) pour qu'elles soient transmises aux tests et savoir comment la réponse finale sera construite pour être utilisée dans le rapport
DoD : le moteur de tests est capable de transformer les informations obtenus lors de l'analyse des fichiers en réponse complète à utiliser dans le rapport, en lançant tous les tests avec les informations dont ils ont besoin

- US 0.0.4 : En tant que développeur, je peux visualiser les résultats des premiers tests couverts par l'audit dans une interface très simplifiée
DoR : Lecture et analyse des fichiers, moteur de tests et tests doivent être développés avant de pouvoir tester l'interface dans un cas concret (mais il est possible de commencer à la développer avant, même sans maquette finale)
DoD : L'interface peut être ouverte au lancement du programme et est capable d'afficher les résultats des 5 tests, peu importe la forme

**Livrables :**
Coeur du projet fonctionnel de bout en bout, du dépôt des fichiers jusqu'à la réponse dans une interface, sur lequel des fonctionnalités pourront être pluggés plus tard.
5 tests couverts, testés avec des tests unitaires, qui atteignent le niveau 1/3 du système d'audit (dire à l'utilisateur les tests qui ne sont pas validés), qui serviront de modèles aux 253 restants

**Suivi de l'avancement du sprint :**
Plus d'informations sur l'avancement du sprint / des US sont disponibles dans le Trello 
#### Sprint 4 : Évaluation et amélioration de la fiabilité des analyses IA via amélioration automatique des prompts

**User Stories :**

- US 4.0.1 : En tant que développeur, je peux exécuter une batterie de cas d’évaluation sur les analyses IA afin de comparer automatiquement les réponses du modèle avec des résultats attendus définis à l’avance
DoR : Avoir les analyzers IA actuels fonctionnels et connaître les différents types de réponses structurées qu’ils retournent (TitleAnalysis, LanguageAnalysis, ImageRoleAnalysis, etc.)
DoD : Un système d’évaluation peut charger des cas de test, appeler les analyzers concernés, comparer leurs réponses à une vérité attendue et produire un résultat exploitable pour chaque cas.

- US 4.0.2 : En tant que développeur, je peux constituer des jeux de données d’évaluation représentatifs pour les différents usages de l’IA dans AccessiCode
DoR : Avoir identifié les analyses IA actuellement utilisées par les tests RGAA et connaître les cas conformes, non conformes, ambigus et limites à couvrir
DoD : Des datasets annotés manuellement sont créés pour les principales analyses IA, avec pour chaque cas les entrées, la réponse attendue et, si nécessaire, le niveau d’incertitude acceptable.

- US 4.0.3 : En tant que développeur, je peux mesurer la qualité des réponses IA à l’aide de métriques afin d’identifier les erreurs, hallucinations et problèmes de confiance
DoR : Le système d’évaluation et les datasets doivent être disponibles
DoD : L’évaluation produit au minimum des statistiques sur les réponses correctes / incorrectes, les NEEDS_REVIEW, les erreurs avec confiance faible ou élevée, ainsi qu’un rapport permettant d’identifier les cas problématiques.

- US 4.0.4 : En tant que développeur, je peux comparer plusieurs versions d’un même prompt afin de vérifier qu’une modification améliore les résultats sans provoquer de régressions importantes
DoR : Disposer d’un score de référence pour les prompts actuels et d’un jeu d’évaluation suffisamment représentatif
DoD : Plusieurs versions de prompts peuvent être exécutées sur les mêmes cas, leurs résultats sont comparés, et le rapport indique les améliorations ainsi que les cas auparavant corrects devenus incorrects.

- US 4.0.5 : En tant que développeur, je peux séparer les données utilisées pour améliorer les prompts de celles utilisées pour vérifier leur généralisation afin de limiter le surapprentissage
DoR : Disposer d’un nombre suffisant de cas annotés pour pouvoir les répartir en plusieurs ensembles
DoD : Les datasets sont séparés en ensembles d’entraînement / optimisation, validation et test, et les performances finales d’un prompt peuvent être vérifiées sur des cas qui n’ont pas servi directement à son amélioration.

- US 4.0.6 : En tant que développeur, je peux générer automatiquement des propositions de prompts améliorés à partir des erreurs observées, sans modifier directement les prompts utilisés par l’application
DoR : Les métriques, rapports d’erreurs et comparaisons de prompts doivent être fonctionnels ; le système doit disposer d’un moyen d’appeler un modèle capable de proposer une nouvelle version de prompt
DoD : Le programme peut analyser les erreurs d’un prompt, générer une ou plusieurs variantes candidates, les enregistrer séparément et les réévaluer automatiquement sans écraser le prompt actuellement utilisé en production.

- US 4.0.7 : En tant que développeur, je peux sélectionner le meilleur prompt candidat à partir des résultats d’évaluation tout en conservant une validation humaine avant son intégration dans l’application
DoR : Plusieurs prompts candidats doivent pouvoir être évalués sur les mêmes datasets et leurs performances comparées
DoD : Le système classe les prompts selon leurs résultats, affiche les gains et régressions éventuels, recommande le meilleur candidat et laisse le développeur décider manuellement s’il doit remplacer le prompt actuel.

**Livrables :**
- Système d’évaluation dédié aux composants IA d’AccessiCode, indépendant des tests unitaires classiques et capable de mesurer objectivement la qualité des analyses produites par les modèles.
- Jeux de données annotés permettant d’évaluer les principaux usages de l’IA : pertinence des titres, langues, rôle informationnel des images, descriptions détaillées et autres analyses ajoutées pendant le projet.
- Rapports de performance permettant d’identifier les mauvaises réponses, hallucinations, excès ou défauts de confiance et régressions entre plusieurs versions de prompts.
- Système de comparaison de prompts et première version d’un mécanisme d’optimisation automatique proposant des variantes améliorées sans modifier directement les prompts de production.

**Suivi de l'avancement du sprint :**
Plus d'informations sur l'avancement du sprint / des US sont disponibles dans le Trello

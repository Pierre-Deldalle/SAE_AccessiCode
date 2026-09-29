#### Sprint 2 : Développement des critères et leurs tests de niveau 1

**User Stories :**

- US 2.0.1 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 1 : Images.
  DoR : les règles d'accessibilité à tester sont explicitées, les formats d'images acceptés sont validés, les interfaces de l'applications sont validés, et le moteur de tests est fonctionnel
  DoD : l'application détecte correctement si une image respecte ou non les critères clés du RGAA, des tests automatisés couvrent tous les cas

- US 2.0.2 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 2 : Cadres.
  DoR : les règles d'accessibilité à tester sont explicitées, les écrans de restitution des résultats spécifiques aux cadres sont validés, et le moteur de tests est fonctionnel
  DoD : l'application détecte correctement si un cadre respecte ou non les critères clés du RGAA, des test automatisés couvrent tous les cas

- US 2.0.3 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 3 : Couleurs.
  DoR : les règles d'accessibilité à tester sont explicitées, les couleurs de premier plan et d'arrière plan sont validées, et le moteur de tests est fonctionnel
  DoD : l'application calcule et détecte correctement les ratios de constraste selon la formule officielle du RGAA, l'application lève une erreur si le contraste est insuffisant, des tests automatisés couvrent tous les cas

- US 2.0.4 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 4 : Multimédia.
  DoR : les règles d'accessibilité à tester sont explicitées, les balises HTML à analyser ainsi que des extensions de fichiers associées sont validées, et le moteur de tests est fonctionnel
  DoD : l'application détecte et valide correctement la structure des balises multimédias, des tests automatisés couvrent tous les cas

- US 2.0.5 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 5 : Tableaux.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement les balises <table> et lève les alertes appropriées, des tests automatisés couvrent tous les cas

- US 2.0.6 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 6 : Liens.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement les balises <a> et lève les alertes appropriées, des tests automatisés couvrent tous les cas

- US 2.0.7 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 7 : Scripts.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement le DOM généré par les scripts et lève les alertes attendues, l'application remonte les anomalies évidentes de navigation au clavier, des tests automatisés couvrent tous les cas

- US 2.0.8 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 8 : Éléments obligatoires.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement le document et lève les alertes associées aux éléments obligatoires, des tests automatisés couvrent tous les cas

- US 2.0.9 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 9 : Structuration de l'information.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement le DOM et lève les alertes appropriées, des tests automatisés couvrent tous les cas

- US 2.0.10 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 10 : Présentation de l'information.
  DoR : les règles d'accessibilité à tester sont explicitées, la méthode pour simuler et analyser le comportement de la page en mode zoomé (200%) ou sur un écran de 320px de large (sans défilement horizontal obligatoire) est validée, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement le code et le rendu calculé, et lève les alertes appropriées, des tests automatisés couvrent tous les cas

- US 2.0.11 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 11 : Formulaires.
  DoR : les règles d'accessibilité à tester sont explicitées, les formats d'images acceptés sont validés, et les interfaces de l'applications sont validés, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement les formulaires et lève les alertes attendues, des tests automatisés couvrent tous les cas

- US 2.0.12 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 12 : Navigation.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application détecte correctement si une image respecte ou non les critères clés du RGAA, des tests automatisés couvrent tous les cas

- US 2.0.13 : En tant que développeur, mon application est capable de vérifier la conformité RGAA des tests contenus dans le thème 13 : Consultation.
  DoR : les règles d'accessibilité à tester sont explicitées, et le moteur de tests est fonctionnel
  DoD : l'application analyse correctement la page et lève les alertes attendues, des tests automatisés couvrent tous les cas

**Livrables :**
Moteur de tests complet capable de vérifier la conformité RGAA sur l'ensemble des 13 thèmes (du thème 1 : Images au thème 13 : Consultation).
L'application est capable d'analyser le code, le DOM dynamique, les règles de contraste, la structure multimédia et la présentation (responsive / zoom à 200 %).
Ensemble des tests automatisés couvrant tous les cas des 13 thèmes pour garantir le bon fonctionnement de l'application.

**Suivi de l'avancement du sprint :**
Plus d'informations sur l'avancement du sprint / des US sont disponibles dans le Trello

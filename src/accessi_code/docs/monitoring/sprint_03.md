#### Sprint 3 : Développement des critères et leurs tests de niveau 2

**User Stories :**

- US 3.0.1 : Recommandations pour le thème 1 : Images
  DoR : le catalogue des messages d'erreur et des correctifs associés aux alternatives textuelles (alt, aria-label, etc.) est validé.
  DoD : pour chaque anomalie d'image détectée, l'application propose un conseil précis (ex. : « Ajouter un attribut alt="" si l'image est décorative » ou « Décrire le contenu métier dans l'attribut alt »), et les tests automatisés sont à jour.

- US 3.0.2 : Recommandations pour le thème 2 : Cadres
  DoR : les modèles d'intitulés et de corrections pour l'attribut title des balises <iframe> et <frame> sont validés.
  DoD : en cas d'erreur sur un cadre, l'application indique précisément la raison (ex. : « Renseigner un attribut title pertinent décrivant le contenu du cadre »), et les tests automatisés sont à jour.

- US 3.0.3 : Recommandations pour le thème 3 : Couleurs
  DoR : l'algorithme de suggestion de couleurs (calcul de la couleur conforme la plus proche) est validé.
  DoD : pour chaque ratio de contraste insuffisant, l'application indique le ratio actuel, le ratio cible (3:1 ou 4.5:1) et suggère au moins une nuance conforme, et les tests automatisés sont à jour.

- US 3.0.4 : Recommandations pour le thème 4 : Multimédia
  DoR : la typologie des correctifs multimédias (transcription textuelle, sous-titres, audiodescription) est explicitée.
  DoD : en cas d'absence d'alternative ou de piste audio/sous-titre, l'application génère une alerte explicitant l'élément manquant à intégrer dans le lecteur ou la page, et les tests automatisés sont à jour.

- US 3.0.5 : Recommandations pour le thème 5 : Tableaux
  DoR : les règles d'aide à la structuration des tableaux (données vs mise en page, balises <caption>, <th>, attributs scope) sont formalisées.
  DoD : l'application fournit le code HTML correcteur à appliquer selon le type de tableau analysé (ex. : « Remplacer l'élément par une balise <caption> » ou « Associer les en-têtes avec scope="col" »), et les tests automatisés sont à jour.

- US 3.0.6 : Recommandations pour le thème 6 : Liens
  DoR : les règles de correction des intitulés de liens vides, ambigus ou hors contexte sont définies.
  DoD : pour chaque lien non conforme, l'application propose un correctif (ex. : « Renseigner un texte explicite » ou « Ajouter un attribut aria-label »), et les tests automatisés sont à jour.

- US 3.0.7 : Recommandations pour le thème 7 : Scripts
  DoR : la base de guides de correction d'accessibilité JavaScript (gestion du focus, rôles ARIA, événements clavier) est constituée.
  DoD : en cas de problème d'interactivité au clavier ou d'état masqué aux lecteurs d'écran, l'application guide le développeur sur les attributs ARIA ou événements JS à ajouter, et les tests automatisés sont à jour.

- US 3.0.8 : Recommandations pour le thème 8 : Éléments obligatoires
  DoR : le catalogue des corrections pour la structure globale (<!DOCTYPE>, lang, <title>, repères WAI-ARIA) est validé.
  DoD : l'application donne la ligne de code exacte à corriger ou à insérer dans l'entête du document HTML (ex. : « Déclarer l'attribut lang="fr" sur la balise <html> »), et les tests automatisés sont à jour.

- US 3.0.9 : Recommandations pour le thème 9 : Structuration de l'information
  DoR : les schémas de hiérarchie des titres (h1-h6) et l'usage des balises de structure (main, nav, header, footer) sont formalisés.
  DoD : l'application indique l'écart de niveau de titre à corriger ou l'élément sémantique manquant pour structurer la page, et les tests automatisés sont à jour.

- US 3.0.10 : Recommandations pour le thème 10 : Présentation de l'information
  DoR : les préconisations CSS pour le responsive, le zoom à 200 %, les défilements et la prise en compte des styles utilisateur sont validées.
  DoD : en cas d'erreur de mise en page ou de perte d'information au zoom/redimensionnement, l'application signale les propriétés CSS problématiques (overflow: hidden, unités fixes en px, etc.) et propose des alternatives fluides (rem, flex/grid), et les tests automatisés sont à jour.

- US 3.0.11 : Recommandations pour le thème 11 : Formulaires
  DoR : la typologie de conseils pour le rattachement des champs (label, for, id), la gestion des erreurs et la saisie automatique (autocomplete) est finalisée.
  DoD : l'application indique la méthode exacte pour lier chaque champ de saisie à son étiquette ou pour expliciter les messages d'erreur au lecteur d'écran, et les tests automatisés sont à jour.

- US 3.0.12 : Recommandations pour le thème 12 : Navigation
  DoR : les règles concernant les liens d'évitement, les systèmes de navigation multiples et la prise en charge du focus sont définies.
  DoD : l'application détecte les lacunes de navigation et explique comment implémenter un lien d'accès rapide au contenu ou corriger l'ordre de tabulation, et les tests automatisés sont à jour.

- US 3.0.13 : Recommandations pour le thème 13 : Consultation
  DoR : les recommandations relatives à la gestion du temps de session, aux rafraîchissements automatiques, aux documents en téléchargement et aux contenus clignotants sont formalisées.
  DoD : l'application identifie les mécanismes bloquants et fournit les consignes pour permettre le contrôle par l'utilisateur (bouton pause, avertissement, alternative au format ouvert), et les tests automatisés sont à jour.

**Livrables :**
Module d'assistance à la correction : Extension du moteur du Sprint 2 retournant, pour chaque anomalie, un objet structuré comprenant :

- le critère RGAA impacté
- la nature de l'erreur
- le plan d'action / le bout de code suggéré pour la résoudre
  Interface / Restitution enrichie : Mise à jour des affichages pour présenter la recommandation en face de chaque erreur.
  Suite de tests automatisés : Vérification que le moteur génère les bonnes suggestions pour chaque cas de non-conformité sur l'ensemble des 13 thèmes.

**Suivi de l'avancement du sprint :**
Plus d'informations sur l'avancement du sprint / des US sont disponibles dans le Trello

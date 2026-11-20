# Site de démonstration non conforme

Petit site qui **accumule volontairement des erreurs d'accessibilité**.
Il sert à montrer qu'AccessiCode les détecte. Chaque erreur est commentée dans `index.html`.

## Utilisation

Importer tous les fichiers de ce dossier dans AccessiCode, cocher toutes les thématiques
et lancer l'audit.

## Résultat attendu

Toutes les thématiques 1 à 12 apparaissent en **rouge** (score de 0 à 35 %).
La thématique 13 (Consultation) n'a pas encore de test automatisé.

## Erreurs illustrées

| Thématique | Exemples d'erreurs |
|---|---|
| 1. Images | Images sans `alt`, lien image sans intitulé, zone cliquable sans alternative, image décorative avec `title` |
| 2. Cadres | `iframe` sans titre ou avec un titre vide |
| 3. Couleurs | Information donnée par la couleur seule, textes et composants peu contrastés |
| 4. Multimédia | Son lancé automatiquement, sous-titres en `kind="subtitles"`, PDF sans alternative |
| 5. Tableaux | Tableau complexe sans résumé, `scope` incorrects, tableau de mise en forme avec `th` |
| 6. Liens | Lien vide, nom accessible différent du texte visible, « Cliquez ici » |
| 7. Scripts | `div` cliquables sans rôle, messages de statut et d'erreur non annoncés |
| 8. Éléments obligatoires | Pas de DOCTYPE, pas de langue, titre vide, code de langue invalide, `id` en double |
| 9. Structuration | Titres vides, niveaux sautés, fausse liste avec des tirets, citations vides |
| 10. Présentation | `<font>`, `<center>`, `align`, mots espacés, information en CSS, focus invisible, largeur fixe |
| 11. Formulaires | Champs sans étiquette, étiquette mal reliée, `autocomplete` invalide, bouton vide |
| 12. Navigation | Pas de lien d'évitement, navigation différente sur `services.html`, `tabindex` positif |

Voir aussi : `../site_conforme` (le contraire) et `../site_demo_rgaa` (tous les tests).

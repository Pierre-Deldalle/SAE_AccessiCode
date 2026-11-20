# Site de démonstration conforme

Petit site qui **respecte les règles d'accessibilité** contrôlées par AccessiCode.
Il sert à montrer à quoi ressemblent les résultats d'une page bien construite.

## Utilisation

Importer tous les fichiers de ce dossier dans AccessiCode, cocher toutes les thématiques
et lancer l'audit.

## Résultat attendu

| Thématique | Résultat |
|---|---|
| 1, 2, 4 à 12 | **100 %** (cercle vert) |
| 3. Couleurs | **À vérifier** (cercle cyan) : les contrastes mesurés sont bons, mais l'outil ne peut pas garantir qu'il a analysé tout le rendu et demande donc une vérification humaine |
| 13. Consultation | Pas de test automatisé pour l'instant |

Beaucoup de critères restent « à vérifier » : AccessiCode ne conclut jamais à la conformité
quand une vérification humaine est nécessaire (pertinence d'une alternative, d'un titre…).
Le pourcentage ne porte que sur les critères qu'il a pu trancher.

## Bonnes pratiques illustrées

- Images avec alternatives pertinentes, image décorative masquée, légende, description détaillée.
- Tableau complexe : en-têtes fusionnés associés aux cellules par `headers` / `id`.
- Formulaires : étiquettes visibles, regroupements `fieldset` / `legend`, messages d'aide et d'erreur.
- Médias : transcriptions, piste de sous-titres `kind="captions"`, alternative au document PDF.
- Messages de statut : `role="status"`, `role="alert"`, `role="log"`, `role="progressbar"`.
- Navigation identique sur les trois pages, lien d'évitement, recherche et plan du site.
- Feuille de style avec des contrastes suffisants et une prise de focus visible.

Voir aussi : `../site_non_conforme` (le contraire) et `../site_demo_rgaa` (tous les tests).

# Site de démonstration RGAA

Ce dossier est un petit site web créé pour **passer en revue tous les tests RGAA d'AccessiCode**.
Chaque thématique y est illustrée par des cas **conformes** et des cas **volontairement non conformes**,
afin de vérifier que l'application détecte bien les deux.

> Ce site n'est pas un modèle d'accessibilité : il contient exprès des erreurs.

Comme cas conformes et non conformes sont mélangés sur la même page, les scores obtenus sont
bas : un critère est non conforme dès qu'un seul de ses tests échoue. Pour une démonstration
plus parlante, voir aussi :

- `../site_conforme` : uniquement des bonnes pratiques (scores à 100 %) ;
- `../site_non_conforme` : uniquement des erreurs (scores en rouge).

## Utilisation

**Dans l'application** : lancer AccessiCode, importer **tous les fichiers de ce dossier**
(`index.html`, les autres pages, `style.css` et les images), cocher toutes les thématiques,
puis lancer l'audit.

**En ligne de commande** (sans interface), depuis la racine du projet :

```powershell
$env:PYTHONPATH = "src"
python -m scripts.debug_rgaa --site site_demo_rgaa          # avec l'IA
python -m scripts.debug_rgaa --site site_demo_rgaa --no-ai  # sans Ollama
```

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `index.html` | Page principale : une section par thématique RGAA (c'est elle qui est auditée) |
| `plan-du-site.html`, `a-propos.html` | Pages annexes avec la même navigation, utilisées par les critères qui comparent plusieurs pages (11.3.2 et thématique 12) |
| `style.css` | Couleurs, contrastes et bordures des champs (thématiques 3 et 10) |
| `logo.png`, `accessibilite.svg` | Images utilisées par les exemples |
| `description.txt` | Description détaillée du logo (attribut `longdesc`, critère 1.6) |
| `sous-titres.vtt` | Piste de sous-titres (critère 4.3) |

Les fichiers audio et vidéo cités dans la page (`media/…`) ne sont volontairement pas fournis :
AccessiCode analyse le code HTML des médias, pas leur contenu.

## Sections de la page principale

| Section | Thématiques couvertes |
|---|---|
| Présentation, Résultats, Contact, Contenu intégré | 1 (images de base), 2 (cadres), 5 (tableau complexe), 8 (éléments obligatoires), 11 (formulaires), 12 (navigation) |
| Thématique 1 — Images (compléments) | `object`, `embed`, `canvas`, `svg`, images décoratives, CAPTCHA, légendes, descriptions détaillées |
| Thématique 3 — Couleurs | Information par la couleur, contrastes du texte et des composants |
| Thématique 4 — Multimédia | Audio, vidéo, sous-titres, médias non temporels, sons automatiques |
| Thématique 5 — Tableaux | `headers`/`id`, `scope`, rôles ARIA, tableaux de mise en forme |
| Thématique 6 — Liens | Liens textuels, images, composites, SVG, sans intitulé |
| Thématique 7 — Scripts | Composants scriptés, alternatives, messages de statut |
| Thématique 9 — Structuration | Titres, listes, citations |
| Thématique 10 — Présentation | Contenus générés par CSS, contenus masqués, zoom |
| Exemples non conformes | Erreurs regroupées de plusieurs thématiques |

## Couverture mesurée

Audit complet avec l'IA (novembre 2026) : **236 tests applicables sur 237**.

| Thématique | Tests | Applicables |
|---|---|---|
| 1. Images | 59 | 59 |
| 2. Cadres | 2 | 2 |
| 3. Couleurs | 15 | 15 |
| 4. Multimédia | 25 | 25 |
| 5. Tableaux | 15 | 15 |
| 6. Liens | 6 | 6 |
| 7. Scripts | 11 | 10 |
| 8. Éléments obligatoires | 13 | 13 |
| 9. Structuration | 9 | 9 |
| 10. Présentation | 31 | 31 |
| 11. Formulaires | 32 | 32 |
| 12. Navigation | 19 | 19 |
| 13. Consultation | — | aucun test automatisé pour l'instant |

Le seul test non applicable est le **7.2.2** : il demande de suivre les changements du DOM
pendant l'exécution des scripts, ce qui n'est pas encore implémenté dans AccessiCode.

Sans IA (Ollama indisponible), les tests 8.2.1, 8.7.1, 8.8.1 et 8.9.1 sont « non testés ».

## Origine

Ce site réunit les anciens jeux de test du projet (`perfect_site`, `worst_site`, `color_site`,
`multimedia_site`, `script_site`, `structure_site`, `presentation_site`, `full_site`,
`theme_06_links.html`), complétés par des exemples pour les tests qu'aucun d'eux ne déclenchait.

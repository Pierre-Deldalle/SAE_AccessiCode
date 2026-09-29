# Conventions de développement — AccessiCode

Ce document décrit la méthode à suivre pour ajouter ou modifier un test RGAA dans AccessiCode.

L’objectif est de garder une architecture homogène entre tous les développeurs du projet, même lorsque les tests sont développés par plusieurs personnes ou avec l’aide d’une IA.

> Avant d’implémenter un test, vérifier son fonctionnement exact dans la documentation officielle du RGAA. Ne jamais inventer une règle ou fusionner plusieurs tests RGAA parce que cela semble plus simple.

---

## 1. Architecture générale

Un audit AccessiCode suit ce pipeline :

```text
Fichiers fournis
      ↓
AuditContext
      ↓
TestRegistry
      ↓
TestRunner
      ↓
Tests RGAA
      ↓
Analyse déterministe / services IA
      ↓
TestResult
      ↓
Agrégation
      ↓
AuditResult
```

Un test RGAA ne doit donc pas dépendre directement :

- de l’interface ;
- de Gradio ;
- de la manière dont les fichiers ont été importés ;
- d’Ollama ou d’un fournisseur IA particulier ;
- du fonctionnement interne du moteur.

Il reçoit principalement :

```python
AuditContext
AuditServices
```

et retourne toujours un :

```python
TestResult
```

---

# 2. Où ajouter un test RGAA ?

Les tests sont placés dans :

```text
src/accessi_code/rgaa/tests/
```

Ils sont organisés par thème RGAA :

```text
rgaa/tests/
├── theme_01_images/
├── theme_05_tables/
├── theme_08_mandatory/
└── theme_11_forms/
```

Pour un nouveau thème :

```text
theme_XX_nom_du_theme/
```

Exemple :

```text
theme_03_colors/
```

## Un fichier par critère

Tous les tests appartenant au même critère doivent être regroupés dans un seul fichier.

Exemple :

```text
criterion_1_1.py
```

contient :

```python
Test111
Test112
Test113
```

Ne pas créer :

```text
criterion_1_1_1.py
criterion_1_1_2.py
criterion_1_1_3.py
```

Convention de nommage :

```text
Critère 1.1   → criterion_1_1.py
Test 1.1.1    → Test111

Critère 8.6   → criterion_8_6.py
Test 8.6.1    → Test861

Critère 11.1  → criterion_11_1.py
Test 11.1.1   → Test1111
```

---

# 3. Structure minimale d’un test

Tous les tests héritent de :

```python
RGAATest
```

Exemple :

```python
from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class TestXYZ(RGAATest):
    test_id = "X.Y.Z"
    criterion_id = "X.Y"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        ...

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.PASS,
            summary="...",
        )
```

Chaque test doit définir :

```python
test_id
criterion_id
required_capabilities
```

Il peut aussi définir :

```python
optional_capabilities
```

---

# 4. Utiliser `AuditContext`

Un test ne reçoit pas directement une chaîne HTML.

Les données de l’audit sont déjà disponibles dans :

```python
context
```

Exemples :

```python
context.html_source
context.dom
context.html_path
context.image_files
context.screenshots
```

Si le DOM existe déjà, ne pas reparcourir tout le pipeline ou refaire :

```python
BeautifulSoup(context.html_source, ...)
```

Utiliser directement :

```python
context.dom
```

---

# 5. Déclarer les capacités nécessaires

Les capacités disponibles sont définies dans :

```text
src/accessi_code/models/capabilities.py
```

Exemples :

```python
Capability.SOURCE_FILES
Capability.HTML_SOURCE
Capability.DOM
Capability.IMAGES
Capability.SCREENSHOT
Capability.COMPUTED_STYLES
Capability.BROWSER_INTERACTION
Capability.ACCESSIBILITY_TREE
```

Une donnée indispensable doit être placée dans :

```python
required_capabilities
```

Exemple :

```python
required_capabilities = frozenset(
    {
        Capability.DOM,
    }
)
```

Une donnée utile mais non obligatoire peut être placée dans :

```python
optional_capabilities
```

Le `TestRunner` gère automatiquement les capacités obligatoires manquantes et retourne alors :

```text
NOT_TESTED
```

Il ne faut pas réimplémenter cette logique dans chaque test.

---

# 6. Séparer logique RGAA et logique réutilisable

Les fichiers de :

```text
rgaa/tests/
```

doivent principalement contenir :

```text
sélection des éléments concernés
        ↓
application de la règle RGAA
        ↓
construction du TestResult
```

Une logique technique pouvant être réutilisée par plusieurs critères doit être placée dans :

```text
src/accessi_code/analysis/
```

Exemples existants :

```text
analysis/dom.py
analysis/images.py
analysis/page.py
analysis/tables.py
```

Si nécessaire, créer un nouveau module :

```text
analysis/links.py
analysis/colors.py
analysis/headings.py
analysis/media.py
```

Les fonctions de `analysis/` doivent autant que possible :

- être déterministes ;
- être réutilisables ;
- ne pas dépendre directement d’un numéro de test RGAA ;
- ne pas décider elles-mêmes du statut `PASS` ou `FAIL`.

La décision finale appartient au test RGAA.

---

# 7. Utilisation de l’IA

Toujours privilégier une vérification déterministe lorsque cela est possible.

Ordre recommandé :

```text
HTML / DOM / attributs / structure
                ↓
IA uniquement si une interprétation est nécessaire
```

Un test RGAA ne doit jamais instancier directement :

```python
OllamaLLM(...)
OllamaVLM(...)
```

Il récupère les services via :

```python
services
```

Exemple :

```python
analyzer = (
    getattr(
        services,
        "image_analyzer",
        None,
    )
    if services is not None
    else None
)
```

Cela permet de changer plus tard de modèle ou de fournisseur IA sans modifier les tests RGAA.

---

# 8. Ajouter une nouvelle analyse IA

Si un test nécessite une analyse IA qui n’existe pas encore, plusieurs fichiers peuvent être concernés :

```text
src/accessi_code/ai/schemas.py
src/accessi_code/ai/prompts/
src/accessi_code/ai/analyzers/
src/accessi_code/service/audit_services.py
src/accessi_code/service/default_services.py
```

Répartition :

```text
schemas.py
→ structure de la réponse IA

prompts/
→ instructions envoyées au modèle

analyzers/
→ appel au modèle + parsing de sa réponse

AuditServices
→ mise à disposition de l’analyzer aux tests RGAA
```

Le test RGAA ne doit pas parser lui-même le JSON retourné par l’IA.

---

# 9. Gestion de la confiance IA

Une réponse IA avec :

```python
confidence == "low"
```

ne doit jamais produire directement :

```text
PASS
```

ou :

```text
FAIL
```

Elle doit produire :

```text
NEEDS_REVIEW
```

Même si le modèle retourne :

```python
relevant = True
```

ou :

```python
relevant = False
```

Principe :

```text
Réponse IA
    ↓
Confiance faible ?
    ├── oui → NEEDS_REVIEW
    └── non
         ↓
Conclusion disponible ?
    ├── non → NEEDS_REVIEW
    └── oui → PASS / FAIL selon la règle RGAA
```

Une incertitude IA ne doit jamais être transformée en certitude RGAA.

---

# 10. Statuts disponibles

Les tests utilisent les statuts définis dans :

```python
TestStatus
```

## `PASS`

Le test est applicable et conforme.

## `FAIL`

Une non-conformité certaine a été détectée.

## `NOT_APPLICABLE`

Aucun élément de la page n’entre dans le périmètre du test.

Exemple :

```text
Aucun tableau présent pour un test concernant les tableaux.
```

## `NOT_TESTED`

Le test aurait dû être exécuté mais une donnée obligatoire manque.

Ce statut est généralement produit automatiquement par le `TestRunner`.

## `NEEDS_REVIEW`

Les données existent mais AccessiCode ne peut pas conclure suffisamment fiablement.

Exemples :

- service IA absent alors qu’il est nécessaire ;
- confiance IA faible ;
- réponse indéterminée ;
- vérification humaine nécessaire.

## `ERROR`

Une erreur technique a empêché l’exécution normale du test.

Exemples :

- exception dans un analyzer ;
- réponse IA invalide ;
- ressource impossible à traiter.

---

# 11. Priorité des résultats

Lorsqu’un test traite plusieurs éléments, utiliser la priorité suivante :

```text
FAIL
>
ERROR
>
NEEDS_REVIEW
>
NOT_TESTED
>
PASS
>
NOT_APPLICABLE
```

Exemple :

```text
Image 1 → PASS
Image 2 → FAIL
Image 3 → NEEDS_REVIEW
```

Résultat global :

```text
FAIL
```

Une non-conformité certaine ne doit pas être masquée par une incertitude.

---

# 12. Findings, metadata et tested_elements

## `Finding`

Une anomalie ou une vérification manuelle doit être expliquée avec un `Finding`.

Exemple :

```python
Finding(
    element="img[index=2]",
    message="Le rôle informationnel reste incertain.",
    recommendation=(
        "Vérifier manuellement le rôle de l'image."
    ),
    evidence={
        "confidence": analysis.confidence,
    },
)
```

Un finding doit idéalement indiquer :

- l’élément concerné ;
- le problème ;
- une recommandation éventuelle ;
- les preuves utiles.

## `metadata`

Les informations générales utiles au rapport ou au debug peuvent être placées dans :

```python
metadata
```

Exemple :

```python
metadata={
    "candidate_images": 4,
    "informative_images": 2,
    "needs_review": 1,
}
```

Les metadata doivent rester sérialisables en JSON.

## `tested_elements`

`tested_elements` représente le nombre d’éléments réellement concernés par le test.

Exemple :

```text
4 images détectées
2 réellement porteuses d'information
```

Alors :

```python
tested_elements = 2
```

---

# 13. Enregistrer un nouveau test

Tout nouveau test doit être ajouté dans :

```text
src/accessi_code/rgaa/default_registry.py
```

Exemple :

```python
from accessi_code.rgaa.tests.theme_01_images.criterion_1_3 import (
    Test131,
)
```

puis :

```python
TestRegistry(
    [
        ...
        Test131(),
        ...
    ]
)
```

Conserver autant que possible l’ordre officiel des tests RGAA.

L’ajout au registre doit suffire pour que le test soit exécuté par l’application.

Il ne doit pas être nécessaire de modifier l’interface ou le moteur.

---

# 14. Tests unitaires

Chaque critère doit avoir son fichier de tests unitaires correspondant.

Exemple :

```text
src/accessi_code/rgaa/tests/
└── theme_01_images/
    └── criterion_1_3.py

tests/unit/rgaa/
└── theme_01_images/
    └── test_criterion_1_3.py
```

Comme pour le code source :

```text
un fichier de tests unitaires par critère
```

et non un fichier par sous-test.

Les helpers ajoutés dans :

```text
analysis/
```

doivent être testés séparément dans :

```text
tests/unit/analysis/
```

---

# 15. Cas à couvrir dans les tests unitaires

Selon le test, prévoir au minimum :

```text
PASS
FAIL
NOT_APPLICABLE
```

Pour un test utilisant l’IA :

```text
réponse positive fiable
réponse négative fiable
confidence="low" → NEEDS_REVIEW
conclusion=None → NEEDS_REVIEW
service IA absent → NEEDS_REVIEW
exception IA → ERROR
```

Pour les tests traitant plusieurs éléments, vérifier également les résultats mixtes :

```text
plusieurs PASS
PASS + FAIL
FAIL + NEEDS_REVIEW
```

Tester aussi les cas limites utiles au critère :

```text
attribut vide
référence inexistante
ID dupliqué
contenu vide
plusieurs mécanismes présents
élément hors périmètre
```

---

# 16. Ne pas utiliser une vraie IA dans les tests unitaires

Les tests unitaires doivent fonctionner :

- sans réseau ;
- sans Ollama ;
- sans modèle installé ;
- de manière reproductible.

Les réponses IA doivent être simulées, par exemple avec :

```python
AsyncMock
```

Les vrais modèles sont évalués séparément avec les scripts de debug ou avec de futurs tests dédiés à la qualité des prompts.

---

# 17. Fichiers qui ne doivent normalement pas être modifiés

Ajouter un nouveau critère ne doit normalement pas nécessiter de modifier :

```text
rgaa/runner.py
rgaa/registry.py
rgaa/aggregation.py
service/audit_service.py
ui_gradio.py
```

Si l’ajout d’un test oblige à écrire quelque chose comme :

```python
if test_id == "X.Y.Z":
```

dans le moteur ou dans l’interface, il faut probablement revoir l’architecture de l’implémentation.

La logique spécifique doit rester dans :

```text
rgaa/tests/
analysis/
ai/
```

---

# 18. Process d’ajout d’un test RGAA

## Étape 1 — Lire le RGAA officiel

Identifier précisément :

```text
test_id
criterion_id
éléments concernés
règles exactes
mécanismes autorisés
données nécessaires
```

## Étape 2 — Déterminer les capacités nécessaires

Exemples :

```python
Capability.DOM
Capability.HTML_SOURCE
Capability.IMAGES
```

Les déclarer dans `required_capabilities` ou `optional_capabilities`.

## Étape 3 — Vérifier les helpers existants

Regarder notamment :

```text
analysis/dom.py
analysis/images.py
analysis/page.py
analysis/tables.py
```

Ne pas dupliquer une logique déjà existante.

## Étape 4 — Ajouter les helpers manquants

Si nécessaire, compléter ou créer un fichier dans :

```text
analysis/
```

et ajouter ses tests dans :

```text
tests/unit/analysis/
```

## Étape 5 — Déterminer si l’IA est nécessaire

Si la règle peut être vérifiée de manière déterministe, ne pas utiliser l’IA.

Sinon, utiliser ou créer un analyzer adapté.

## Étape 6 — Ajouter l’analyse IA si nécessaire

Éventuellement modifier :

```text
ai/schemas.py
ai/prompts/
ai/analyzers/
service/audit_services.py
service/default_services.py
```

## Étape 7 — Implémenter le test RGAA

Dans :

```text
rgaa/tests/theme_XX_<theme>/criterion_X_Y.py
```

## Étape 8 — Ajouter les tests unitaires

Dans :

```text
tests/unit/rgaa/theme_XX_<theme>/test_criterion_X_Y.py
```

## Étape 9 — Ajouter le test au registre

Modifier :

```text
rgaa/default_registry.py
```

## Étape 10 — Valider

Lancer :

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Tout doit passer avant fusion.

---

# 19. Validation de bout en bout

Si nécessaire, ajouter un exemple représentatif dans :

```text
test_files/
```

Les scripts de debug permettent de vérifier plusieurs niveaux :

```text
debug_context.py
→ création du AuditContext

debug_engine.py
→ fonctionnement du moteur

debug_rgaa.py
→ vrais tests RGAA + services IA
```

Les tests unitaires vérifient la logique.

Les scripts de debug vérifient l’intégration de bout en bout.

---

# 20. Checklist avant fusion

Avant de considérer un test terminé :

- [ ] Le comportement a été vérifié dans le RGAA officiel.
- [ ] Le test est dans le bon thème.
- [ ] Le fichier correspond au bon critère.
- [ ] La classe hérite de `RGAATest`.
- [ ] `test_id` et `criterion_id` sont corrects.
- [ ] Les capabilities nécessaires sont déclarées.
- [ ] La logique déterministe est privilégiée avant l’IA.
- [ ] Aucun client IA n’est instancié directement dans le test.
- [ ] Une confiance IA faible produit `NEEDS_REVIEW`.
- [ ] Une erreur technique produit `ERROR`.
- [ ] Les helpers réutilisables sont placés dans `analysis/`.
- [ ] Le test est ajouté dans `default_registry.py`.
- [ ] Les tests unitaires couvrent les principales branches.
- [ ] `ruff check` passe.
- [ ] `ruff format --check` passe.
- [ ] `pytest` passe.

---

# 21. Principe à retenir

Un test RGAA doit idéalement suivre ce fonctionnement :

```text
AuditContext
      ↓
sélection des éléments concernés
      ↓
analyse déterministe
      ↓
analyse IA uniquement si nécessaire
      ↓
décision RGAA
      ↓
TestResult
```

Le moteur, l’interface et le fournisseur d’IA ne doivent pas connaître les détails internes du test.

Si l’ajout d’un nouveau critère oblige à modifier de nombreuses parties non liées de l’application, vérifier d’abord si la logique a été placée au bon niveau de l’architecture.
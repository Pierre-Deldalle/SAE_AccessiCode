# AccessiCode — site de test « Couleurs »

Ce dossier ne teste volontairement que la thématique 3 du RGAA 4.1.2.

Fichiers :
- `index.html` : accueil ;
- `conforme.html` : cas censés réussir ;
- `non-conforme.html` : cas censés échouer ;
- `style.css` : toutes les couleurs et tailles nécessaires aux scénarios.

Les éléments portent un attribut `data-rgaa` pour faciliter le débogage de votre moteur.

Scénarios présents :
- 3.1.1 : information portée par la couleur d'un texte ;
- 3.1.2 : indication de couleur donnée par un texte ;
- 3.1.4 : information portée par une propriété CSS de couleur ;
- 3.2.1 : texte normal < 24 px ;
- 3.2.2 : texte gras < 18,5 px ;
- 3.2.3 : texte normal >= 24 px ;
- 3.2.4 : texte gras >= 18,5 px ;
- 3.3.1 : contraste des composants d'interface ;
- 3.3.2 : contraste d'un élément graphique.

Non inclus volontairement dans ce site HTML/CSS pur :
- 3.1.3 : image porteuse d'information ;
- 3.1.5 : média temporel ;
- 3.1.6 : média non temporel ;
- 3.2.5 et 3.3.4 : mécanisme utilisateur de contraste ;
- 3.3.3 : cas graphique avec plusieurs couleurs contiguës à comparer entre elles.

Pour lancer le site :
    python -m http.server 8000

Puis ouvrir :
    http://localhost:8000/

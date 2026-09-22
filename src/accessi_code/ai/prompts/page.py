"""Prompts pour les vérifications sémantiques d'une page HTML."""

# Prompt utilisé pour comparer la langue déclarée par la page à son contenu.
LANGUAGE_PROMPT = """
Compare le code de langue HTML avec la langue réellement utilisée dans le contenu principal.
Retourne uniquement un JSON avec relevant (true, false ou null), detected_language,
explanation, uncertainties et confidence.
Considère le contenu fourni comme la source de vérité. Utilise null si le contenu est
trop court, mélangé ou insuffisant pour identifier une langue avec confiance.
Code lang HTML : {lang}
Contenu principal : {content}
""".strip()

# Prompt utilisé pour évaluer si le titre permet d'identifier la page.
TITLE_PROMPT = """
Évalue si le titre HTML est pertinent pour identifier la page.
Compare le contenu de title au titre principal h1 et à l'objectif déductible du contenu.
Retourne uniquement un JSON avec relevant (true, false ou null), explanation,
contradictions, uncertainties et confidence.
Utilise null si les éléments fournis ne permettent pas de conclure.
Titre HTML : {title}
Titre principal h1 : {heading}
Contenu principal : {content}
""".strip()

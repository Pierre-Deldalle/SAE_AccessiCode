"""Garde-fou contre les explications IA manifestement dégénérées.

Ne transforme jamais une réponse incohérente en conformité : elle devient
une preuve insuffisante (confidence='low').
"""
from __future__ import annotations

import re


def clean_explanation(value: object, max_chars: int = 450) -> tuple[str, bool]:
    text = " ".join(str(value or "").split())
    if not text:
        return "Analyse IA sans explication exploitable.", True
    words = re.findall(r"[\w-]+", text.casefold())
    # Détecter les boucles de 1 à 4 mots répétées au moins 4 fois.
    repeated = any(
        len(words) >= length * 4 and any(
            words[start:start + length] * 4 == words[start:start + length * 4]
            for start in range(len(words) - length * 4 + 1)
        ) for length in range(1, 5)
    )
    if repeated or len(text) > 1800:
        return "Réponse IA répétitive ou incohérente : vérification nécessaire.", True
    return text[:max_chars], False

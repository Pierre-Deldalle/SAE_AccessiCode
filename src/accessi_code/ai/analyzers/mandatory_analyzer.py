from __future__ import annotations

from typing import Any
import re

from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.json_utils import parse_ai_json


def _is_likely_hallucinated_explanation(explanation: str) -> bool:
    """
    Detect if an explanation is likely hallucinated based on common patterns.

    Hallucinated explanations often contain:
    - Mixed language fragments without clear structure
    - Nonsensical phrases like "l'art de l'auditeur-spitécialisé"
    - Inappropriate technical jargon like "amps; text nodes"
    - Excessive repetition or lack of coherence
    - Strange technical patterns like "docs-lang-01" repeated
    """
    if not explanation or not isinstance(explanation, str):
        return False

    explanation_lower = explanation.lower()

    # Check for known hallucination patterns
    hallucination_patterns = [
        r'l\'art de l\'auditeur[-]?sp[ée]cialis[ée]',
        r'visible text/amps;? text nodes?',
        r'main de la page.*titres?.*paragraphs?-in-violation',
        r"missing[' ’]document language mismatch",
        r'\(en/fr\) mismatch-document lang=\'en\'',
        r'docs-lang-\d+.*docs-lang-\d+.*docs-lang-\d+',  # Repeated docs-lang patterns
        r'single-language.*document\.\w+',  # strange single-language patterns
    ]

    for pattern in hallucination_patterns:
        if re.search(pattern, explanation_lower, re.IGNORECASE):
            return True

    # Check for excessive language mixing without structure
    # Count French vs English indicators (very rough heuristic)
    french_indicators = ['le', 'la', 'les', 'de', 'des', 'du', 'et', 'est', 'une', 'un', 'pour', 'dans', 'qui', 'que', 'quoi']
    english_indicators = ['the', 'a', 'an', 'of', 'and', 'is', 'are', 'was', 'were', 'for', 'in', 'that', 'this', 'what']

    words = re.findall(r'\b[a-zÀ-ÿ]+\b', explanation_lower)
    if len(words) > 10:  # Only check for substantial explanations
        french_count = sum(1 for word in words if word in french_indicators)
        english_count = sum(1 for word in words if word in english_indicators)
        total_indicators = french_count + english_count

        # If we have significant indicators from both languages but very few total words recognized,
        # it might be hallucinated mixing
        if total_indicators > 5 and len(words) > 0 and (french_count > 0 and english_count > 0):
            # Check if the ratio is suspicious (could indicate random mixing)
            ratio = min(french_count, english_count) / max(french_count, english_count) if max(french_count, english_count) > 0 else 0
            if ratio > 0.3:  # Both languages present in significant amounts
                # Additional check: if there are many technical terms mixed in strangely
                technical_terms = ['amps', 'nodes', 'elements', 'attributes', 'tags', 'html', 'dom', 'svg', 'docs', 'language', 'single']
                technical_count = sum(1 for word in words if any(term in word for term in technical_terms))
                if technical_count > len(words) * 0.15:  # More than 15% technical terms
                    return True

    return False


def _clean_hallucinated_explanation(explanation: str) -> str:
    """
    Clean or replace a hallucinated explanation with a safe alternative.
    """
    if not _is_likely_hallucinated_explanation(explanation):
        return explanation

    # Return a generic, safe explanation instead of hallucinated content
    return "Analyse automatique effectuée - voir les findings pour les détails spécifiques."


class OllamaMandatoryAnalyzer:
    """Analyseur Gemma pour les contrôles textuels du thème RGAA 8."""

    def __init__(self, llm: OllamaLLM) -> None:
        self.llm = llm

    async def _analyze(self, instruction: str, html_source: str | None) -> dict[str, Any]:
        source = html_source or ""
        prompt = f"""
Tu es un auditeur RGAA spécialisé dans le thème 8.
Analyse exclusivement le code HTML fourni et ne devine pas ce qui n'est pas visible.
Retourne uniquement un objet JSON valide, sans Markdown, avec les champs demandés.

{instruction}

Code HTML :
{source}
""".strip()
        response = await self.llm.generate(
            prompt,
            format="json",
            max_tokens=1200,
            temperature=0,
        )
        data = parse_ai_json(response)
        if not isinstance(data, dict):
            raise ValueError("La réponse du modèle doit être un objet JSON.")
        return data

    async def validate_html(self, html_source: str | None) -> Any:
        data = await self._analyze(
            """
Détermine si le HTML est syntaxiquement valide.
Réponds avec {"is_valid": boolean, "errors": [{"line": number, "message": string}]}.
""",
            html_source,
        )
        return _ValidationResult(
            is_valid=_bool(data, "is_valid"),
            errors=_errors(data.get("errors")),
        )

    async def analyze_language_changes(self, dom: Any, html_source: str | None) -> Any:
        data = await self._analyze(
            """
Repère les textes dans une langue différente de la langue par défaut qui
n'ont pas d'attribut lang approprié sur eux-mêmes ou un parent.
Réponds avec {"has_violations": boolean, "confidence": "low|medium|high",
"total_elements_checked": number, "explanation": string, "findings": [...],
"metadata": {}}.
Chaque finding doit contenir element, message et recommendation.
Règle obligatoire :
Si has_errors vaut true, findings ne doit jamais
être vide.

Pour chaque erreur, indique :
- element : la balise et son attribut lang
- message : le texte concerné, la langue du texte
  et le code de langue déclaré
- recommendation : la correction exacte à effectuer
- evidence : le texte HTML justifiant le constat

Si tu ne peux pas identifier précisément
l'élément et le problème, utilise confidence="low".

Ne considère pas un code de langue valide comme
pertinent uniquement parce qu'il respecte
la syntaxe ISO.
""",
            html_source,
        )
        return _LanguageChangesResult.from_data(data)

    async def analyze_language_validity(self, dom: Any, html_source: str | None) -> Any:
        data = await self._analyze(
            """
Vérifie les attributs lang utilisés pour les changements de langue :
validité ISO et pertinence par rapport au texte.
Réponds avec {"has_errors": boolean, "confidence": "low|medium|high",
"total_changes_checked": number, "explanation": string, "findings": [...],
"metadata": {}}.
""",
            html_source,
        )
        return _LanguageValidityResult.from_data(data)

    async def analyze_semantic_presentation(self, dom: Any, html_source: str | None) -> Any:
        data = await self._analyze(
            """
Détermine si des balises sémantiques sont utilisées uniquement pour la
présentation sans justification.
Réponds avec {"has_violations": boolean, "confidence": "low|medium|high",
"total_elements_checked": number, "explanation": string, "findings": [...],
"metadata": {}}.
""",
            html_source,
        )
        return _SemanticResult.from_data(data)

    async def analyze_text_direction_presence(self, dom: Any, html_source: str | None) -> Any:
        data = await self._analyze(
            """
Repère les passages RTL nécessitant dir et qui ne le possèdent pas.
Réponds avec {"missing_dir_count": number, "confidence": "low|medium|high",
"total_rtl_segments_checked": number, "explanation": string, "findings": [...],
"metadata": {}}.
""",
            html_source,
        )
        return _TextDirectionPresenceResult.from_data(data)

    
    async def analyze_text_direction_validity(
        self,
        dom: Any,
        html_source: str | None,
    ) -> Any:
        # Vérification déterministe des valeurs de dir.
        # On examine les attributs internes, comme dans Test8102.
        elements = [
            element
            for element in dom.find_all(True)
            if element.name != "html"
            and element.has_attr("dir")
        ]

        allowed_values = {"ltr", "rtl", "auto"}
        findings = []

        for element in elements:
            direction = str(element.get("dir", "")).strip()

            if direction not in allowed_values:
                findings.append({
                    "element": f'{element.name}[dir="{direction}"]',
                    "message": (
                        f'La valeur dir="{direction}" est invalide. '
                        "Les valeurs autorisées sont ltr, rtl et auto."
                    ),
                    "recommendation": (
                        "Remplacer la valeur par une direction "
                        "valide et adaptée au contenu."
                    ),
                    "evidence": {
                        "dir": direction,
                        "text": element.get_text(
                            " ", strip=True
                        )[:150],
                    },
                })

        if findings:
            return _TextDirectionValidityResult.from_data({
                "has_errors": True,
                "confidence": "high",
                "total_dir_attributes_checked": len(elements),
                "explanation": (
                    f"{len(findings)} attribut(s) dir "
                    "avec une valeur invalide."
                ),
                "findings": findings,
                "metadata": {
                    "validation": "dom",
                },
            })

        # Les valeurs sont syntaxiquement valides.
        # Gemma vérifie encore leur pertinence
        # par rapport au contenu.
        data = await self._analyze(
            """
Vérifie si chaque attribut dir est pertinent
par rapport au sens de lecture du texte.

Les valeurs des attributs dir ont déjà été
vérifiées et sont syntaxiquement valides.

Réponds avec :
{
"has_errors": false,
"confidence": "high",
"total_dir_attributes_checked": 0,
"explanation": "",
"findings": [],
"metadata": {}
}

Adapte les valeurs aux éléments réellement analysés.

Si has_errors vaut true, chaque anomalie doit
avoir un finding avec element, message,
recommendation et evidence.

N'invente aucune anomalie.
""",
            html_source,
        )

        return _TextDirectionValidityResult.from_data(data)


class _Result:
    @staticmethod
    def _common(data: dict[str, Any]) -> dict[str, Any]:
        explanation = str(data.get("explanation", ""))
        # Clean hallucinated explanations
        explanation = _clean_hallucinated_explanation(explanation)
        return {
            "confidence": data.get("confidence", "low"),
            "explanation": explanation,
            "findings": data.get("findings", []),
            "metadata": data.get("metadata", {}),
        }


class _LanguageChangesResult(_Result):
    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "_LanguageChangesResult":
        return cls({**cls._common(data), "has_violations": _bool(data, "has_violations"),
                    "total_elements_checked": _count(data, "total_elements_checked")})


class _LanguageValidityResult(_Result):
    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "_LanguageValidityResult":
        return cls({**cls._common(data), "has_errors": _bool(data, "has_errors"),
                    "total_changes_checked": _count(data, "total_changes_checked")})


class _SemanticResult(_LanguageChangesResult):
    pass


class _TextDirectionPresenceResult(_Result):
    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "_TextDirectionPresenceResult":
        return cls({**cls._common(data), "missing_dir_count": _count(data, "missing_dir_count"),
                    "total_rtl_segments_checked": _count(data, "total_rtl_segments_checked")})


class _TextDirectionValidityResult(_Result):
    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "_TextDirectionValidityResult":
        return cls({**cls._common(data), "has_errors": _bool(data, "has_errors"),
                    "total_dir_attributes_checked": _count(data, "total_dir_attributes_checked")})


class _ValidationResult:
    def __init__(self, is_valid: bool, errors: list[dict[str, Any]]) -> None:
        self.is_valid = is_valid
        self.errors = errors


def _bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Le champ {key} doit être booléen.")
    return value


def _count(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Le champ {key} doit être un entier positif.")
    return value


def _errors(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("Le champ errors doit être une liste.")
    errors: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Chaque erreur HTML doit être un objet.")
        errors.append(item)
    return errors

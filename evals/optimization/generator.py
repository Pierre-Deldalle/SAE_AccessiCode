from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.json_utils import parse_ai_json

from evals.optimization.models import (
    GeneratedPromptCandidate,
)


OPTIMIZER_PROMPT = """
Tu dois améliorer un prompt utilisé par AccessiCode pour déterminer
si le titre HTML d'une page est pertinent par rapport à son contenu.

Tu reçois :
- le prompt de production actuel ;
- des erreurs représentatives observées sur le dataset TRAIN ;
- quelques exemples déjà correctement traités.

Tu dois produire exactement {candidate_count} nouveau(x) prompt(s)
COMPLET(S) et AUTONOME(S).

OBJECTIFS :
- améliorer l'exactitude de relevant ;
- distinguer une page réellement identifiée par son titre d'une page
  seulement liée au même thème ;
- tenir compte des différences importantes comme une action, une étape,
  un identifiant, un numéro de page ou une ressource précise ;
- utiliser relevant=null lorsque les informations disponibles sont
  réellement insuffisantes pour conclure ;
- ne pas utiliser null lorsque les informations permettent clairement
  de conclure ;
- mieux calibrer confidence ;
- éviter les erreurs à haute confiance ;
- préserver les comportements déjà corrects.

RÈGLES IMPORTANTES :
- ne mémorise pas les exemples du dataset ;
- ne cite jamais les identifiants des cas ;
- ne transforme pas un nom, une date, un produit, une ville,
  un numéro ou une valeur précise du dataset en règle générale ;
- n'écris aucune analyse de ton travail ;
- n'écris aucune justification séparée ;
- chaque prompt candidat doit être directement utilisable.

Le prompt candidat sera ensuite interprété par Python avec str.format().

Dans le prompt candidat final, les trois variables obligatoires sont exactement :
- {{title}}
- {{heading}}
- {{content}}

Ces trois variables doivent réellement être substituables par str.format().

Toutes les autres accolades littérales présentes dans le prompt candidat,
notamment celles utilisées pour montrer un objet JSON, doivent être doublées.

Par exemple, si le prompt candidat contient un exemple de réponse JSON,
il doit contenir exactement :

{{{{
  "relevant": true,
  "explanation": "explication courte",
  "contradictions": [],
  "uncertainties": [],
  "confidence": "high"
}}}}

et non des accolades JSON simples.

Le prompt candidat doit demander au modèle analysé de répondre avec
le même schéma JSON que le prompt actuel :

- relevant : true, false ou null ;
- explanation : chaîne courte ;
- contradictions : tableau de chaînes ;
- uncertainties : tableau de chaînes ;
- confidence : "low", "medium" ou "high".

confidence représente la confiance dans la valeur choisie pour relevant.

relevant=null signifie que les informations disponibles sont réellement
insuffisantes pour décider.
Cela ne signifie pas automatiquement confidence=low.

Le système d'évaluation utilise une vérité humaine.
N'essaie pas de contourner l'évaluation.

Voici le contexte issu exclusivement du dataset TRAIN :

{optimization_context}

Réponds UNIQUEMENT avec un objet JSON valide sous cette forme :

{{
  "candidates": [
    {{
      "prompt": "prompt complet"
    }}
  ]
}}

Aucun Markdown.
Aucun texte avant ou après le JSON.
""".strip()


class PromptGenerationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        raw_response: str,
        parsed_data: dict[str, Any] | None = None,
        rejection_reasons: list[str] | None = None,
    ):
        super().__init__(
            message
        )

        self.raw_response = (
            raw_response
        )

        self.parsed_data = (
            parsed_data
        )

        self.rejection_reasons = (
            rejection_reasons
            or []
        )


def normalize_prompt_template(
    template: str,
) -> str:
    """
    Normalise un prompt généré par une IA pour qu'il puisse être
    utilisé ensuite avec str.format().

    - {title}, {heading} et {content} restent des variables.
    - {{title}}, {{heading}} et {{content}} sont corrigés en variables.
    - Les autres accolades littérales sont échappées avec {{ et }}.
    - Les accolades déjà correctement échappées ne sont pas doublées
      une seconde fois.
    """
    placeholders = {
        "title": "__ACCESSICODE_TITLE__",
        "heading": "__ACCESSICODE_HEADING__",
        "content": "__ACCESSICODE_CONTENT__",
    }

    normalized = template

    #
    # 1. Protéger les variables obligatoires.
    #
    # On traite d'abord la forme double pour éviter que
    # "{{title}}" ne devienne quelque chose d'ambigu.
    #
    for name, sentinel in placeholders.items():
        normalized = normalized.replace(
            f"{{{{{name}}}}}",
            sentinel,
        )

        normalized = normalized.replace(
            f"{{{name}}}",
            sentinel,
        )

    #
    # 2. Protéger les accolades littérales déjà échappées.
    #
    left_brace_sentinel = (
        "__ACCESSICODE_LEFT_BRACE__"
    )

    right_brace_sentinel = (
        "__ACCESSICODE_RIGHT_BRACE__"
    )

    normalized = normalized.replace(
        "{{",
        left_brace_sentinel,
    )

    normalized = normalized.replace(
        "}}",
        right_brace_sentinel,
    )

    #
    # 3. Échapper toutes les accolades littérales restantes.
    #
    normalized = normalized.replace(
        "{",
        "{{",
    )

    normalized = normalized.replace(
        "}",
        "}}",
    )

    #
    # 4. Restaurer les accolades qui étaient déjà échappées.
    #
    normalized = normalized.replace(
        left_brace_sentinel,
        "{{",
    )

    normalized = normalized.replace(
        right_brace_sentinel,
        "}}",
    )

    #
    # 5. Restaurer les trois véritables variables Python.
    #
    for name, sentinel in placeholders.items():
        normalized = normalized.replace(
            sentinel,
            f"{{{name}}}",
        )

    return normalized


class PromptCandidateGenerator:
    def __init__(
        self,
        llm: OllamaLLM,
    ):
        self.llm = llm

    async def generate(
        self,
        *,
        optimization_context: dict[str, Any],
        candidate_count: int = 3,
    ) -> list[GeneratedPromptCandidate]:
        if candidate_count < 1:
            raise ValueError(
                "candidate_count doit être supérieur ou égal à 1."
            )

        prompt = OPTIMIZER_PROMPT.format(
            candidate_count=candidate_count,
            optimization_context=json.dumps(
                optimization_context,
                ensure_ascii=False,
                indent=2,
            ),
        )

        data, raw_response = (
            await self._generate_json(
                prompt
            )
        )

        raw_candidates = data.get(
            "candidates"
        )

        if not isinstance(
            raw_candidates,
            list,
        ):
            raise ValueError(
                "La réponse de l'optimiseur doit contenir "
                "une liste 'candidates'."
            )

        candidates: list[
            GeneratedPromptCandidate
        ] = []

        seen_templates: set[str] = set()

        rejection_reasons: list[str] = []

        for index, raw_candidate in enumerate(
            raw_candidates,
            start=1,
        ):
            if isinstance(
                raw_candidate,
                dict,
            ):
                template = raw_candidate.get(
                    "prompt"
                )

                if not isinstance(
                    template,
                    str,
                ):
                    template = raw_candidate.get(
                        "template"
                    )

            elif isinstance(
                raw_candidate,
                str,
            ):
                template = raw_candidate

            else:
                rejection_reasons.append(
                    f"Candidat {index} : "
                    "le candidat n'est ni un objet JSON "
                    "ni une chaîne."
                )

                continue

            if not isinstance(
                template,
                str,
            ):
                rejection_reasons.append(
                    f"Candidat {index} : "
                    "aucun champ 'prompt' ou 'template' "
                    "contenant une chaîne."
                )

                continue

            template = template.strip()

            if not template:
                rejection_reasons.append(
                    f"Candidat {index} : "
                    "le prompt est vide."
                )

                continue
            
            template = normalize_prompt_template(
                template
            )

            if template in seen_templates:
                rejection_reasons.append(
                    f"Candidat {index} : "
                    "prompt dupliqué."
                )

                continue

            seen_templates.add(
                template
            )

            candidates.append(
                GeneratedPromptCandidate(
                    name=(
                        f"candidate_"
                        f"{len(candidates) + 1:03d}"
                    ),
                    template=template,
                    rationale="",
                )
            )

            if len(candidates) >= candidate_count:
                break

        if not candidates:
            details = "\n".join(
                f"- {reason}"
                for reason in rejection_reasons
            )

            raise PromptGenerationError(
                (
                    "L'optimiseur n'a produit aucun "
                    "prompt candidat exploitable."
                    + (
                        f"\n{details}"
                        if details
                        else ""
                    )
                ),
                raw_response=raw_response,
                parsed_data=data,
                rejection_reasons=(
                    rejection_reasons
                ),
            )

        return candidates

    async def _generate_json(
        self,
        prompt: str,
    ) -> tuple[
        dict[str, Any],
        str,
    ]:
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = await self.llm.generate(
                    prompt,
                    format="json",
                    max_tokens=1200,
                    temperature=0,
                )

                data = parse_ai_json(
                    response
                )

                return (
                    data,
                    response,
                )

            except (
                ValueError,
                aiohttp.ClientError,
                OSError,
                asyncio.TimeoutError,
            ) as error:
                last_error = error

                if attempt == 0:
                    await asyncio.sleep(
                        0.5
                    )

        raise RuntimeError(
            "Impossible d'obtenir une réponse JSON "
            "exploitable de l'optimiseur : "
            f"{last_error}"
        ) from last_error
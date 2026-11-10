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


CANDIDATE_STRATEGIES = (
    """
Adopte une stratégie équilibrée.

Cherche à améliorer globalement :
- l'exactitude de relevant ;
- la distinction entre true, false et null ;
- la conservation des comportements déjà corrects.

Évite de surcorriger une catégorie d'erreurs au détriment des autres.
""".strip(),

    """
Concentre particulièrement ce candidat sur la gestion des preuves
insuffisantes.

Le prompt doit aider le modèle à distinguer :
- une contradiction réelle, qui peut justifier false ;
- une correspondance claire, qui peut justifier true ;
- une absence réelle d'informations suffisantes, qui doit conduire à null.

Évite les verdicts forcés lorsque le contenu est incomplet, ambigu,
corrompu, principalement constitué de navigation ou encore en chargement,
sans pour autant utiliser null lorsqu'une conclusion est clairement possible.
""".strip(),

    """
Concentre particulièrement ce candidat sur la calibration de confidence
et la prévention des erreurs critiques.

Le prompt doit :
- encourager high uniquement lorsque les preuves sont réellement fortes ;
- éviter une confiance élevée lorsqu'il existe une contradiction,
  une ambiguïté ou une information insuffisante ;
- conserver une confiance élevée sur les cas clairement déterminables ;
- ne pas confondre incertitude sur relevant et manque total de confiance
  dans le verdict choisi.
""".strip(),
)


OPTIMIZER_PROMPT = """
Tu dois améliorer un prompt utilisé par AccessiCode pour déterminer
si le titre HTML d'une page permet d'identifier correctement son contenu.

Tu reçois :
- le prompt de production actuel ;
- des erreurs représentatives observées uniquement sur le dataset TRAIN ;
- quelques exemples déjà correctement traités ;
- une stratégie particulière à suivre pour ce candidat.

Tu dois produire UN SEUL nouveau prompt COMPLET, AUTONOME.

STRATÉGIE IMPOSÉE POUR CE CANDIDAT :

{strategy}

OBJECTIFS GÉNÉRAUX :
- améliorer l'exactitude de relevant ;
- préserver les comportements déjà corrects ;
- distinguer une page réellement identifiée par son titre d'une page
  seulement liée au même thème ;
- détecter les incohérences importantes portant notamment sur une action,
  une étape, un état, un identifiant, une date, une pagination,
  une ressource ou toute autre information distinctive ;
- utiliser relevant=null lorsque les informations disponibles sont
  réellement insuffisantes pour conclure ;
- ne pas forcer true ou false lorsque le contenu est trop incomplet,
  ambigu, corrompu, principalement constitué de navigation,
  ou encore en cours de chargement ;
- ne pas utiliser null lorsque les informations permettent clairement
  de conclure ;
- mieux calibrer confidence ;
- éviter particulièrement les verdicts incorrects avec une confiance élevée.

RÈGLE FONDAMENTALE DE GÉNÉRALISATION :

Les exemples du dataset TRAIN servent uniquement à identifier des
principes généraux.

Tu ne dois JAMAIS mémoriser ou recopier dans un prompt candidat une
valeur précise provenant des exemples TRAIN.

En particulier :
- ne cite aucun identifiant de cas ;
- ne cite aucun nom de site ou de service observé dans TRAIN ;
- ne cite aucun titre exact observé dans TRAIN ;
- ne cite aucun produit, ville, personne, numéro, date, identifiant
  ou valeur spécifique provenant de TRAIN ;
- ne transforme pas un exemple particulier en exception spéciale ;
- ne crée pas une règle disant qu'un type précis de page reçoit
  automatiquement true ou false simplement parce qu'un exemple TRAIN
  appartenait à ce type.

Exemple de mauvaise généralisation :
"Le titre X doit être considéré comme faux."

Exemple de bonne généralisation :
"Un titre constitué uniquement du nom du site ne suffit pas forcément
à identifier le contenu spécifique de la page."

Autre exemple de mauvaise généralisation :
"Une page d'erreur doit toujours être considérée comme non pertinente."

Exemple de bonne généralisation :
"Un titre décrivant correctement l'état réel d'une page peut être pertinent ;
le verdict doit dépendre de la correspondance entre le titre et le contenu,
et non du type de page."

Pour chaque erreur TRAIN, cherche donc la règle générale expliquant
l'erreur plutôt que de recopier l'exemple.

CONTRAINTES DU PROMPT CANDIDAT :

Chaque prompt candidat doit :
- être directement utilisable ;
- contenir exactement les trois variables suivantes :
  {{title}}
  {{heading}}
  {{content}}
- demander une réponse JSON uniquement ;
- utiliser exactement les champs :
  relevant
  explanation
  contradictions
  uncertainties
  confidence
- rester concis : chaque prompt candidat doit idéalement tenir en moins
  de 500 mots ;
- ne pas ajouter d'exemples spécifiques si une règle générale suffit ;
- éviter les répétitions entre les différentes consignes du prompt.

Le champ relevant doit pouvoir valoir :
- true ;
- false ;
- null.

Le champ confidence doit pouvoir valoir uniquement :
- "low" ;
- "medium" ;
- "high".

confidence représente la confiance dans la valeur choisie pour relevant.

IMPORTANT :
relevant=null signifie que les informations disponibles sont réellement
insuffisantes pour déterminer si le titre est pertinent.

Cela ne signifie PAS automatiquement confidence=low.

Par exemple, si les données sont manifestement insuffisantes,
le modèle peut être très certain que le bon verdict est null.

Le prompt candidat doit également demander une explication courte.
Il ne doit pas encourager les longues analyses, les répétitions
ou le texte en dehors du JSON.

Le code AccessiCode normalisera lui-même les accolades nécessaires
à l'utilisation ultérieure avec Python str.format().
Tu n'as donc pas besoin d'échapper spécialement les accolades JSON.

IMPORTANT :
- n'écris aucune analyse de ton travail ;
- n'écris aucune justification séparée des candidats ;
- n'essaie pas de contourner le système d'évaluation ;
- le système utilise une vérité humaine indépendante.

Voici le contexte issu exclusivement du dataset TRAIN :

{optimization_context}

{retry_instruction}

Réponds UNIQUEMENT avec un objet JSON valide de cette forme :

{{
  "prompt": "prompt complet"
}}

Aucun Markdown.
Aucun texte avant ou après le JSON.
Aucun champ supplémentaire.
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
                "candidate_count doit être "
                "supérieur ou égal à 1."
            )

        candidates: list[
            GeneratedPromptCandidate
        ] = []

        seen_templates: set[str] = set()

        raw_responses: list[str] = []

        parsed_responses: dict[
            str,
            Any,
        ] = {}

        rejection_reasons: list[str] = []

        context_json = json.dumps(
            optimization_context,
            ensure_ascii=False,
            indent=2,
        )

        for index in range(
            candidate_count
        ):
            candidate_name = (
                f"candidate_{index + 1:03d}"
            )

            strategy = (
                self._get_strategy(
                    index
                )
            )

            candidate_created = False

            #
            # Deux tentatives maximum pour un candidat.
            #
            # _generate_json possède déjà son propre retry
            # pour les erreurs JSON/réseau.
            #
            # Ici, cette boucle sert aux réponses valides
            # mais inutilisables : prompt absent, vide
            # ou dupliqué.
            #
            for candidate_attempt in range(2):
                if candidate_attempt == 0:
                    retry_instruction = ""
                else:
                    retry_instruction = """
    ATTENTION :
    La tentative précédente pour ce candidat était
    inexploitable ou trop proche d'un candidat déjà généré.

    Produis cette fois un prompt complet, valide et
    réellement différent, tout en respectant la stratégie.
    """.strip()

                prompt = OPTIMIZER_PROMPT.format(
                    strategy=strategy,
                    optimization_context=(
                        context_json
                    ),
                    retry_instruction=(
                        retry_instruction
                    ),
                )

                try:
                    data, raw_response = (
                        await self._generate_json(
                            prompt,
                            max_tokens=1500,
                        )
                    )

                except RuntimeError as error:
                    rejection_reasons.append(
                        (
                            f"{candidate_name} "
                            f"(tentative "
                            f"{candidate_attempt + 1}) : "
                            f"{error}"
                        )
                    )

                    continue

                raw_responses.append(
                    (
                        f"===== {candidate_name} "
                        f"/ tentative "
                        f"{candidate_attempt + 1} =====\n"
                        f"{raw_response}"
                    )
                )

                parsed_responses[
                    (
                        f"{candidate_name}_"
                        f"attempt_"
                        f"{candidate_attempt + 1}"
                    )
                ] = data

                template = data.get(
                    "prompt"
                )

                if not isinstance(
                    template,
                    str,
                ):
                    rejection_reasons.append(
                        (
                            f"{candidate_name} "
                            f"(tentative "
                            f"{candidate_attempt + 1}) : "
                            "aucun champ 'prompt' "
                            "contenant une chaîne."
                        )
                    )

                    continue

                template = template.strip()

                if not template:
                    rejection_reasons.append(
                        (
                            f"{candidate_name} "
                            f"(tentative "
                            f"{candidate_attempt + 1}) : "
                            "le prompt est vide."
                        )
                    )

                    continue

                template = (
                    normalize_prompt_template(
                        template
                    )
                )

                if template in seen_templates:
                    rejection_reasons.append(
                        (
                            f"{candidate_name} "
                            f"(tentative "
                            f"{candidate_attempt + 1}) : "
                            "prompt dupliqué."
                        )
                    )

                    continue

                seen_templates.add(
                    template
                )

                candidates.append(
                    GeneratedPromptCandidate(
                        name=candidate_name,
                        template=template,
                        rationale="",
                    )
                )

                candidate_created = True

                break

            if not candidate_created:
                details = "\n".join(
                    f"- {reason}"
                    for reason in rejection_reasons
                )

                raise PromptGenerationError(
                    (
                        "L'optimiseur n'a pas réussi "
                        "à produire tous les prompts "
                        "candidats demandés.\n"
                        f"Échec sur {candidate_name}."
                        + (
                            f"\n{details}"
                            if details
                            else ""
                        )
                    ),
                    raw_response=(
                        "\n\n".join(
                            raw_responses
                        )
                    ),
                    parsed_data=(
                        parsed_responses
                    ),
                    rejection_reasons=(
                        rejection_reasons
                    ),
                )

        return candidates

    async def _generate_json(
        self,
        prompt: str,
        *,
        max_tokens: int,
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
                    max_tokens=max_tokens,
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
    
    @staticmethod
    def _get_strategy(
        index: int,
    ) -> str:
        if index < len(
            CANDIDATE_STRATEGIES
        ):
            return (
                CANDIDATE_STRATEGIES[index]
            )

        return (
            "Propose une stratégie complémentaire "
            "différente des stratégies précédentes. "
            "Cherche un autre compromis général entre "
            "exactitude, utilisation de null et "
            "calibration de confidence."
        )
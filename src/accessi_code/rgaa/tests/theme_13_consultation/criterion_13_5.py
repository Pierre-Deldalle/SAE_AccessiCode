"""
RGAA 4.1.2 — critère 13.5 : dans chaque page web, chaque contenu cryptique
(art ASCII, émoticône, syntaxe cryptique) a-t-il une alternative ?

Contenus repérés par ``analysis/cryptic.py`` (les sigles ne sont pas concernés).
Le contenu vérifie une de ces conditions :
- un attribut title est disponible (ou aria-label sur role="img") → PASS,
  sans IA ; sa pertinence relève de 13.6 ;
- une définition est donnée par le contexte adjacent : question de sens, jugée
  par l'IA (``cryptic_context``) → PASS / FAIL, NEEDS_REVIEW si l'IA est
  incertaine ou absente.
"""

from __future__ import annotations

from html import escape
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.components import component_identifier
from accessi_code.analysis.cryptic import ASCII_ART_KIND, CrypticContent, find_cryptic_contents
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

EMPTY_SUMMARY = "Aucun contenu cryptique (art ASCII, émoticône, syntaxe cryptique) dans la page."
RECOMMENDATION = (
    "Donner une alternative au contenu cryptique (attribut title) ou expliquer son sens dans le texte qui l'entoure."
)
# Texte à remplacer dans l'exemple : l'alternative dépend du sens du contenu.
MEANING_PLACEHOLDER = "[sens du contenu]"


def cryptic_example(content: CrypticContent, alternative: str | None = None) -> str:
    """
    Correction « avant → après » avec le vrai contenu : un dessin en art ASCII devient une image
    (role="img" et aria-label) ; une émoticône ou une abréviation est entourée d'un span avec un title.
    """
    alternative = alternative or MEANING_PLACEHOLDER
    if content.kind == ASCII_ART_KIND:
        after = opening_tag(content.element, role="img", **{"aria-label": alternative})
        return f"Exemple : {opening_tag(content.element)} → {after}"
    text = escape(content.text, quote=False)
    span = opening_tag(BeautifulSoup("", "html.parser").new_tag("span"), title=alternative)
    return f"Exemple : {text} → {span}{text}</span>"


class Test1351(RGAATest):
    test_id = "13.5.1"
    criterion_id = "13.5"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        contents = find_cryptic_contents(soup)
        outcomes: list[Outcome | None] = [None] * len(contents)
        to_judge: list[tuple[int, RelevanceItem]] = []
        for position, content in enumerate(contents):
            if content.alternative:
                outcomes[position] = make_outcome(TestStatus.PASS)
                continue
            to_judge.append(
                (
                    position,
                    RelevanceItem(
                        text=content.text[:400],
                        element_html=str(content.element)[:400],
                        context=content.context,
                        details={"kind": content.kind},
                    ),
                )
            )

        verdicts = await judge_relevance(services, "cryptic_context", [item for _, item in to_judge])
        for (position, item), verdict in zip(to_judge, verdicts, strict=True):
            content = contents[position]
            recommendation = verdict.recommendation(RECOMMENDATION)
            if verdict.status is TestStatus.FAIL:
                recommendation += " " + cryptic_example(content, verdict.suggestion)
            outcomes[position] = make_outcome(
                verdict.status,
                component_identifier(content.element, position),
                verdict.message(
                    f"Le contenu cryptique ({content.kind}) « {item.text[:80]} » n'a ni attribut title, "
                    "ni définition dans le contexte adjacent.",
                    f"Le sens du contenu cryptique ({content.kind}) « {item.text[:80]} » donné par le contexte "
                    "reste à vérifier.",
                ),
                recommendation,
                node=content.element,
                kind=content.kind,
                cryptic_content=item.text,
                context=item.context,
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=EMPTY_SUMMARY,
            noun="contenu(s) cryptique(s)",
        )

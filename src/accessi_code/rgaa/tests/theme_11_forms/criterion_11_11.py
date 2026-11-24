"""
RGAA 4.1.2 — critère 11.11 : dans chaque formulaire, le contrôle de saisie
est-il accompagné, si nécessaire, de suggestions facilitant la correction ?

- 11.11.1 : le message d'erreur suggère le type et le format attendus.
- 11.11.2 : le message d'erreur suggère des exemples de valeurs attendues.

Seuls les messages présents dans le DOM fourni sont jugés (par l'IA). Note
technique : un attribut pattern accompagné d'un title fournit le message du
navigateur et valide 11.11.1.
"""

from __future__ import annotations

from typing import Any, ClassVar

from bs4 import BeautifulSoup

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import clean, field_description, field_error_message, fields, identifier, label_text
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable


class _SuggestionTest(RGAATest):
    criterion_id = "11.11"
    required_capabilities = frozenset({Capability.DOM})
    kind: ClassVar[str]
    fail_message: ClassVar[str]
    recommendation: ClassVar[str]
    pattern_title_passes: ClassVar[bool] = False

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        outcomes = []
        pending = []
        for field in fields(soup):
            message = field_error_message(field, soup)
            if self.pattern_title_passes and field.has_attr("pattern") and clean(field.get("title")):
                outcomes.append(make_outcome(TestStatus.PASS))
            elif message:
                pending.append((field, message))
        if not outcomes and not pending:
            return not_applicable(self, "Aucun message d'erreur de saisie dans le DOM fourni.")

        items = [
            RelevanceItem(text=message, context=label_text(field, soup), details=field_description(field, soup))
            for field, message in pending
        ]
        verdicts = await judge_relevance(services, self.kind, items)
        for (field, message), verdict in zip(pending, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(field, soup),
                    verdict.message(
                        f"{self.fail_message} (« {message[:100]} »).",
                        f"La suggestion de correction du message « {message[:100]} » reste à vérifier.",
                    ),
                    verdict.recommendation(self.recommendation),
                    node=field,
                    error_message=message,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun message d'erreur de saisie.", noun="message(s)")


class Test11111(_SuggestionTest):
    """11.11.1 : les types et formats attendus sont-ils suggérés, si nécessaire ?"""

    test_id = "11.11.1"
    kind = "error_suggestion_format"
    fail_message = "Le message d'erreur n'indique pas le type ou le format attendu"
    recommendation = "Préciser le format attendu dans le message d'erreur (ex. « jj/mm/aaaa »)."
    pattern_title_passes = True


class Test11112(_SuggestionTest):
    """11.11.2 : des exemples de valeurs attendues sont-ils suggérés, si nécessaire ?"""

    test_id = "11.11.2"
    kind = "error_suggestion_example"
    fail_message = "Le message d'erreur ne propose pas d'exemple de valeur attendue"
    recommendation = "Ajouter un exemple dans le message d'erreur (ex. « nom@exemple.fr »)."

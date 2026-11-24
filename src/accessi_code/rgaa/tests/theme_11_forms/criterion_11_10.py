"""
RGAA 4.1.2 — critère 11.10 : dans chaque formulaire, le contrôle de saisie
est-il utilisé de manière pertinente (hors cas particuliers) ?

- 11.10.1 / 11.10.2 : indication des champs obligatoires (non applicables si le
  formulaire n'a qu'un champ ou si les champs facultatifs sont signalés).
- 11.10.3 / 11.10.6 : un message d'erreur identifie nommément le champ, ou le
  champ porte aria-invalid="true" (l'identification est jugée par l'IA).
- 11.10.4 : le message d'erreur d'un champ obligatoire invalide est dans
  l'étiquette ou un passage associé.
- 11.10.5 / 11.10.7 : une instruction de type ou de format est présente dans
  l'étiquette ou le passage associé (sa présence et sa pertinence sont jugées par l'IA).

Les messages d'erreur ne sont visibles que s'ils figurent dans le DOM fourni
(page après soumission, ou erreurs affichées).
"""

from __future__ import annotations

from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import (
    all_required_notice,
    associated_text,
    field_description,
    field_error_message,
    fields,
    form_context,
    group_legend,
    has_format,
    identifier,
    invalid,
    label_text,
    mandatory_text,
    normalize,
    optional_text,
    referenced_text,
    required,
)
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import example, free_id

_ERROR_WORDS = ("erreur", "incorrect", "invalide", "veuillez", "obligatoire", "requis", "manquant")


INVALID_RECOMMENDATION = 'Nommer le champ dans le message d\'erreur, ou ajouter aria-invalid="true" au champ.'


def _mandatory_example(field: Tag, soup: BeautifulSoup) -> str:
    """Mention « (obligatoire) » ajoutée au texte du label for du champ, s'il en a un seul."""
    field_id = field.get("id")
    labels = soup.find_all("label", attrs={"for": field_id}) if isinstance(field_id, str) and field_id else []
    if len(labels) != 1 or not labels[0].get_text(strip=True):
        return ""
    label, text = labels[0], labels[0].get_text(" ", strip=True)
    return example(f"{opening_tag(label)}{text}</label>", f"{opening_tag(label)}{text} (obligatoire)</label>")


def _invalid_example(field: Tag) -> str:
    return example(opening_tag(field), opening_tag(field, **{"aria-invalid": "true"}))


def _describedby_example(field: Tag, soup: BeautifulSoup) -> str:
    """Message d'erreur relié au champ par aria-describedby (identifiant du message tiré de celui du champ)."""
    message_id = f"{free_id(field, soup)}-erreur"
    references = " ".join(filter(None, [str(field.get("aria-describedby") or "").strip(), message_id]))
    after = opening_tag(field, **{"aria-describedby": references})
    return example(opening_tag(field), f'{after} et <p id="{message_id}">[message d\'erreur]</p>')


def _dom(context: AuditContext, test_id: str) -> BeautifulSoup:
    if not isinstance(context.dom, BeautifulSoup):
        raise ValueError(f"Le test {test_id} nécessite un DOM.")
    return context.dom


def _group_text(field: Tag, soup: BeautifulSoup) -> str:
    group = field.find_parent(lambda node: node.name == "fieldset" or node.get("role") in {"group", "radiogroup"})
    return group_legend(group, soup) if isinstance(group, Tag) else ""


def _exempt_forms(soup: BeautifulSoup) -> set[int]:
    """Formulaires exemptés de 11.10.1 et 11.10.2 (un seul champ, ou champs facultatifs signalés)."""
    exempt: set[int] = set()
    by_form: dict[int, list[Tag]] = {}
    for field in fields(soup):
        by_form.setdefault(id(field.find_parent("form")), []).append(field)
    for form_id, members in by_form.items():
        if len(members) == 1:
            exempt.add(form_id)
            continue
        if any(optional_text(f"{label_text(field, soup)} {_group_text(field, soup)}") for field in members):
            # Les champs facultatifs sont indiqués visiblement : cas particulier,
            # sauf si tous les champs sont obligatoires.
            if not all(required(field) for field in members):
                exempt.add(form_id)
    return exempt


class Test11101(RGAATest):
    """11.10.1 : chaque champ obligatoire est-il signalé (indication visible ou required / aria-required) ?"""

    test_id = "11.10.1"
    criterion_id = "11.10"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        exempt = _exempt_forms(soup)
        outcomes: list[Outcome] = []
        forms_without_indication: dict[int, Tag] = {}
        for field in fields(soup):
            form = field.find_parent("form")
            if id(form) in exempt:
                continue
            if required(field) or mandatory_text(label_text(field, soup)) or all_required_notice(form, soup):
                outcomes.append(make_outcome(TestStatus.PASS))
            else:
                forms_without_indication.setdefault(id(form), field)

        for field in forms_without_indication.values():
            if outcomes:
                continue  # D'autres champs sont signalés : ceux-ci sont présumés facultatifs.
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    identifier(field, soup),
                    "Aucun champ n'est signalé comme obligatoire : vérifier qu'aucun ne l'est réellement.",
                    "Signaler les champs obligatoires (required ou aria-required, et mention visible).",
                    node=field,
                )
            )
        return build_result(
            self,
            outcomes,
            empty_summary="Aucun champ concerné (formulaire à un seul champ ou exempté).",
            noun="champ(s)",
        )


class Test11102(RGAATest):
    """11.10.2 : l'indication d'obligation est-elle visible dans l'étiquette ou un passage associé ?"""

    test_id = "11.10.2"
    criterion_id = "11.10"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        exempt = _exempt_forms(soup)
        outcomes = []
        for field in fields(soup):
            form = field.find_parent("form")
            if not required(field) or id(form) in exempt:
                continue
            text = f"{associated_text(field, soup)} {_group_text(field, soup)}"
            if mandatory_text(text) or all_required_notice(form, soup):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(field, soup),
                    "Le champ est obligatoire (required / aria-required) mais aucune mention visible ne le signale "
                    "dans son étiquette ou un texte associé.",
                    "Ajouter « (obligatoire) » ou un astérisque expliqué dans l'étiquette du champ."
                    + _mandatory_example(field, soup),
                    node=field,
                    associated_text=text.strip()[:200],
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun champ obligatoire concerné.", noun="champ(s)")


class _ErrorIdentificationTest(RGAATest):
    """Message d'erreur identifiant le champ, ou aria-invalid="true"."""

    criterion_id = "11.10"
    required_capabilities = frozenset({Capability.DOM})
    empty_summary: ClassVar[str]

    def in_scope(self, field: Tag) -> bool:
        raise NotImplementedError

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        outcomes = []
        pending: list[tuple[Tag, str]] = []
        for field in fields(soup):
            if not self.in_scope(field):
                continue
            message = field_error_message(field, soup)
            if invalid(field):
                outcomes.append(make_outcome(TestStatus.PASS))
            elif message:
                pending.append((field, message))

        if not outcomes and not pending:
            return not_applicable(self, self.empty_summary)

        items = [
            RelevanceItem(text=message, context=label_text(field, soup), details=field_description(field, soup))
            for field, message in pending
        ]
        verdicts = await judge_relevance(services, "error_identification", items)
        for (field, message), verdict in zip(pending, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(field, soup),
                    verdict.message(
                        f"Le message d'erreur « {message[:100]} » n'identifie pas le champ concerné.",
                        f"Le message d'erreur « {message[:100]} » doit identifier le champ : à vérifier.",
                    ),
                    verdict.recommendation(INVALID_RECOMMENDATION)
                    + (_invalid_example(field) if verdict.status is TestStatus.FAIL else ""),
                    node=field,
                    error_message=message,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty_summary, noun="champ(s)")


class Test11103(_ErrorIdentificationTest):
    """11.10.3 : erreur de champ obligatoire vide."""

    test_id = "11.10.3"
    empty_summary = "Aucun message d'erreur de champ obligatoire dans le DOM fourni."

    def in_scope(self, field: Tag) -> bool:
        return required(field)


class Test11106(_ErrorIdentificationTest):
    """11.10.6 : message d'erreur fournissant une instruction de type ou de format."""

    test_id = "11.10.6"
    empty_summary = "Aucun message d'erreur de format dans le DOM fourni."

    def in_scope(self, field: Tag) -> bool:
        return has_format(field)


class Test11104(RGAATest):
    """11.10.4 : le message d'erreur d'un champ obligatoire invalide est-il dans l'étiquette ou un passage associé ?"""

    test_id = "11.10.4"
    criterion_id = "11.10"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        candidates = [field for field in fields(soup) if required(field) and invalid(field)]
        if not candidates:
            return not_applicable(self, "Aucun champ obligatoire en erreur (aria-invalid) dans le DOM fourni.")
        outcomes = []
        for field in candidates:
            associated = f"{associated_text(field, soup)} {referenced_text(field, soup, 'aria-errormessage')}"
            if any(word in normalize(associated) for word in _ERROR_WORDS):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(field, soup),
                    "Le champ est en erreur mais aucun message n'est placé dans son étiquette ou un passage associé.",
                    "Associer le message d'erreur au champ avec aria-describedby ou aria-errormessage."
                    + _describedby_example(field, soup),
                    node=field,
                    separate_message=field_error_message(field, soup)[:200],
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun champ obligatoire en erreur.", noun="champ(s)")


class _FormatInstructionTest(RGAATest):
    """Instruction de type ou de format dans l'étiquette ou le passage associé."""

    criterion_id = "11.10"
    required_capabilities = frozenset({Capability.DOM})
    empty_summary: ClassVar[str]

    def in_scope(self, field: Tag) -> bool:
        raise NotImplementedError

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        candidates = [field for field in fields(soup) if self.in_scope(field)]
        if not candidates:
            return not_applicable(self, self.empty_summary)

        items = [
            RelevanceItem(
                text=associated_text(field, soup) or "(aucun texte associé)",
                element_html=str(field)[:300],
                context=form_context(field, soup),
                details=field_description(field, soup),
            )
            for field in candidates
        ]
        verdicts = await judge_relevance(services, "format_instruction", items)
        outcomes = [
            make_outcome(
                verdict.status,
                identifier(field, soup),
                verdict.message(
                    "Le type ou le format attendu n'est pas indiqué dans l'étiquette ni dans un texte associé.",
                    "La présence d'une instruction de format pertinente reste à vérifier.",
                ),
                verdict.recommendation(
                    "Indiquer le format attendu dans l'étiquette (ex. « Date de naissance (jj/mm/aaaa) »)."
                ),
                node=field,
                associated_text=item.text[:200],
                **verdict.evidence,
            )
            for field, item, verdict in zip(candidates, items, verdicts, strict=True)
        ]
        return build_result(self, outcomes, empty_summary=self.empty_summary, noun="champ(s)")


class Test11105(_FormatInstructionTest):
    """11.10.5 : champ obligatoire dont le type ou le format est imposé."""

    test_id = "11.10.5"
    empty_summary = "Aucun champ obligatoire avec un type ou un format imposé."

    def in_scope(self, field: Tag) -> bool:
        return required(field) and has_format(field)


class Test11107(_FormatInstructionTest):
    """11.10.7 : champ en erreur (aria-invalid) dont le type ou le format est imposé."""

    test_id = "11.10.7"
    empty_summary = "Aucun champ en erreur avec un type ou un format imposé dans le DOM fourni."

    def in_scope(self, field: Tag) -> bool:
        return invalid(field) and has_format(field)

"""
RGAA 4.1.2 — critère 11.13 : la finalité d'un champ de saisie peut-elle être
déduite pour faciliter le remplissage automatique des champs avec les données
de l'utilisateur ?

11.13.1, pour chaque champ qui concerne l'utilisateur :
- le champ a un attribut autocomplete ;
- la valeur fait partie des valeurs autorisées (un seul « field name »,
  préfixes section-*, shipping/billing, et home/work/mobile/fax/pager
  uniquement devant tel*, email et impp) ;
- la valeur est pertinente au regard de l'information attendue.

Les libellés évidents (courriel, prénom, code postal…) sont reconnus sans IA ;
sinon l'IA juge si le champ concerne l'utilisateur et si la valeur est pertinente.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import (
    clean,
    field_description,
    fields,
    form_context,
    identifier,
    label_text,
    normalize,
)
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import example

# WCAG 2.1 — Identify Input Purpose : valeurs de finalité utilisateur.
PURPOSES = {
    "name", "honorific-prefix", "given-name", "additional-name", "family-name",
    "honorific-suffix", "nickname", "username", "new-password", "current-password",
    "organization-title", "organization", "street-address", "address-line1",
    "address-line2", "address-line3", "address-level4", "address-level3",
    "address-level2", "address-level1", "country", "country-name", "postal-code",
    "cc-name", "cc-given-name", "cc-additional-name", "cc-family-name",
    "cc-number", "cc-exp", "cc-exp-month", "cc-exp-year", "cc-csc", "cc-type",
    "transaction-currency", "transaction-amount", "language", "bday", "bday-day",
    "bday-month", "bday-year", "sex", "url", "photo", "tel", "tel-country-code",
    "tel-national", "tel-area-code", "tel-local", "tel-local-prefix", "tel-local-suffix",
    "tel-extension", "email", "impp",
}  # fmt: skip
CONTACT_TOKENS = {"home", "work", "mobile", "fax", "pager"}
CONTACT_PURPOSES = {"email", "impp"} | {purpose for purpose in PURPOSES if purpose.startswith("tel")}

# Libellés évidents : la finalité est reconnue sans IA.
LABEL_PURPOSES = {
    "email": "email", "e mail": "email", "courriel": "email", "adresse email": "email",
    "adresse e mail": "email", "votre email": "email", "votre courriel": "email",
    "prenom": "given-name", "votre prenom": "given-name", "nom de famille": "family-name",
    "code postal": "postal-code", "telephone": "tel", "numero de telephone": "tel",
    "date de naissance": "bday", "adresse postale": "street-address", "ville": "address-level2",
    "pays": "country-name", "mot de passe": "current-password",
}  # fmt: skip

_EXCLUDED_TYPES = {
    "hidden",
    "submit",
    "reset",
    "button",
    "image",
    "search",
    "checkbox",
    "radio",
    "file",
    "range",
    "color",
}


def parse_autocomplete(value: str) -> str | None:
    """Finalité (« field name ») d'une valeur autocomplete valide, sinon None."""
    tokens = clean(value).lower().split()
    if tokens and tokens[0].startswith("section-") and len(tokens[0]) > len("section-"):
        tokens.pop(0)
    if tokens and tokens[0] in {"shipping", "billing"}:
        tokens.pop(0)
    contact = None
    if tokens and tokens[0] in CONTACT_TOKENS:
        contact = tokens.pop(0)
    if len(tokens) != 1 or tokens[0] not in PURPOSES:
        return None
    if contact is not None and tokens[0] not in CONTACT_PURPOSES:
        return None
    return tokens[0]


# Finalité déduite du type du champ quand l'étiquette ne suffit pas.
_TYPE_PURPOSES = {"email": "email", "tel": "tel", "url": "url"}


def _deduced_purpose(field: Tag, raw: str, expected: str | None) -> str | None:
    """
    Finalité certaine sans IA : celle de l'étiquette (lexique), sinon le dernier mot d'une
    valeur mal formée s'il est une finalité valide (« work given-name » → given-name),
    sinon celle du type du champ (email, tel, url).
    """
    if expected:
        return expected
    tokens = raw.lower().split()
    if tokens and parse_autocomplete(tokens[-1]):
        return tokens[-1]
    return _TYPE_PURPOSES.get(clean(field.get("type")).lower())


def _autocomplete_example(field: Tag, purpose: str | None) -> str:
    return example(opening_tag(field), opening_tag(field, autocomplete=purpose)) if purpose else ""


class Test11131(RGAATest):
    """11.13.1 : chaque champ concernant l'utilisateur a-t-il un autocomplete valide et pertinent ?"""

    test_id = "11.13.1"
    criterion_id = "11.13"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.13.1 nécessite un DOM.")

        candidates = [
            field
            for field in fields(soup)
            if field.name in {"input", "select", "textarea"}
            and clean(field.get("type")).lower() not in _EXCLUDED_TYPES
            and field.find_parent(attrs={"role": "search"}) is None
        ]
        if not candidates:
            return not_applicable(self, "Aucun champ de saisie concerné.")

        # 1. Champs qui concernent l'utilisateur : lexique, sinon IA.
        user_fields: list[Tag] = []
        unknown: list[Tag] = []
        for field in candidates:
            if normalize(label_text(field, soup)) in LABEL_PURPOSES:
                user_fields.append(field)
            else:
                unknown.append(field)
        outcomes = []
        verdicts = await judge_relevance(services, "user_data_field", [self._item(field, soup) for field in unknown])
        for field, verdict in zip(unknown, verdicts, strict=True):
            if verdict.status is TestStatus.PASS:
                user_fields.append(field)
            elif verdict.status is not TestStatus.FAIL and parse_autocomplete(clean(field.get("autocomplete"))) is None:
                outcomes.append(
                    make_outcome(
                        verdict.status,
                        identifier(field, soup),
                        verdict.message("", "Impossible d'établir si le champ concerne l'utilisateur."),
                        "Si le champ recueille une donnée de l'utilisateur, ajouter l'attribut autocomplete adapté.",
                        node=field,
                        **verdict.evidence,
                    )
                )

        # 2. Présence et validité de la valeur (déterministe).
        to_check: list[Tag] = []
        for field in user_fields:
            raw = clean(field.get("autocomplete"))
            expected = LABEL_PURPOSES.get(normalize(label_text(field, soup)))
            if not raw or raw.lower() in {"on", "off"}:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        identifier(field, soup),
                        "Le champ concerne l'utilisateur mais n'a pas d'attribut autocomplete exploitable.",
                        "Ajouter l'attribut autocomplete qui correspond à la donnée demandée."
                        + _autocomplete_example(field, _deduced_purpose(field, raw, expected)),
                        node=field,
                        autocomplete=raw,
                    )
                )
            elif parse_autocomplete(raw) is None:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        identifier(field, soup),
                        f"La valeur autocomplete « {raw} » ne fait pas partie des valeurs autorisées.",
                        "Utiliser une valeur de la liste WCAG (ex. email, given-name, postal-code)."
                        + _autocomplete_example(field, _deduced_purpose(field, raw, expected)),
                        node=field,
                        autocomplete=raw,
                    )
                )
            elif expected is not None and parse_autocomplete(raw) == expected:
                outcomes.append(make_outcome(TestStatus.PASS))
            else:
                to_check.append(field)

        # 3. Pertinence de la valeur (IA), lorsqu'elle n'est pas évidente.
        verdicts = await judge_relevance(
            services, "autocomplete_value", [self._item(field, soup) for field in to_check]
        )
        for field, verdict in zip(to_check, verdicts, strict=True):
            raw = clean(field.get("autocomplete"))
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(field, soup),
                    verdict.message(
                        f"La valeur autocomplete « {raw} » ne correspond pas à l'information demandée.",
                        f"La pertinence de autocomplete « {raw} » reste à vérifier.",
                    ),
                    verdict.recommendation(
                        "Choisir la valeur autocomplete qui correspond exactement à la donnée demandée."
                    )
                    + _autocomplete_example(field, parse_autocomplete(verdict.suggestion or "")),
                    node=field,
                    autocomplete=raw,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun champ concernant l'utilisateur.", noun="champ(s)")

    @staticmethod
    def _item(field: Tag, soup: BeautifulSoup) -> RelevanceItem:
        return RelevanceItem(
            text=label_text(field, soup) or clean(field.get("name")) or "(sans étiquette)",
            element_html=str(field)[:300],
            context=form_context(field, soup),
            details=field_description(field, soup),
        )

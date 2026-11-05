"""RGAA 4.1.2 — critère 11.3 : cohérence des étiquettes répétées.

11.3.1 : même page ; 11.3.2 : ensemble de pages.
Une différence de libellé n'est pas nécessairement une non-conformité.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_labelledby_text,
    get_wrapping_label,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


@dataclass(frozen=True)
class _FieldLabel:
    page: str
    identifier: str
    function: str
    mechanism: str
    label: str


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.sub(r"[^\w]+", " ", without_accents).split())


# Equivalences explicites et restreintes : ne pas confondre synonymes et fonctions.
_EQUIVALENCES = {
    "email": {"email", "e mail", "courriel", "adresse email", "adresse e mail", "adresse electronique", "votre email", "votre adresse email", "votre courriel"},
    "phone": {"telephone", "numero de telephone", "tel", "votre telephone", "numero de tel"},
    "search": {"recherche", "rechercher", "chercher", "search", "recherche sur le site"},
    "first_name": {"prenom", "votre prenom", "first name"},
    "last_name": {"nom de famille", "votre nom de famille", "last name"},
    "name": {"nom", "votre nom", "name"},
    "postal_code": {"code postal", "votre code postal", "zip code"},
    "city": {"ville", "votre ville", "city"},
    "address": {"adresse postale", "adresse", "votre adresse", "postal address"},
    "url": {"url", "adresse web", "site web", "website"},
}
_EQUIVALENCE_LOOKUP = {
    _normalize(term): group
    for group, terms in _EQUIVALENCES.items()
    for term in terms
}


def _meaning(label: str) -> str | None:
    return _EQUIVALENCE_LOOKUP.get(_normalize(label))


def _function_key(field: Tag) -> str | None:
    """Identité probable d'une fonction, sans assimiler des choix radio distincts."""
    field_type = _clean(field.get("type", "text")).lower()
    if field.name == "input" and field_type in {"radio", "checkbox", "hidden"}:
        return None

    autocomplete = _clean(field.get("autocomplete", "")).lower()
    if autocomplete and autocomplete not in {"on", "off"}:
        # Conserver billing/shipping et les autres préfixes : fonctions distinctes.
        return f"autocomplete:{autocomplete}"

    name = _normalize(_clean(field.get("name", "")))
    if name and name not in {"field", "input", "value", "data"}:
        return f"name:{field.name}:{field_type}:{name}"

    if field.name == "input" and field_type in {"email", "tel", "search", "url"}:
        return f"type:{field_type}"
    return None


def _label_text(field: Tag, soup: BeautifulSoup) -> tuple[str, str]:
    """Résout un libellé accessible explicite, sans deviner le placeholder."""
    if field.has_attr("aria-labelledby"):
        valid, text = get_labelledby_text(field, soup)
        return "aria-labelledby", _clean(text) if valid else ""

    if field.has_attr("aria-label"):
        return "aria-label", _clean(field.get("aria-label"))

    field_id = _clean(field.get("id", ""))
    if field_id:
        labels = soup.find_all("label", attrs={"for": field_id})
        if len(labels) == 1:
            return "label-for", _clean(labels[0].get_text(" ", strip=True))
        if len(labels) > 1:
            return "label-for-ambiguous", ""

    wrapper = get_wrapping_label(field)
    if wrapper is not None:
        return "label-wrapper", _clean(wrapper.get_text(" ", strip=True))

    if field.has_attr("title"):
        return "title", _clean(field.get("title"))

    return "missing", ""


def _extract(page: str, soup: BeautifulSoup) -> list[_FieldLabel]:
    result = []
    for index, field in enumerate(find_form_fields(soup)):
        key = _function_key(field)
        if key is None:
            continue
        mechanism, label = _label_text(field, soup)
        result.append(
            _FieldLabel(
                page=page,
                identifier=get_element_identifier(field, index),
                function=key,
                mechanism=mechanism,
                label=label,
            )
        )
    return result


def _compare(
    test_id: str,
    criterion_id: str,
    entries: list[_FieldLabel],
    *,
    cross_page: bool,
    pages_count: int,
) -> TestResult:
    groups: dict[str, list[_FieldLabel]] = defaultdict(list)
    for entry in entries:
        groups[entry.function].append(entry)

    repeated = [
        group for group in groups.values()
        if len(group) >= 2
        and (not cross_page or len({item.page for item in group}) >= 2)
    ]
    checked = sum(len(group) for group in repeated)
    failed: list[Finding] = []
    uncertain: list[Finding] = []
    confirmed_groups = 0

    for group in repeated:
        labels = [item.label for item in group]
        normalized = {_normalize(label) for label in labels}
        meanings = [_meaning(label) for label in labels]
        if all(labels) and len(normalized) == 1:
            confirmed_groups += 1
            continue
        if all(labels) and all(meaning is not None for meaning in meanings):
            if len(set(meanings)) == 1:
                confirmed_groups += 1
                continue
            # Un même name ne prouve pas la même fonction : rester prudent.
            if not group[0].function.startswith("name:"):
                target = group[0]
                failed.append(
                    Finding(
                        element=f"{target.page} : {target.identifier}",
                        message=(
                            "Des champs identifiés comme ayant la même fonction "
                            "présentent des étiquettes décrivant des fonctions "
                            "différentes : "
                            + " / ".join(f"« {label} »" for label in labels) + "."
                        ),
                        recommendation=(
                            "Vérifier la fonction réelle de ces champs et harmoniser "
                            "les étiquettes des champs ayant la même fonction."
                        ),
                        evidence={
                            "function_key": target.function,
                            "labels": [
                                {"page": item.page, "element": item.identifier, "label": item.label}
                                for item in group
                            ],
                        },
                    )
                )
                continue

        target = group[0]
        uncertain.append(
            Finding(
                element=f"{target.page} : {target.identifier}",
                message=(
                    "La cohérence des étiquettes de champs potentiellement "
                    "équivalents ne peut pas être confirmée automatiquement : "
                    + " / ".join(f"« {label or '(vide)'} »" for label in labels) + "."
                ),
                recommendation=(
                    "Vérifier que ces champs remplissent la même fonction "
                    "et que leurs étiquettes sont cohérentes."
                ),
                evidence={
                    "function_key": target.function,
                    "labels": [
                        {"page": item.page, "element": item.identifier, "label": item.label}
                        for item in group
                    ],
                },
            )
        )

    status = (
        TestStatus.FAIL if failed else
        TestStatus.NEEDS_REVIEW if uncertain else
        TestStatus.PASS if repeated else TestStatus.NOT_APPLICABLE
    )
    summary = (
        f"{len(repeated)} groupe(s) de champs répétés, {checked} champ(s) concernés : "
        f"{len(failed)} incohérence(s) explicite(s), "
        f"{len(uncertain)} groupe(s) à vérifier, "
        f"{confirmed_groups} groupe(s) cohérent(s)."
        if repeated else
        "Aucun groupe de champs ayant une même fonction répétée n'a pu être identifié."
    )
    return TestResult(
        test_id=test_id,
        criterion_id=criterion_id,
        status=status,
        summary=summary,
        findings=failed + uncertain,
        tested_elements=checked,
        metadata={
            "pages_analyzed": pages_count,
            "repeated_groups": len(repeated),
            "confirmed_groups": confirmed_groups,
            "failed_groups": len(failed),
            "review_groups": len(uncertain),
            "grouping": "autocomplete, name/type, selected input types",
        },
    )


class Test1131(RGAATest):
    """11.3.1 : cohérence des étiquettes pour une même fonction sur la page."""

    test_id = "11.3.1"
    criterion_id = "11.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self, context: AuditContext, services: Any | None = None
    ) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.3.1 nécessite un DOM BeautifulSoup.")
        return _compare(
            self.test_id, self.criterion_id,
            _extract("page courante", soup),
            cross_page=False,
            pages_count=1,
        )


class Test1132(RGAATest):
    """11.3.2 : cohérence entre les pages d'un même ensemble.

    Contrat optionnel : context.page_doms = {"page_a.html": soup_a, ...}.
    Le moteur AccessiCode actuel ne renseigne pas cet attribut : tant qu'il
    n'est pas alimenté, le test ne conclut pas artificiellement à PASS.
    """

    test_id = "11.3.2"
    criterion_id = "11.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self, context: AuditContext, services: Any | None = None
    ) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.3.2 nécessite un DOM BeautifulSoup.")

        page_doms = getattr(context, "page_doms", None)
        if not isinstance(page_doms, dict) or len(page_doms) < 2:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NEEDS_REVIEW,
                summary=(
                    "Le contexte ne contient pas au moins deux DOM identifiés "
                    "appartenant à un même ensemble de pages : la cohérence "
                    "inter-pages ne peut pas être vérifiée."
                ),
                tested_elements=0,
                metadata={"pages_available": 0 if not isinstance(page_doms, dict) else len(page_doms)},
            )

        if not all(
            isinstance(page, str) and page.strip() and isinstance(dom, BeautifulSoup)
            for page, dom in page_doms.items()
        ):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NEEDS_REVIEW,
                summary="Certains DOM de l'ensemble de pages sont manquants ou invalides.",
                tested_elements=0,
            )

        entries = [
            entry
            for page, dom in page_doms.items()
            for entry in _extract(page, dom)
        ]
        return _compare(
            self.test_id, self.criterion_id, entries,
            cross_page=True,
            pages_count=len(page_doms),
        )

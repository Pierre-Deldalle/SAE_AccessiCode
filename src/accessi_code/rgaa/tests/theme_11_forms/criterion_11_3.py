"""
RGAA 4.1.2 — critère 11.3 : dans chaque formulaire, chaque étiquette associée
à un champ ayant la même fonction et répété plusieurs fois dans une même page
(11.3.1) ou dans un ensemble de pages (11.3.2) est-elle cohérente ?

Les champs sont regroupés par fonction (autocomplete, name, type). Des
étiquettes identiques (majuscules, accents et ponctuation ignorés) sont
cohérentes ; des étiquettes différentes sont jugées par l'IA.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_labelledby_text,
    get_wrapping_label,
)
from accessi_code.analysis.location import source_file_name
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable


@dataclass(frozen=True)
class _FieldLabel:
    page: str
    identifier: str
    function: str
    mechanism: str
    label: str
    # Champ dans le DOM de sa page, et fichier de cette page s'il n'est pas la page auditée.
    node: Tag | None = field(default=None, compare=False)
    file: str | None = None


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w]+", " ", without_accents).split())


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


def _extract(page: str, soup: BeautifulSoup, file: str | None = None) -> list[_FieldLabel]:
    result = []
    for index, tag in enumerate(find_form_fields(soup)):
        key = _function_key(tag)
        if key is None:
            continue
        mechanism, label = _label_text(tag, soup)
        result.append(
            _FieldLabel(
                page=page,
                identifier=get_element_identifier(tag, index),
                function=key,
                mechanism=mechanism,
                label=label,
                node=tag,
                file=file,
            )
        )
    return result


def _page_file(context: AuditContext, page: str) -> str:
    """Fichier d'une page de context.page_doms (clé : chemin relatif dans le site importé)."""
    if context.workspace_path is None:
        return page
    return source_file_name(context, context.workspace_path / "source" / page) or page


async def _compare(
    test: RGAATest,
    entries: list[_FieldLabel],
    services: Any | None,
    *,
    cross_page: bool,
    pages_count: int,
) -> TestResult:
    groups: dict[str, list[_FieldLabel]] = defaultdict(list)
    for entry in entries:
        # Une étiquette absente relève du critère 11.1, pas de la cohérence.
        if entry.label:
            groups[entry.function].append(entry)

    repeated = [
        group
        for group in groups.values()
        if len(group) >= 2 and (not cross_page or len({item.page for item in group}) >= 2)
    ]
    empty_summary = "Aucun groupe de champs ayant la même fonction n'a été identifié."
    if not repeated:
        return not_applicable(test, empty_summary)

    outcomes = []
    differing = []
    for group in repeated:
        if len({_normalize(item.label) for item in group}) == 1:
            outcomes.append(make_outcome(TestStatus.PASS))
        else:
            differing.append(group)

    items = [
        RelevanceItem(
            text=" / ".join(f"« {item.label} »" for item in group),
            context=" ; ".join(f"{item.page} : {item.identifier}" for item in group),
            details={"fonction": group[0].function},
        )
        for group in differing
    ]
    verdicts = await judge_relevance(services, "label_consistency", items)
    for group, item, verdict in zip(differing, items, verdicts, strict=True):
        target = group[0]
        outcomes.append(
            make_outcome(
                verdict.status,
                f"{target.page} : {target.identifier}",
                verdict.message(
                    f"Les étiquettes des champs de même fonction ne sont pas cohérentes : {item.text}.",
                    f"La cohérence des étiquettes {item.text} reste à vérifier.",
                ),
                verdict.recommendation("Harmoniser les étiquettes des champs qui ont la même fonction."),
                node=target.node,
                file=target.file,
                function_key=target.function,
                labels=[
                    {
                        "page": entry.page,
                        "element": entry.identifier,
                        "label": entry.label,
                        "file": entry.file,
                        "line": entry.node.sourceline if entry.node is not None else None,
                    }
                    for entry in group
                ],
                **verdict.evidence,
            )
        )
    return build_result(
        test,
        outcomes,
        empty_summary=empty_summary,
        noun="groupe(s) de champs",
        metadata={"pages_analyzed": pages_count, "repeated_groups": len(repeated)},
    )


class Test1131(RGAATest):
    """11.3.1 : cohérence des étiquettes pour une même fonction sur la page."""

    test_id = "11.3.1"
    criterion_id = "11.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.3.1 nécessite un DOM BeautifulSoup.")
        return await _compare(self, _extract("page courante", soup), services, cross_page=False, pages_count=1)


class Test1132(RGAATest):
    """11.3.2 : cohérence entre les pages d'un même ensemble.

    Contrat : context.page_doms = {"page_a.html": soup_a, ...}, rempli par
    AuditContextBuilder avec chaque page HTML importée. Avec moins de deux
    pages, le test ne conclut pas artificiellement à PASS.
    """

    test_id = "11.3.2"
    criterion_id = "11.3"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.3.2 nécessite un DOM BeautifulSoup.")

        page_doms = getattr(context, "page_doms", None)
        if not isinstance(page_doms, dict) or len(page_doms) < 2:
            available = len(page_doms) if isinstance(page_doms, dict) else 0
            if context.site_inventory_complete and available == 1:
                return not_applicable(self, "Le site ne comporte qu'une seule page.")
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary=(
                    "Une seule page a été fournie : importer les autres pages du site pour "
                    "vérifier la cohérence des étiquettes entre les pages."
                ),
                tested_elements=0,
                metadata={"pages_available": available},
            )

        if not all(
            isinstance(page, str) and page.strip() and isinstance(dom, BeautifulSoup) for page, dom in page_doms.items()
        ):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NEEDS_REVIEW,
                summary="Certains DOM de l'ensemble de pages sont manquants ou invalides.",
                tested_elements=0,
            )

        entries = [entry for page, dom in page_doms.items() for entry in _extract(page, dom, _page_file(context, page))]
        return await _compare(self, entries, services, cross_page=True, pages_count=len(page_doms))

"""Extraction DOM réutilisable des contrôles de formulaires (sans décision RGAA)."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import find_form_fields, get_element_identifier
from accessi_code.models.result import Finding, TestResult, TestStatus


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", clean(value).casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def fields(soup: BeautifulSoup) -> list[Tag]:
    return find_form_fields(soup)


def identifier(tag: Tag, soup: BeautifulSoup) -> str:
    return get_element_identifier(tag, list(soup.find_all(True)).index(tag))


def finding(tag: Tag, soup: BeautifulSoup, message: str, recommendation: str, **evidence: Any) -> Finding:
    return Finding(identifier(tag, soup), message, recommendation, evidence)


def result(test: Any, checked: int, failures: list[Finding] | None = None,
           reviews: list[Finding] | None = None, *, empty: str = "Aucun élément concerné.",
           metadata: dict[str, Any] | None = None) -> TestResult:
    failures, reviews = failures or [], reviews or []
    status = (TestStatus.FAIL if failures else TestStatus.NEEDS_REVIEW if reviews
              else TestStatus.PASS if checked else TestStatus.NOT_APPLICABLE)
    summary = (f"{checked} élément(s) contrôlé(s), {len(failures)} anomalie(s) certaine(s), "
               f"{len(reviews)} vérification(s) nécessaire(s)." if checked else empty)
    return TestResult(test.test_id, test.criterion_id, status, summary,
                      findings=failures + reviews, tested_elements=checked,
                      metadata=metadata or {})


def referenced_text(tag: Tag, soup: BeautifulSoup, attribute: str) -> str:
    ids = clean(tag.get(attribute)).split()
    if not ids:
        return ""
    texts = []
    for value in ids:
        matches = soup.find_all(id=value)
        if len(matches) != 1:
            return ""
        texts.append(matches[0].get_text(" ", strip=True))
    return clean(" ".join(texts))


def label_text(field: Tag, soup: BeautifulSoup) -> str:
    if field.has_attr("aria-labelledby"):
        return referenced_text(field, soup, "aria-labelledby")
    if field.has_attr("aria-label"):
        return clean(field.get("aria-label"))
    field_id = clean(field.get("id"))
    if field_id:
        labels = soup.find_all("label", attrs={"for": field_id})
        if len(labels) == 1:
            return labels[0].get_text(" ", strip=True)
    parent = field.find_parent("label")
    if parent:
        return parent.get_text(" ", strip=True)
    return clean(field.get("title"))


def associated_text(field: Tag, soup: BeautifulSoup) -> str:
    """Texte lié par label, aria-describedby ou aria-labelledby, sans inférer sa visibilité."""
    pieces = [label_text(field, soup), referenced_text(field, soup, "aria-describedby")]
    return clean(" ".join(pieces))


def group_candidates(soup: BeautifulSoup) -> list[list[Tag]]:
    """Groupes probables : radios partageant un name dans un même formulaire.

    Les autres regroupements demandent une interprétation fonctionnelle.
    """
    groups: dict[tuple[int, str], list[Tag]] = defaultdict(list)
    for tag in fields(soup):
        if (tag.name == "input" and clean(tag.get("type")).lower() == "radio") or clean(tag.get("role")) == "radio":
            name = clean(tag.get("name"))
            if name:
                form = tag.find_parent("form")
                groups[(id(form), name)].append(tag)
    return [group for group in groups.values() if len(group) > 1]


def common_group(fields_in_group: list[Tag]) -> Tag | None:
    if not fields_in_group:
        return None
    ancestors = [tag for tag in [fields_in_group[0], *fields_in_group[0].parents]
                 if isinstance(tag, Tag) and (tag.name == "fieldset" or tag.get("role") in {"group", "radiogroup"})]
    for ancestor in ancestors:
        if all(ancestor is field or ancestor in field.parents for field in fields_in_group):
            if ancestor.get("role") == "radiogroup" and not all(
                (field.name == "input" and field.get("type") == "radio") or field.get("role") == "radio"
                for field in fields_in_group
            ):
                continue
            return ancestor
    return None


def group_tags(soup: BeautifulSoup) -> list[Tag]:
    return [tag for tag in soup.find_all(True) if tag.name == "fieldset" or tag.get("role") in {"group", "radiogroup"}]


def group_legend(tag: Tag, soup: BeautifulSoup) -> str:
    if tag.name == "fieldset":
        legend = tag.find("legend", recursive=False)
        return legend.get_text(" ", strip=True) if legend else ""
    if tag.has_attr("aria-labelledby"):
        return referenced_text(tag, soup, "aria-labelledby")
    return clean(tag.get("aria-label"))


def buttons(soup: BeautifulSoup) -> list[Tag]:
    return [tag for tag in soup.find_all(["button", "input"]) if tag.find_parent("form") is not None
            and (tag.name == "button" or clean(tag.get("type")).lower() in {"submit", "reset", "button", "image"})]


def button_visible(tag: Tag) -> str:
    if tag.name == "button":
        return tag.get_text(" ", strip=True)
    if tag.get("type") == "image":
        return ""  # Texte d'image non déductible sans capture.
    return clean(tag.get("value"))


def button_name(tag: Tag, soup: BeautifulSoup) -> str:
    if tag.has_attr("aria-labelledby"):
        return referenced_text(tag, soup, "aria-labelledby")
    if tag.has_attr("aria-label"):
        return clean(tag.get("aria-label"))
    if tag.name == "button":
        return tag.get_text(" ", strip=True)
    if tag.get("type") == "image":
        return clean(tag.get("alt")) or clean(tag.get("title"))
    return clean(tag.get("value")) or clean(tag.get("title"))


def required(tag: Tag) -> bool:
    return tag.has_attr("required") or clean(tag.get("aria-required")).lower() == "true"


def invalid(tag: Tag) -> bool:
    return clean(tag.get("aria-invalid")).lower() == "true"


def has_format(tag: Tag) -> bool:
    return tag.has_attr("pattern") or clean(tag.get("type")).lower() in {"email", "url", "tel", "date", "time", "number"}


def hint(text: str) -> bool:
    text = normalize(text)
    return bool(re.search(r"\b(format|exemple|ex|caracteres|chiffres|jj|mm|aaaa|@|date|type|saisir|renseigner)\b", text))


def error_text(tag: Tag, soup: BeautifulSoup) -> str:
    """Retourne seulement un message d'erreur identifiable, pas une aide ordinaire.

    aria-describedby peut contenir des indications de format ou d'obligation :
    les traiter systématiquement comme des erreurs créait des faux positifs
    pour 11.10 et 11.11 (ex. « Les champs sont facultatifs. »).
    """
    if not invalid(tag):
        return ""
    explicit = referenced_text(tag, soup, "aria-errormessage")
    if explicit:
        return explicit
    for ref in clean(tag.get("aria-describedby")).split():
        matches = soup.find_all(id=ref)
        if len(matches) != 1:
            continue
        node = matches[0]
        value = clean(node.get_text(" ", strip=True))
        if node.get("role") in {"alert", "status"} or normalize(value).startswith(
            ("erreur", "incorrect", "invalide", "veuillez corriger")
        ):
            return value
    return ""

"""
RGAA 4.1.2 — critère 11.2 : chaque étiquette associée à un champ de formulaire
est-elle pertinente (hors cas particuliers) ?

- 11.2.1 à 11.2.4 : une étiquette vide est non conforme sans IA ; sinon l'IA
  juge si elle indique la fonction exacte du champ (type, name, autocomplete
  et contexte du formulaire fournis).
- 11.2.5 : l'intitulé visible est contenu dans chaque étiquette (comparaison
  déterministe ; majuscules et ponctuation ignorées, symboles à vérifier).
- 11.2.6 : pertinence du bouton adjacent servant d'étiquette visible (IA).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_labelledby_text,
    get_wrapping_label,
)
from accessi_code.analysis.forms import button_name, button_visible, field_description, form_context
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import example
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_1 import adjacent_button


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _labels(field: Tag, soup: BeautifulSoup) -> list[Tag]:
    """Récupère les labels explicites et englobants sans doublons."""
    labels: list[Tag] = []
    field_id = field.get("id")
    if isinstance(field_id, str) and field_id:
        for label in soup.find_all("label", attrs={"for": field_id}):
            if isinstance(label, Tag) and label not in labels:
                labels.append(label)
    wrapping = get_wrapping_label(field)
    if wrapping is not None and wrapping not in labels:
        labels.append(wrapping)
    return labels


def _normalized(text: str) -> str:
    # RGAA 11.2.5 : majuscules et ponctuation peuvent être ignorées.
    return " ".join(
        "".join(" " if unicodedata.category(char).startswith("P") else char for char in text.casefold()).split()
    )


def _finding(field: Tag, index: int, message: str, recommendation: str, **evidence: Any) -> Finding:
    return Finding(
        element=get_element_identifier(field, index),
        message=message,
        recommendation=recommendation,
        evidence=evidence,
    )


def _visible(label: Tag) -> bool | None:
    """Visible certain seulement dans des cas simples ; CSS externe inconnu."""
    if label.has_attr("hidden") or label.get("aria-hidden") == "true":
        return False
    style = re.sub(r"\s+", "", str(label.get("style", "")).lower())
    if "display:none" in style or "visibility:hidden" in style:
        return False
    classes = {str(value).lower() for value in label.get("class", [])}
    if classes & {"sr-only", "visually-hidden", "screen-reader-only"}:
        return None
    return True


class _LabelRelevanceTest(RGAATest):
    """Pertinence des étiquettes fournies par un mécanisme donné (11.2.1 à 11.2.4)."""

    criterion_id = "11.2"
    required_capabilities = frozenset({Capability.DOM})
    mechanism: str = ""

    def _candidates(self, field: Tag, soup: BeautifulSoup) -> list[str]:
        """Textes d'étiquette fournis par le mécanisme du test (chaque occurrence est jugée)."""
        if self.mechanism == "label":
            return [_text(label.get_text(" ", strip=True)) for label in _labels(field, soup)]
        if self.mechanism in {"title", "aria-label"}:
            return [_text(field.get(self.mechanism))] if field.has_attr(self.mechanism) else []
        if self.mechanism == "aria-labelledby":
            if not field.has_attr("aria-labelledby"):
                return []
            valid, value = get_labelledby_text(field, soup)
            return [value if valid else ""]
        return []

    def _suggestion_example(self, field: Tag, suggestion: str | None) -> str:
        """Proposition de l'IA écrite dans l'attribut du champ (title ou aria-label)."""
        if not suggestion or self.mechanism not in {"title", "aria-label"}:
            return ""
        return example(opening_tag(field), opening_tag(field, **{self.mechanism: suggestion}))

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        recommendation = "Rédiger une étiquette qui indique précisément la donnée attendue dans le champ."
        outcomes = []
        pending: list[tuple[Tag, int, str]] = []
        for index, field in enumerate(find_form_fields(soup)):
            for label in self._candidates(field, soup):
                if not label:
                    outcomes.append(
                        make_outcome(
                            TestStatus.FAIL,
                            get_element_identifier(field, index),
                            f"L'étiquette {self.mechanism} est vide ou référence un passage absent.",
                            recommendation,
                            node=field,
                        )
                    )
                else:
                    pending.append((field, index, label))

        if not outcomes and not pending:
            return not_applicable(self, f"Aucune étiquette {self.mechanism} dans la page.")

        items = [
            RelevanceItem(
                text=label,
                element_html=str(field)[:300],
                context=form_context(field, soup),
                details={"mécanisme": self.mechanism, **field_description(field, soup)},
            )
            for field, _, label in pending
        ]
        verdicts = await judge_relevance(services, "form_label", items)
        for (field, index, label), verdict in zip(pending, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    get_element_identifier(field, index),
                    verdict.message(
                        f"L'étiquette {self.mechanism} « {label[:100]} » n'indique pas la fonction du champ.",
                        f"La pertinence de l'étiquette {self.mechanism} « {label[:100]} » reste à vérifier.",
                    ),
                    verdict.recommendation(recommendation) + self._suggestion_example(field, verdict.suggestion),
                    node=field,
                    label=label,
                    **verdict.evidence,
                )
            )
        return build_result(
            self, outcomes, empty_summary=f"Aucune étiquette {self.mechanism} dans la page.", noun="étiquette(s)"
        )


class Test1121(_LabelRelevanceTest):
    """11.2.1 : contenu de chaque <label> associé à un champ."""

    test_id = "11.2.1"
    mechanism = "label"


class Test1122(_LabelRelevanceTest):
    """11.2.2 : contenu de chaque attribut title associé à un champ."""

    test_id = "11.2.2"
    mechanism = "title"


class Test1123(_LabelRelevanceTest):
    """11.2.3 : contenu de chaque attribut aria-label associé à un champ."""

    test_id = "11.2.3"
    mechanism = "aria-label"


class Test1124(_LabelRelevanceTest):
    """11.2.4 : passage de texte référencé par aria-labelledby."""

    test_id = "11.2.4"
    mechanism = "aria-labelledby"


class Test1125(RGAATest):
    """Vérifie l'inclusion de l'intitulé visible dans les étiquettes présentes."""

    test_id = "11.2.5"
    criterion_id = "11.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le critère 11.2 nécessite un DOM BeautifulSoup.")
        failed: list[Finding] = []
        uncertain: list[Finding] = []
        checked = 0
        for index, field in enumerate(find_form_fields(soup)):
            labels = _labels(field, soup)
            visible_labels = [label for label in labels if _visible(label) is True]
            if not visible_labels:
                # Une étiquette non détectable dans le HTML peut être visible via CSS/JS.
                if field.has_attr("aria-label") or field.has_attr("aria-labelledby"):
                    uncertain.append(
                        _finding(
                            field,
                            index,
                            "La présence d'un intitulé visible ne peut pas être établie depuis le DOM seul.",
                            "Comparer l'intitulé réellement affiché avec le nom accessible dans le navigateur.",
                        )
                    )
                    checked += 1
                continue
            checked += 1
            visible_text = " ".join(_text(label.get_text(" ", strip=True)) for label in visible_labels).strip()
            if not visible_text:
                uncertain.append(
                    _finding(
                        field,
                        index,
                        "Intitulé visible vide ou impossible à déterminer.",
                        "Vérifier visuellement l'intitulé et son nom accessible.",
                    )
                )
                continue
            candidates: list[tuple[str, str]] = []
            if field.has_attr("aria-label"):
                candidates.append(("aria-label", _text(field.get("aria-label"))))
            if field.has_attr("aria-labelledby"):
                valid, value = get_labelledby_text(field, soup)
                if not valid:
                    uncertain.append(
                        _finding(
                            field,
                            index,
                            "Référence aria-labelledby absente, vide ou ambiguë.",
                            "Corriger les références puis comparer l'intitulé visible.",
                            reference=field.get("aria-labelledby"),
                        )
                    )
                else:
                    candidates.append(("aria-labelledby", value))
            if field.has_attr("title"):
                candidates.append(("title", _text(field.get("title"))))
            candidates.extend(("label", _text(label.get_text(" ", strip=True))) for label in labels)
            for mechanism, text in candidates:
                source = _normalized(visible_text)
                target = _normalized(text)
                if not source or not target or source not in target:
                    # Les symboles isolés peuvent avoir un nom exprimant leur fonction.
                    if len(visible_text) <= 3 and not any(char.isalnum() for char in visible_text):
                        uncertain.append(
                            _finding(
                                field,
                                index,
                                f"Intitulé symbolique « {visible_text} » : exception RGAA à examiner.",
                                "Vérifier que le nom accessible exprime la fonction du symbole.",
                                mechanism=mechanism,
                                visible_label=visible_text,
                                accessible_label=text,
                            )
                        )
                    else:
                        failed.append(
                            _finding(
                                field,
                                index,
                                (
                                    f"L'étiquette {mechanism} « {text} » ne contient pas "
                                    f"l'intitulé visible « {visible_text} »."
                                ),
                                "Inclure l'intitulé visible dans le nom accessible, dans le même ordre.",
                                mechanism=mechanism,
                                visible_label=visible_text,
                                accessible_label=text,
                            )
                        )
        status = (
            TestStatus.FAIL
            if failed
            else TestStatus.NEEDS_REVIEW
            if uncertain
            else TestStatus.PASS
            if checked
            else TestStatus.NOT_APPLICABLE
        )
        return TestResult(
            self.test_id,
            self.criterion_id,
            status,
            f"{checked} champ(s) vérifié(s), {len(failed)} non-conformité(s), {len(uncertain)} point(s) à vérifier.",
            findings=failed + uncertain,
            tested_elements=checked,
            metadata={"failed": len(failed), "needs_review": len(uncertain)},
        )


class Test1126(RGAATest):
    """
    11.2.6 : le texte du bouton adjacent qui sert d'étiquette visible au champ
    est-il pertinent ? Concerne les champs sans <label> visible dont un bouton
    voisin tient lieu d'étiquette (par exemple un champ de recherche).
    """

    test_id = "11.2.6"
    criterion_id = "11.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le critère 11.2 nécessite un DOM BeautifulSoup.")

        candidates: list[tuple[Tag, int, str]] = []
        for index, field in enumerate(find_form_fields(soup)):
            if any(_visible(label) is True and label.get_text(strip=True) for label in _labels(field, soup)):
                continue
            button = adjacent_button(field)
            if button is None:
                continue
            text = button_visible(button) or button_name(button, soup)
            candidates.append((field, index, text))

        if not candidates:
            return not_applicable(self, "Aucun bouton adjacent servant d'étiquette visible.")

        recommendation = "Rédiger un intitulé de bouton qui indique aussi la fonction du champ (ex. « Rechercher »)."
        outcomes = [
            make_outcome(
                TestStatus.FAIL,
                get_element_identifier(field, index),
                "Le bouton adjacent qui sert d'étiquette n'a aucun intitulé.",
                recommendation,
                node=field,
            )
            for field, index, text in candidates
            if not text
        ]
        pending = [(field, index, text) for field, index, text in candidates if text]
        items = [
            RelevanceItem(
                text=text,
                element_html=str(field)[:300],
                context=form_context(field, soup),
                details={"rôle": "bouton adjacent servant d'étiquette visible", **field_description(field, soup)},
            )
            for field, _, text in pending
        ]
        verdicts = await judge_relevance(services, "form_label", items)
        for (field, index, text), verdict in zip(pending, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    get_element_identifier(field, index),
                    verdict.message(
                        f"Le bouton adjacent « {text[:100]} » n'indique pas la fonction du champ.",
                        f"La pertinence du bouton adjacent « {text[:100]} » comme étiquette reste à vérifier.",
                    ),
                    verdict.recommendation(recommendation),
                    node=field,
                    button_text=text,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun bouton adjacent servant d'étiquette.", noun="champ(s)")

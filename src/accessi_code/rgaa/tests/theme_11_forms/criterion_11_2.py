"""RGAA 4.1.2 — critère 11.2 : pertinence des étiquettes de formulaires.

La pertinence sémantique n'est pas déduite d'un simple texte non vide.
Les cas impossibles à établir depuis le DOM sont laissés à vérifier.
"""
from __future__ import annotations

import re
import unicodedata
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
        "".join(
            " " if unicodedata.category(char).startswith("P") else char
            for char in text.casefold()
        ).split()
    )


def _relevance(field: Tag, label: str) -> bool | None:
    """Certitude limitée : vide -> faux ; type/nom explicites -> vrai ; sinon inconnu."""
    if not _text(label):
        return False
    field_type = _text(field.get("type", "")).lower()
    known = {
        "email": ("e-mail", "email", "courriel", "adresse e-mail", "adresse email", "adresse électronique"),
        "tel": ("téléphone", "telephone", "numéro de téléphone"),
        "password": ("mot de passe", "password"),
        "search": ("recherche", "rechercher", "search"),
        "url": ("url", "adresse web", "site web", "lien web"),
    }
    if field.name == "input" and field_type in known:
        normalized = _normalized(label)
        # Un simple mot-clé contenu dans une phrase peut être trompeur :
        # n'accepter que des formulations canoniques complètes.
        accepted = {
            _normalized(term) for term in known[field_type]
        } | {
            _normalized(f"votre {term}") for term in known[field_type]
        }
        if normalized in accepted:
            return True
    normalized = _normalized(label)
    # Confirmations DOM à portée limitée : libellés canoniques, cohérents
    # avec les métadonnées du champ ou la nature explicite du formulaire.
    field_key = _normalized(field.get("name") or field.get("id") or "")
    canonical = {
        "nom": {"nom", "votre nom"},
        "prenom": {"prenom", "prénom", "votre prénom"},
        "message": {"message", "votre message"},
        "demande": {"demande", "demande rapide", "votre demande"},
        "email": {"email", "adresse email", "adresse e-mail", "courriel"},
        "q": {"rechercher sur le site", "recherche sur le site"},
    }
    if field_key in canonical and normalized in {_normalized(v) for v in canonical[field_key]}:
        if field_key != "q" or field.find_parent(attrs={"role": "search"}) is not None:
            return True
    if normalized in {"rechercher sur le site", "recherche sur le site"}:
        if field.find_parent(attrs={"role": "search"}) is not None:
            return True
    return None


def _finding(field: Tag, index: int, message: str, recommendation: str,
             **evidence: Any) -> Finding:
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
    required_capabilities = frozenset({Capability.DOM})
    mechanism: str = ""

    def _candidates(self, field: Tag, soup: BeautifulSoup) -> list[tuple[str, str]]:
        if self.mechanism == "label":
            return [("label", _text(label.get_text(" ", strip=True)))
                    for label in _labels(field, soup)]
        if self.mechanism == "title":
            # title ne fournit normalement le nom qu'en absence de mécanisme prioritaire.
            if not field.has_attr("title"):
                return []
            if field.has_attr("aria-labelledby") or field.has_attr("aria-label"):
                return []
            if _labels(field, soup):
                return []
            return [("title", _text(field.get("title")))]
        if self.mechanism == "aria-label":
            if not field.has_attr("aria-label") or field.has_attr("aria-labelledby"):
                return []
            return [("aria-label", _text(field.get("aria-label")))]
        if self.mechanism == "aria-labelledby":
            if not field.has_attr("aria-labelledby"):
                return []
            valid, value = get_labelledby_text(field, soup)
            return [("aria-labelledby", value if valid else "")]
        return []

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le critère 11.2 nécessite un DOM BeautifulSoup.")

        failed: list[Finding] = []
        uncertain: list[Finding] = []
        checked = 0
        passed = 0
        for index, field in enumerate(find_form_fields(soup)):
            candidates = self._candidates(field, soup)
            if not candidates:
                continue
            checked += 1
            for mechanism, label in candidates:
                relevance = _relevance(field, label)
                if relevance is False:
                    failed.append(_finding(
                        field, index,
                        f"L'étiquette {mechanism} est vide et n'indique pas la fonction du champ.",
                        "Fournir une étiquette décrivant précisément la fonction du champ.",
                        mechanism=mechanism, label=label,
                    ))
                elif relevance is None:
                    uncertain.append(_finding(
                        field, index,
                        f"La pertinence de l'étiquette {mechanism} « {label[:120]} » ne peut pas être établie depuis le DOM.",
                        "Vérifier que le libellé indique exactement la fonction du champ.",
                        mechanism=mechanism, label=label,
                    ))
                else:
                    passed += 1

        status = (TestStatus.FAIL if failed else TestStatus.NEEDS_REVIEW if uncertain
                  else TestStatus.PASS if checked else TestStatus.NOT_APPLICABLE)
        return TestResult(
            test_id=self.test_id, criterion_id=self.criterion_id, status=status,
            summary=(f"{checked} champ(s) concerné(s) : {len(failed)} anomalie(s) certaine(s), "
                     f"{len(uncertain)} vérification(s) manuelle(s), "
                     f"{passed} libellé(s) confirmé(s)." if checked
                     else f"Aucune étiquette {self.mechanism} concernée."),
            findings=failed + uncertain,
            tested_elements=checked,
            metadata={"mechanism": self.mechanism, "failed": len(failed),
                      "needs_review": len(uncertain), "confirmed_labels": passed},
        )


class Test1121(_LabelRelevanceTest):
    test_id = "11.2.1"
    criterion_id = "11.2"
    mechanism = "label"


class Test1122(_LabelRelevanceTest):
    test_id = "11.2.2"
    criterion_id = "11.2"
    mechanism = "title"


class Test1123(_LabelRelevanceTest):
    test_id = "11.2.3"
    criterion_id = "11.2"
    mechanism = "aria-label"


class Test1124(_LabelRelevanceTest):
    test_id = "11.2.4"
    criterion_id = "11.2"
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
                    uncertain.append(_finding(
                        field, index,
                        "La présence d'un intitulé visible ne peut pas être établie depuis le DOM seul.",
                        "Comparer l'intitulé réellement affiché avec le nom accessible dans le navigateur.",
                    ))
                    checked += 1
                continue
            checked += 1
            visible_text = " ".join(_text(label.get_text(" ", strip=True))
                                    for label in visible_labels).strip()
            if not visible_text:
                uncertain.append(_finding(
                    field, index, "Intitulé visible vide ou impossible à déterminer.",
                    "Vérifier visuellement l'intitulé et son nom accessible.",
                ))
                continue
            candidates: list[tuple[str, str]] = []
            if field.has_attr("aria-label"):
                candidates.append(("aria-label", _text(field.get("aria-label"))))
            if field.has_attr("aria-labelledby"):
                valid, value = get_labelledby_text(field, soup)
                if not valid:
                    uncertain.append(_finding(
                        field, index, "Référence aria-labelledby absente, vide ou ambiguë.",
                        "Corriger les références puis comparer l'intitulé visible.",
                        reference=field.get("aria-labelledby"),
                    ))
                else:
                    candidates.append(("aria-labelledby", value))
            if field.has_attr("title"):
                candidates.append(("title", _text(field.get("title"))))
            candidates.extend(("label", _text(label.get_text(" ", strip=True)))
                              for label in labels)
            for mechanism, text in candidates:
                source = _normalized(visible_text)
                target = _normalized(text)
                if not source or not target or source not in target:
                    # Les symboles isolés peuvent avoir un nom exprimant leur fonction.
                    if len(visible_text) <= 3 and not any(char.isalnum() for char in visible_text):
                        uncertain.append(_finding(
                            field, index,
                            f"Intitulé symbolique « {visible_text} » : exception RGAA à examiner.",
                            "Vérifier que le nom accessible exprime la fonction du symbole.",
                            mechanism=mechanism, visible_label=visible_text, accessible_label=text,
                        ))
                    else:
                        failed.append(_finding(
                            field, index,
                            f"L'étiquette {mechanism} « {text} » ne contient pas l'intitulé visible « {visible_text} ».",
                            "Inclure l'intitulé visible dans le nom accessible, dans le même ordre.",
                            mechanism=mechanism, visible_label=visible_text, accessible_label=text,
                        ))
        status = (TestStatus.FAIL if failed else TestStatus.NEEDS_REVIEW if uncertain
                  else TestStatus.PASS if checked else TestStatus.NOT_APPLICABLE)
        return TestResult(
            self.test_id, self.criterion_id, status,
            f"{checked} champ(s) vérifié(s), {len(failed)} non-conformité(s), "
            f"{len(uncertain)} point(s) à vérifier.",
            findings=failed + uncertain, tested_elements=checked,
            metadata={"failed": len(failed), "needs_review": len(uncertain)},
        )


class Test1126(RGAATest):
    """Pertinence du bouton adjacent qui sert d'étiquette visible."""
    test_id = "11.2.6"
    criterion_id = "11.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le critère 11.2 nécessite un DOM BeautifulSoup.")
        findings: list[Finding] = []
        checked = 0
        for index, field in enumerate(find_form_fields(soup)):
            neighbors = [field.find_previous_sibling(), field.find_next_sibling()]
            buttons = [node for node in neighbors if isinstance(node, Tag)
                       and (node.name == "button" or
                            (node.name == "input" and node.get("type") in {"submit", "button", "image"}))]
            if not buttons:
                continue
            checked += 1
            for button in buttons:
                text = _text(button.get_text(" ", strip=True)) if button.name == "button" else _text(
                    button.get("value") or button.get("alt")
                )
                findings.append(_finding(
                    field, index,
                    f"Bouton adjacent « {text} » : son rôle d'étiquette et sa pertinence nécessitent une vérification visuelle.",
                    "Vérifier si le bouton sert d'étiquette visible et si son contenu indique la fonction exacte du champ.",
                    button=str(button)[:250], button_text=text,
                ))
        status = TestStatus.NEEDS_REVIEW if checked else TestStatus.NOT_APPLICABLE
        return TestResult(
            self.test_id, self.criterion_id, status,
            (f"{checked} champ(s) avec bouton adjacent potentiel : vérification visuelle nécessaire."
             if checked else "Aucun bouton adjacent susceptible de servir d'étiquette détecté."),
            findings=findings, tested_elements=checked,
            metadata={"candidate_fields": checked},
        )

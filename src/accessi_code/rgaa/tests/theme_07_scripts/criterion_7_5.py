"""
RGAA 4.1.2 — critère 7.5 : dans chaque page web, les messages de statut
sont-ils correctement restitués par les technologies d'assistance ?

- 7.5.1 : réussite, résultat d'une action ou état d'une application → rôle status ;
- 7.5.2 : suggestion ou avertissement d'erreur → rôle alert ;
- 7.5.3 : progression d'un processus → rôle log, progressbar ou status.

Les propriétés équivalentes admises par le RGAA sont acceptées
(aria-live="polite" + aria-atomic="true" pour status, aria-live="assertive"
+ aria-atomic="true" pour alert, aria-live="polite" pour log), ainsi que les
rôles implicites des éléments ``<output>`` (status) et ``<progress>`` (progressbar).

Candidats : zones déjà déclarées comme régions dynamiques et textes contenant
un mot-clé de la catégorie (pré-filtre).

- marquage attendu présent → PASS, sans IA ;
- sinon l'IA dit si le passage est un message de statut de la catégorie :
  oui → FAIL (rôle manquant), non → NOT_APPLICABLE, incertain → NEEDS_REVIEW.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.ai.schemas import StructureCandidate
from accessi_code.analysis.structure import HEADING_TAGS
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_structure
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

# Éléments qui ne sont jamais des messages de statut (titres, libellés, métadonnées…).
NON_MESSAGE_TAGS = frozenset(
    {
        "html",
        "body",
        "script",
        "style",
        "noscript",
        "template",
        "head",
        "meta",
        "title",
        "desc",
        "label",
        "legend",
        "caption",
        "th",
        "option",
        "button",
        "a",
        "code",
        "pre",
        *HEADING_TAGS,
    }
)

LIVE_ROLES = frozenset({"status", "alert", "log", "progressbar"})

SUCCESS_WORDS = re.compile(
    r"(?<!\w)(?:succès|réussie?s?|effectuée?s?|enregistrée?s?|envoyée?s?|ajoutée?s?|supprimée?s?"
    r"|terminée?s?|confirmée?s?|validée?s?|\d+\s+résultats?|aucun résultat"
    r"|successful|saved|sent|added|completed)(?!\w)",
    re.IGNORECASE,
)
ERROR_WORDS = re.compile(
    r"(?<!\w)(?:erreurs?|error|échoué|échec|invalide|incorrecte?|obligatoire|manquante?|trop (?:court|long)e?"
    r"|avertissement|warning|attention|veuillez|failed|invalid|required)(?!\w)",
    re.IGNORECASE,
)
PROGRESS_WORDS = re.compile(
    r"(?<!\w)(?:en cours|chargement|loading|traitement|processing|progression|progress|patientez|veuillez patienter"
    r"|étape\s+\d+|step\s+\d+|\d+\s*%)(?!\w)",
    re.IGNORECASE,
)


def normalize(value: str) -> str:
    return " ".join(value.split())


def own_text(element: Tag) -> str:
    """Texte porté directement par l'élément, sans celui de ses enfants."""
    return normalize(" ".join(str(part) for part in element.children if isinstance(part, NavigableString)))


def live_role(element: Tag) -> str:
    """Rôle de région dynamique, explicite ou implicite (output, progress)."""
    role = str(element.get("role") or "").strip().lower()
    if role:
        return role
    return {"output": "status", "progress": "progressbar"}.get(element.name, "")


def live_markers(element: Tag) -> tuple[str, str, str]:
    return (
        live_role(element),
        str(element.get("aria-live") or "").strip().lower(),
        str(element.get("aria-atomic") or "").strip().lower(),
    )


def is_live_region(element: Tag) -> bool:
    role, live, _ = live_markers(element)
    return role in LIVE_ROLES or live in {"polite", "assertive"}


def element_identifier(element: Tag, index: int) -> str:
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return f"{element.name}#{element_id.strip()}"
    classes = element.get("class")
    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(name) for name in classes[:2])}"
    return f"{element.name}[index={index}]"


class StatusMessageTest(RGAATest):
    """Base commune des trois catégories de messages de statut."""

    criterion_id = "7.5"
    required_capabilities = frozenset({Capability.DOM})

    kind: ClassVar[str]
    keywords: ClassVar[re.Pattern[str]]
    expected: ClassVar[str]
    empty_summary: ClassVar[str]
    fail_message: ClassVar[str]
    uncertain_message: ClassVar[str]
    recommendation: ClassVar[str]

    def accepts(self, role: str, live: str, atomic: str) -> bool:
        raise NotImplementedError

    def candidates(self, soup: BeautifulSoup) -> list[Tag]:
        found: list[Tag] = []
        for element in soup.find_all(True):
            if element.name in NON_MESSAGE_TAGS or element.find_parent(["head", "script", "template"]):
                continue
            if is_live_region(element) or self.keywords.search(own_text(element)):
                found.append(element)
        # Une région dynamique englobe ses enfants : on ne garde pas un enfant
        # déjà couvert par une région candidate.
        regions = [element for element in found if is_live_region(element)]
        return [
            element
            for element in found
            if is_live_region(element) or not any(region in element.parents for region in regions)
        ]

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        elements = self.candidates(context.dom)
        if not elements:
            return not_applicable(self, self.empty_summary)

        outcomes: list[Outcome | None] = [None] * len(elements)
        to_judge: list[int] = []
        for index, element in enumerate(elements):
            if self.accepts(*live_markers(element)):
                outcomes[index] = make_outcome(TestStatus.PASS)
            else:
                to_judge.append(index)

        items = [
            StructureCandidate(
                text=normalize(elements[index].get_text(" ", strip=True))[:300] or "(région vide)",
                element_html=str(elements[index])[:400],
                context=_context(elements[index]),
            )
            for index in to_judge
        ]
        verdicts = await judge_structure(services, self.kind, items)
        for index, item, verdict in zip(to_judge, items, verdicts, strict=True):
            role, live, atomic = live_markers(elements[index])
            outcomes[index] = make_outcome(
                verdict.status,
                element_identifier(elements[index], index),
                verdict.message(self.fail_message, self.uncertain_message),
                self.recommendation,
                text=item.text,
                role=role,
                aria_live=live,
                aria_atomic=atomic,
                expected=self.expected,
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=self.empty_summary,
            noun="message(s) de statut",
        )


def _context(element: Tag) -> str:
    role, live, atomic = live_markers(element)
    markers = ", ".join(part for part in (f"role={role}" if role else "", f"aria-live={live}" if live else "") if part)
    parent = element.parent if isinstance(element.parent, Tag) else None
    around = normalize(parent.get_text(" ", strip=True))[:250] if parent is not None else ""
    return " — ".join(
        part
        for part in (
            f"Marquage actuel : {markers}" if markers else "Aucun marquage de région dynamique",
            f"aria-atomic={atomic}" if atomic else "",
            f"Contenu autour : {around}" if around else "",
        )
        if part
    )


class Test751(StatusMessageTest):
    """7.5.1 : messages de réussite, de résultat ou d'état → rôle status."""

    test_id = "7.5.1"
    kind = "status_success"
    keywords = SUCCESS_WORDS
    expected = 'role="status"'
    empty_summary = "Aucun message de statut de réussite, de résultat ou d'état."
    fail_message = "Ce message de statut (réussite, résultat ou état) n'a pas le rôle status."
    uncertain_message = (
        "Vérifier si ce passage est un message de statut (réussite, résultat ou état) et s'il a le rôle status."
    )
    recommendation = 'Ajouter role="status" (ou aria-live="polite" et aria-atomic="true") sur le conteneur du message.'

    def accepts(self, role: str, live: str, atomic: str) -> bool:
        return role == "status" or (live == "polite" and atomic == "true")


class Test752(StatusMessageTest):
    """7.5.2 : suggestions et avertissements d'erreur → rôle alert."""

    test_id = "7.5.2"
    kind = "status_error"
    keywords = ERROR_WORDS
    expected = 'role="alert"'
    empty_summary = "Aucun message de statut de suggestion ou d'erreur."
    fail_message = "Ce message de statut (suggestion ou erreur) n'a pas le rôle alert."
    uncertain_message = (
        "Vérifier si ce passage est un message de statut (suggestion ou erreur) et s'il a le rôle alert."
    )
    recommendation = (
        'Ajouter role="alert" (ou aria-live="assertive" et aria-atomic="true") sur le conteneur du message.'
    )

    def accepts(self, role: str, live: str, atomic: str) -> bool:
        return role == "alert" or (live == "assertive" and atomic == "true")


class Test753(StatusMessageTest):
    """7.5.3 : progression d'un processus → rôle log, progressbar ou status."""

    test_id = "7.5.3"
    kind = "status_progress"
    keywords = PROGRESS_WORDS
    expected = 'role="log", role="progressbar" ou role="status"'
    empty_summary = "Aucun message de statut de progression."
    fail_message = "Ce message de progression n'a ni le rôle log, ni progressbar, ni status."
    uncertain_message = "Vérifier si ce passage indique la progression d'un processus et s'il a le rôle adapté."
    recommendation = 'Ajouter role="log", role="progressbar" ou role="status" (ou aria-live="polite") sur le message.'

    def accepts(self, role: str, live: str, atomic: str) -> bool:
        return role in {"log", "progressbar", "status"} or live == "polite"

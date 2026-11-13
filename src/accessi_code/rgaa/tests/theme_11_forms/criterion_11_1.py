"""
RGAA 4.1.2 — critère 11.1 : chaque champ de formulaire a-t-il une étiquette ?

- 11.1.1 : présence d'une étiquette (aria-labelledby, aria-label, label[for],
  title, ou bouton adjacent servant d'étiquette visible avec un nom accessible).
- 11.1.2 : chaque label[for] est associé à un champ dont l'id est unique et égal à for.
- 11.1.3 : un champ dont l'étiquette n'est pas visible (aria-label, label masqué)
  ou n'est pas accolée (aria-labelledby vers un passage éloigné) possède un
  title, ou un passage de texte visible accolé.

Ces tests sont déterministes : la pertinence des étiquettes relève de 11.2.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.dom import find_form_fields, get_element_identifier, get_labelledby_text
from accessi_code.analysis.forms import clean, identifier
from accessi_code.analysis.structure import is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

_HIDDEN_CLASSES = {"sr-only", "visually-hidden", "screen-reader-only", "sr-only-focusable", "hidden"}
_BUTTON_TYPES = {"submit", "button", "image", "reset"}


def _dom(context: AuditContext, test_id: str) -> BeautifulSoup:
    if not isinstance(context.dom, BeautifulSoup):
        raise ValueError(f"Le test {test_id} nécessite un DOM.")
    return context.dom


def labels_for(field: Tag, soup: BeautifulSoup) -> list[Tag]:
    """Balises label[for] désignant l'id du champ (plusieurs labels sont autorisés en HTML)."""
    field_id = clean(field.get("id"))
    if not field_id:
        return []
    return [label for label in soup.find_all("label", attrs={"for": field_id})]


def label_hidden(label: Tag) -> bool:
    classes = {str(value).lower() for value in label.get("class") or []}
    return is_hidden(label) or bool(classes & _HIDDEN_CLASSES)


def adjacent_button(field: Tag) -> Tag | None:
    for sibling in (field.find_next_sibling(), field.find_previous_sibling()):
        if isinstance(sibling, Tag) and (
            sibling.name == "button"
            or (sibling.name == "input" and clean(sibling.get("type")).lower() in _BUTTON_TYPES)
        ):
            return sibling
    return None


def adjacent_text(field: Tag) -> str:
    """Texte visible immédiatement voisin du champ (dans le même conteneur)."""
    for node in (field.previous_sibling, field.next_sibling):
        text = ""
        if isinstance(node, Tag):
            if node.name in {"input", "select", "textarea", "button"} or is_hidden(node):
                continue
            text = node.get_text(" ", strip=True)
        elif node is not None:
            text = str(node).strip()
        if text:
            return text
    return ""


def labeling_mechanisms(field: Tag, soup: BeautifulSoup) -> list[str]:
    """Mécanismes d'étiquetage du test 11.1.1 présents sur le champ."""
    found: list[str] = []
    valid, _ = get_labelledby_text(field, soup)
    if valid:
        found.append("aria-labelledby")
    if clean(field.get("aria-label")):
        found.append("aria-label")
    if any(label.get_text(" ", strip=True) for label in labels_for(field, soup)):
        found.append("label-for")
    if clean(field.get("title")):
        found.append("title")
    return found


class Test1111(RGAATest):
    """11.1.1 : chaque champ de formulaire a-t-il une étiquette ?"""

    test_id = "11.1.1"
    criterion_id = "11.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        fields = find_form_fields(soup)
        if not fields:
            return not_applicable(self, "Aucun champ de formulaire détecté.")

        outcomes = []
        for field in fields:
            mechanisms = labeling_mechanisms(field, soup)
            if mechanisms:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(field, soup),
                    "Le champ n'a aucune étiquette (aria-labelledby, aria-label, label for ou title).",
                    'Associer une étiquette au champ, par exemple <label for="id-du-champ">.',
                    wrapping_label=field.find_parent("label") is not None,
                    adjacent_button=adjacent_button(field) is not None,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun champ de formulaire.", noun="champ(s)")


class Test1112(RGAATest):
    """11.1.2 : chaque label[for] est-il associé à un champ dont l'id est unique et égal à for ?"""

    test_id = "11.1.2"
    criterion_id = "11.1"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        labels = [label for label in soup.find_all("label") if label.has_attr("for")]
        if not labels:
            return not_applicable(self, "Aucune balise <label> avec un attribut for.")

        field_ids = {id(field) for field in find_form_fields(soup)}
        outcomes = []
        for label in labels:
            target = clean(label.get("for"))
            matches = soup.find_all(id=target) if target else []
            problem = ""
            if not target:
                problem = "L'attribut for du label est vide."
            elif not matches:
                problem = f"Aucun champ ne possède l'identifiant « {target} » désigné par le label."
            elif len(matches) > 1:
                problem = f"L'identifiant « {target} » n'est pas unique dans la page."
            elif id(matches[0]) not in field_ids:
                problem = f"L'élément d'identifiant « {target} » n'est pas un champ de formulaire."
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    identifier(label, soup),
                    problem,
                    "Donner au champ un id unique et le reporter dans l'attribut for du label.",
                    label=label.get_text(" ", strip=True)[:100],
                )
                if problem
                else make_outcome(TestStatus.PASS)
            )
        return build_result(self, outcomes, empty_summary="Aucun label for.", noun="étiquette(s)")


class Test1113(RGAATest):
    """
    11.1.3 : chaque champ dont l'étiquette n'est pas visible ou pas accolée
    possède-t-il un title ou un passage de texte visible accolé ?
    """

    test_id = "11.1.3"
    criterion_id = "11.1"
    required_capabilities = frozenset({Capability.DOM})
    optional_capabilities = frozenset({Capability.BROWSER_INTERACTION})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = _dom(context, self.test_id)
        outcomes = []
        for index, field in enumerate(find_form_fields(soup)):
            reason = self._invisible_label_reason(field, soup)
            if reason is None:
                continue
            if clean(field.get("title")) or adjacent_text(field):
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            # Clé identique à celle de analysis/form_layout.py (rang parmi les champs).
            layout = (context.form_label_layout or {}).get(get_element_identifier(field, index), {})
            if layout.get("verified") is True and layout.get("adjacent") is True:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            status = TestStatus.NEEDS_REVIEW if reason == "aria-labelledby" else TestStatus.FAIL
            outcomes.append(
                make_outcome(
                    status,
                    identifier(field, soup),
                    {
                        "aria-label": "L'étiquette n'est fournie que par aria-label (invisible), sans title ni texte "
                        "visible accolé.",
                        "hidden-label": "L'étiquette est masquée, et le champ n'a ni title ni texte visible accolé.",
                        "aria-labelledby": "L'étiquette référencée par aria-labelledby n'est pas accolée au champ ; "
                        "sa proximité visuelle doit être vérifiée.",
                    }[reason],
                    "Ajouter un attribut title explicite ou un texte visible accolé au champ.",
                    reason=reason,
                )
            )
        return build_result(
            self, outcomes, empty_summary="Aucun champ avec une étiquette invisible ou éloignée.", noun="champ(s)"
        )

    @staticmethod
    def _invisible_label_reason(field: Tag, soup: BeautifulSoup) -> str | None:
        labels = labels_for(field, soup)
        wrapping = field.find_parent("label")
        visible_labels = [label for label in [*labels, wrapping] if isinstance(label, Tag) and not label_hidden(label)]
        if visible_labels:
            return None
        if clean(field.get("aria-labelledby")):
            valid, _ = get_labelledby_text(field, soup)
            if valid and not _labelledby_adjacent(field, soup):
                return "aria-labelledby"
            return None
        if labels or wrapping is not None:
            return "hidden-label"
        if clean(field.get("aria-label")):
            return "aria-label"
        return None


def _labelledby_adjacent(field: Tag, soup: BeautifulSoup) -> bool:
    """Le passage référencé est-il un voisin immédiat du champ (ou de son conteneur direct) ?"""
    neighbours = {
        id(node)
        for node in (
            field.find_previous_sibling(),
            field.find_next_sibling(),
            field.parent.find_previous_sibling() if isinstance(field.parent, Tag) else None,
        )
        if node is not None
    }
    for ref in clean(field.get("aria-labelledby")).split():
        target = soup.find(id=ref)
        if target is not None and (id(target) in neighbours or target is field.parent):
            return True
    return False

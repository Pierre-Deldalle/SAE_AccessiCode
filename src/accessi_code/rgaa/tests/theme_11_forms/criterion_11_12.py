"""
RGAA 4.1.2 — critère 11.12 : pour chaque formulaire qui modifie ou supprime
des données, ou qui transmet des réponses à un test ou à un examen, ou dont
la validation a des conséquences financières ou juridiques, les données
saisies peuvent-elles être modifiées, mises à jour ou récupérées ?

1. Périmètre : une vérification documentée (``form_transaction_evidence``)
   prime ; les formulaires de recherche sont exclus ; sinon l'IA juge la nature
   du formulaire à partir de son titre, de ses champs et de ses boutons.
2. Mécanismes visibles dans la page : case de confirmation explicite, étape
   de vérification, possibilité d'annuler ou de modifier. Sans mécanisme
   visible, la vérification après validation reste nécessaire.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.forms import button_name, clean, form_summary, identifier, label_text
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

_CONFIRMATION = re.compile(r"confirm|j'accepte|je certifie|je reconnais|je valide|j'atteste", re.IGNORECASE)
_REVIEW_STEP = re.compile(
    r"vérifier|récapitulatif|étape suivante|suivant|aperçu|modifier|annuler|corriger", re.IGNORECASE
)


def is_search_form(form: Tag) -> bool:
    if clean(form.get("role")).lower() == "search" or form.find_parent(attrs={"role": "search"}):
        return True
    inputs = [
        tag for tag in form.find_all(["input", "select", "textarea"]) if clean(tag.get("type")).lower() != "hidden"
    ]
    texts = [tag for tag in inputs if clean(tag.get("type")).lower() not in {"submit", "button", "image", "reset"}]
    return bool(texts) and all(clean(tag.get("type")).lower() == "search" for tag in texts)


def visible_mechanisms(form: Tag, soup: BeautifulSoup) -> list[str]:
    """Mécanismes de confirmation ou de correction présents dans le formulaire."""
    found = []
    for box in form.find_all("input", attrs={"type": "checkbox"}):
        if _CONFIRMATION.search(label_text(box, soup)):
            found.append("confirmation explicite (case à cocher)")
            break
    controls = [button_name(tag, soup) for tag in form.find_all(["button", "input"])]
    controls += [link.get_text(" ", strip=True) for link in form.find_all("a")]
    if any(_REVIEW_STEP.search(text or "") for text in controls):
        found.append("étape de vérification ou de correction")
    return found


class _TransactionTest(RGAATest):
    criterion_id = "11.12"
    required_capabilities = frozenset({Capability.DOM})
    scope_kind: ClassVar[str]
    scope_key: ClassVar[str]
    proof_keys: ClassVar[tuple[str, ...]]

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        forms = [(index, form) for index, form in enumerate(soup.find_all("form")) if not is_search_form(form)]
        if not forms:
            return not_applicable(self, "Aucun formulaire concerné (hors recherche).")

        proofs = context.form_transaction_evidence if isinstance(context.form_transaction_evidence, Mapping) else {}
        outcomes = []
        to_judge = []
        in_scope = []
        for index, form in forms:
            proof = proofs.get(index)
            if isinstance(proof, Mapping) and isinstance(proof.get(self.scope_key), bool):
                if proof[self.scope_key]:
                    in_scope.append((index, form, proof))
                continue
            to_judge.append((index, form))

        items = [RelevanceItem(text=form_summary(form, soup)) for _, form in to_judge]
        verdicts = await judge_relevance(services, self.scope_kind, items)
        for (index, form), verdict in zip(to_judge, verdicts, strict=True):
            if verdict.status is TestStatus.PASS:
                in_scope.append((index, form, {}))
            elif verdict.status is not TestStatus.FAIL:
                outcomes.append(
                    make_outcome(
                        verdict.status,
                        identifier(form, soup),
                        verdict.message(
                            "", "La nature du formulaire (conséquences, données modifiées) reste à vérifier."
                        ),
                        "Vérifier si la validation du formulaire a des conséquences financières, juridiques ou "
                        "modifie des données.",
                        node=form,
                        **verdict.evidence,
                    )
                )

        for index, form, proof in in_scope:
            outcomes.append(self._mechanism_outcome(form, soup, proof, index))
        return build_result(self, outcomes, empty_summary="Aucun formulaire dans le périmètre.", noun="formulaire(s)")

    def _mechanism_outcome(self, form: Tag, soup: BeautifulSoup, proof: Mapping, index: int):
        values = [proof.get(key) for key in self.proof_keys]
        if any(value is True for value in values):
            return make_outcome(TestStatus.PASS)
        if values and all(value is False for value in values):
            return make_outcome(
                TestStatus.FAIL,
                identifier(form, soup),
                "Aucun mécanisme de correction, de récupération ou de confirmation n'est disponible "
                "(vérification documentée).",
                "Ajouter une confirmation explicite, une étape de vérification ou un moyen d'annuler ou de récupérer.",
                node=form,
                form_index=index,
            )
        mechanisms = visible_mechanisms(form, soup)
        if mechanisms:
            return make_outcome(TestStatus.PASS)
        return make_outcome(
            TestStatus.NEEDS_REVIEW,
            identifier(form, soup),
            "Aucun mécanisme de confirmation ou de correction n'est visible dans la page : vérifier ce qui est "
            "proposé après la validation du formulaire.",
            "Ajouter une case de confirmation explicite ou une étape de vérification avant validation.",
            node=form,
            form_index=index,
        )


class Test11121(_TransactionTest):
    """11.12.1 : données modifiables, vérifiables ou confirmation explicite."""

    test_id = "11.12.1"
    scope_kind = "transaction_scope"
    scope_key = "in_scope"
    proof_keys = ("reversible", "review_and_correct", "explicit_confirmation")


class Test11122(_TransactionTest):
    """11.12.2 : données financières, juridiques ou personnelles récupérables ou confirmation explicite."""

    test_id = "11.12.2"
    scope_kind = "sensitive_data_modification"
    scope_key = "modifies_sensitive_data"
    proof_keys = ("recoverable", "explicit_confirmation")

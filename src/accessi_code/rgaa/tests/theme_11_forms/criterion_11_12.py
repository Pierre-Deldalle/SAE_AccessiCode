"""RGAA 11.12 — prévention des erreurs lors d'actions sensibles.

La portée d'une transaction ne se déduit pas de son attribut action/method.
Le contexte peut recevoir ``form_transaction_evidence`` issu d'un contrôle
fonctionnel vérifié, sous forme de mapping index_formulaire -> preuves.
"""
from __future__ import annotations

from collections.abc import Mapping

from accessi_code.analysis.forms import finding, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class _TransactionTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})
    financial_personal_only = False

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        forms = soup.find_all("form")
        proofs = getattr(context, "form_transaction_evidence", None)
        failures, reviews = [], []
        applicable = 0
        for index, form in enumerate(forms):
            proof = proofs.get(index) if isinstance(proofs, Mapping) else None
            if not isinstance(proof, Mapping) or not isinstance(proof.get("in_scope"), bool):
                reviews.append(finding(form, soup,
                    "La nature juridique, financière ou personnelle de l'action n'est pas déterminable depuis le DOM.",
                    "Vérifier l'effet de la validation du formulaire et les mécanismes de correction.", form_index=index))
                continue
            if not proof["in_scope"]:
                continue
            if self.financial_personal_only and proof.get("modifies_sensitive_data") is not True:
                if proof.get("modifies_sensitive_data") is None:
                    reviews.append(finding(form, soup,
                        "Vérifier si le formulaire modifie des données financières, juridiques ou personnelles.",
                        "Documenter la portée de la transaction.", form_index=index))
                continue
            applicable += 1
            keys = ("recoverable", "explicit_confirmation") if self.financial_personal_only else (
                "reversible", "review_and_correct", "explicit_confirmation")
            values = [proof.get(key) for key in keys]
            if any(value is True for value in values):
                continue
            if all(value is False for value in values):
                failures.append(finding(form, soup,
                    "Aucun mécanisme de prévention ou de récupération exigé n'est disponible selon la vérification fournie.",
                    "Ajouter un mécanisme de correction, annulation, récupération ou confirmation explicite.",
                    form_index=index, mechanisms=list(keys)))
            else:
                reviews.append(finding(form, soup,
                    "Les preuves des mécanismes de confirmation ou récupération sont incomplètes.",
                    "Tester et documenter les mécanismes réellement disponibles.", form_index=index))
        return result(self, applicable + len(reviews), failures, reviews,
                      empty="Aucun formulaire dans le périmètre confirmé.",
                      metadata={"forms": len(forms), "confirmed_in_scope": applicable})


class Test11121(_TransactionTest):
    test_id = "11.12.1"
    criterion_id = "11.12"


class Test11122(_TransactionTest):
    financial_personal_only = True
    test_id = "11.12.2"
    criterion_id = "11.12"

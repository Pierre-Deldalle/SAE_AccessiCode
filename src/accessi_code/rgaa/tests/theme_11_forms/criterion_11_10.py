"""RGAA 11.10 — indications d'obligation, de format et d'erreurs de saisie."""
from __future__ import annotations

from accessi_code.analysis.forms import (associated_text, error_text, fields, finding,
                                         has_format, hint, invalid, normalize, required, result)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


def _mandatory_text(text: str) -> bool:
    return any(token in normalize(text).split() for token in {"obligatoire", "requis", "required"}) or "*" in text


class _FormTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})


class Test11101(_FormTest):
    test_id = "11.10.1"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        all_fields = fields(soup)
        if not all_fields:
            return result(self, 0)
        required_fields = [tag for tag in all_fields if required(tag)]
        if len(required_fields) == len(all_fields):
            return result(self, len(all_fields), metadata={"all_declared_required": True})
        # L'obligation réelle d'un champ sans required est fonctionnelle, non déductible du HTML.
        reviews = [finding(all_fields[0], soup,
            "Vérifier qu'aucun champ obligatoire non déclaré n'a été omis et que les indications sont visibles.",
            "Tester les règles de validation et les états avant soumission.",
            declared_required=len(required_fields))]
        return result(self, len(all_fields), reviews=reviews)


class Test11102(_FormTest):
    test_id = "11.10.2"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if required(tag)]
        reviews = []
        for tag in candidates:
            text = associated_text(tag, soup)
            if not _mandatory_text(text):
                reviews.append(finding(tag, soup,
                    "Le caractère obligatoire n'est pas démontré dans l'étiquette ou un texte associé visible.",
                    "Ajouter une mention obligatoire visible dans l'étiquette ou un texte associé.", associated_text=text))
            else:
                reviews.append(finding(tag, soup,
                    "Une indication d'obligation existe dans le DOM, mais sa visibilité reste à confirmer.",
                    "Vérifier l'affichage de l'indication avant la validation du formulaire.", associated_text=text))
        return result(self, len(candidates), reviews=reviews)


class Test11103(_FormTest):
    test_id = "11.10.3"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if required(tag) and (invalid(tag) or error_text(tag, soup))]
        reviews = []
        for tag in candidates:
            if invalid(tag):
                continue  # aria-invalid=true satisfait une des conditions.
            text = error_text(tag, soup)
            reviews.append(finding(tag, soup,
                "Vérifier que le message d'absence de saisie identifie visiblement le champ concerné.",
                "Associer un message d'erreur explicite ou aria-invalid=true.", error_text=text))
        return result(self, len(candidates), reviews=reviews,
                      empty="Aucun état d'erreur de champ obligatoire présent dans le DOM fourni.")


class Test11104(_FormTest):
    test_id = "11.10.4"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if required(tag) and invalid(tag)]
        reviews = []
        for tag in candidates:
            text = error_text(tag, soup)
            reviews.append(finding(tag, soup,
                "Le message d'erreur doit être visible dans l'étiquette ou le passage de texte associé.",
                "Contrôler l'affichage et l'association du message d'erreur.", error_text=text))
        return result(self, len(candidates), reviews=reviews)


class Test11105(_FormTest):
    test_id = "11.10.5"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if required(tag) and has_format(tag)]
        reviews = []
        for tag in candidates:
            text = associated_text(tag, soup)
            if not hint(text):
                reviews.append(finding(tag, soup,
                    "Aucune instruction de format suffisamment explicite n'est repérée dans le texte associé.",
                    "Fournir une instruction visible précisant le format attendu avant soumission.", text=text))
            else:
                reviews.append(finding(tag, soup,
                    "Une instruction de format est présente, mais sa visibilité et sa pertinence restent à vérifier.",
                    "Confirmer que l'instruction est visible avant soumission.", text=text))
        return result(self, len(candidates), reviews=reviews)


class Test11106(_FormTest):
    test_id = "11.10.6"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if has_format(tag) and (invalid(tag) or error_text(tag, soup))]
        reviews = []
        for tag in candidates:
            if invalid(tag):
                continue
            text = error_text(tag, soup)
            reviews.append(finding(tag, soup,
                "Le message de format doit identifier visiblement le champ concerné.",
                "Associer un message explicite ou utiliser aria-invalid=true.", error_text=text))
        return result(self, len(candidates), reviews=reviews)


class Test11107(_FormTest):
    test_id = "11.10.7"
    criterion_id = "11.10"

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if invalid(tag) and has_format(tag)]
        reviews = []
        for tag in candidates:
            text = associated_text(tag, soup)
            reviews.append(finding(tag, soup,
                "Vérifier que le type ou format obligatoire est indiqué visiblement dans l'étiquette ou le texte associé.",
                "Associer au champ une instruction de format visible et pertinente.",
                associated_text=text, hint_detected=hint(text)))
        return result(self, len(candidates), reviews=reviews)

"""RGAA 11.11 — suggestions de correction pour les erreurs de saisie."""
from __future__ import annotations

from accessi_code.analysis.forms import error_text, fields, finding, has_format, hint, invalid, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest


class _SuggestionTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})
    examples: bool = False

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        candidates = [tag for tag in fields(soup) if invalid(tag) or error_text(tag, soup)]
        reviews = []
        for tag in candidates:
            text = error_text(tag, soup)
            if self.examples:
                reviews.append(finding(tag, soup,
                    "Vérifier si un exemple de valeur attendue est nécessaire et proposé lors de l'erreur.",
                    "Fournir un exemple lorsque cela aide à corriger la saisie.", error_text=text))
            elif has_format(tag) and not hint(text):
                reviews.append(finding(tag, soup,
                    "Aucune suggestion explicite de type ou format n'est identifiable dans le message d'erreur.",
                    "Indiquer le format ou le type attendu, si nécessaire.", error_text=text))
            else:
                reviews.append(finding(tag, soup,
                    "La nécessité et la pertinence des suggestions dépendent de l'erreur réellement déclenchée.",
                    "Tester la soumission invalide et les messages présentés.", error_text=text))
        return result(self, len(candidates), reviews=reviews,
                      empty="Aucun message d'erreur de saisie observable dans le DOM fourni.")


class Test11111(_SuggestionTest):
    test_id = "11.11.1"
    criterion_id = "11.11"


class Test11112(_SuggestionTest):
    test_id = "11.11.2"
    criterion_id = "11.11"
    examples = True

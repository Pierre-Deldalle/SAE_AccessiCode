"""RGAA 11.13.1 — identification de la finalité des champs utilisateur."""
from __future__ import annotations

from accessi_code.analysis.forms import clean, fields, finding, label_text, normalize, result
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.rgaa.base import RGAATest

# WCAG 2.1 — Identify Input Purpose (section 7) : valeurs de finalité utilisateur.
_PURPOSES = {
    "name", "honorific-prefix", "given-name", "additional-name", "family-name",
    "honorific-suffix", "nickname", "username", "new-password", "current-password",
    "organization-title", "organization", "street-address", "address-line1",
    "address-line2", "address-line3", "address-level4", "address-level3",
    "address-level2", "address-level1", "country", "country-name", "postal-code",
    "cc-name", "cc-given-name", "cc-additional-name", "cc-family-name",
    "cc-number", "cc-exp", "cc-exp-month", "cc-exp-year", "cc-csc", "cc-type",
    "transaction-currency", "transaction-amount", "language", "bday", "bday-day",
    "bday-month", "bday-year", "sex", "url", "photo", "tel", "tel-country-code",
    "tel-national", "tel-area-code", "tel-local", "tel-local-prefix", "tel-local-suffix",
    "tel-extension", "email", "impp",
}
_CONTACT = {"home", "work", "mobile", "fax", "pager"}


def _parse_autocomplete(value: str) -> str | None:
    tokens = clean(value).lower().split()
    if not tokens:
        return None
    if tokens[0].startswith("section-") and len(tokens[0]) > len("section-"):
        tokens.pop(0)
    if tokens and tokens[0] in {"shipping", "billing"}:
        tokens.pop(0)
    if tokens and tokens[0] in _CONTACT:
        tokens.pop(0)
    return tokens[0] if len(tokens) == 1 and tokens[0] in _PURPOSES else None


# Correspondances sûres uniquement pour les libellés explicites.
_LABEL_PURPOSES = {
    "email": "email", "e mail": "email", "courriel": "email", "adresse email": "email",
    "prenom": "given-name", "nom de famille": "family-name", "code postal": "postal-code",
    "telephone": "tel", "numero de telephone": "tel", "date de naissance": "bday",
    "nom": "name", "adresse postale": "street-address", "ville": "address-level2",
    "pays": "country-name", "mot de passe": "current-password",
}


class Test11131(RGAATest):
    test_id = "11.13.1"
    criterion_id = "11.13"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services=None):
        soup = context.dom
        failures, reviews = [], []
        checked = 0
        for tag in fields(soup):
            if tag.name not in {"input", "textarea", "select"}:
                continue
            label = normalize(label_text(tag, soup))
            expected = _LABEL_PURPOSES.get(label)
            raw = clean(tag.get("autocomplete"))
            parsed = _parse_autocomplete(raw)
            # Un champ explicitement identifié par sa finalité ou avec un autocomplete
            # renseigné est candidat ; les autres peuvent aussi l'être : vérifier.
            if expected is None and (not raw or raw.lower() in {"on", "off"}):
                continue
            checked += 1
            if expected is not None and not raw:
                failures.append(finding(tag, soup,
                    f"Le champ utilisateur « {label} » n'a pas d'attribut autocomplete.",
                    f'Ajouter autocomplete="{expected}" si cette finalité est confirmée.',
                    expected=expected))
            elif not parsed:
                target = failures if expected is not None else reviews
                target.append(finding(tag, soup,
                    f"La valeur autocomplete « {raw} » ne correspond pas à une finalité utilisateur autorisée.",
                    "Employer une valeur de finalité reconnue si ce champ concerne des données utilisateur.", value=raw))
            elif expected is not None and parsed != expected:
                # Certains cas sont équivalents ou dépendent du contexte (name vs given-name).
                reviews.append(finding(tag, soup,
                    f"La valeur autocomplete « {parsed} » doit être comparée au libellé « {label} ».",
                    "Vérifier que la valeur correspond précisément à la donnée demandée.", expected=expected, actual=parsed))
            elif expected is None:
                reviews.append(finding(tag, soup,
                    f"Vérifier que autocomplete=« {parsed} » décrit bien la finalité du champ.",
                    "Comparer la valeur au type de donnée personnelle réellement attendu.", actual=parsed))
        # Champs personnels non identifiés par le lexique : couverture partielle.
        other_fields = [tag for tag in fields(soup) if tag.name in {"input", "textarea", "select"}
                        and normalize(label_text(tag, soup)) not in _LABEL_PURPOSES
                        and not clean(tag.get("autocomplete"))]
        if other_fields:
            reviews.append(finding(other_fields[0], soup,
                "D'autres champs peuvent concerner l'utilisateur sans être reconnus par le lexique déterministe.",
                "Vérifier les champs de données personnelles non reconnus.", count=len(other_fields)))
            checked += len(other_fields)
        return result(self, checked, failures, reviews,
                      metadata={"purpose_tokens": len(_PURPOSES)})

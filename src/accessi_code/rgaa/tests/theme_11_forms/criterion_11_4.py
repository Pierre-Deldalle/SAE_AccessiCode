"""RGAA 4.1.2 — critère 11.4 : proximité et position visuelles des étiquettes.

Le DOM identifie les champs, mais ne démontre pas la disposition visuelle.
Les résultats PASS/FAIL exigent une preuve vérifiée fournie par un navigateur
ou par une observation humaine via ``context.form_label_layout``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bs4 import Tag

from accessi_code.analysis.dom import (
    find_form_fields,
    get_element_identifier,
    get_matching_label,
    get_wrapping_label,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


_CHOICE_ROLES = frozenset({"checkbox", "radio", "switch"})
_POSITIONS = frozenset({"above", "below", "left", "right"})
_EXCEPTIONS = frozenset({
    "mixed_label_directions",
    "mixed_form_directions",
    "nonstandard_choice_appearance",
    "legitimate_alternative_placement",
})


def _is_choice(field: Tag) -> bool:
    role = str(field.get("role", "")).strip().lower()
    if role in _CHOICE_ROLES:
        return True
    return field.name == "input" and str(field.get("type", "text")).lower() in {
        "checkbox", "radio"
    }


def _label(field: Tag, soup: Any) -> tuple[str, str] | None:
    """Trouve un libellé textuel potentiellement visible, sans inférer le CSS.

    ``aria-label`` et ``title`` ne prouvent pas l'existence d'une étiquette
    visuelle. Les références ``aria-labelledby`` ne prouvent pas sa visibilité.
    """
    explicit = get_matching_label(field, soup)
    if explicit is not None:
        return ("label-for", explicit.get_text(" ", strip=True))

    wrapper = get_wrapping_label(field)
    if wrapper is not None:
        return ("label-wrapper", wrapper.get_text(" ", strip=True))

    references = str(field.get("aria-labelledby", "")).split()
    if len(references) == 1:
        matches = soup.find_all(id=references[0])
        if len(matches) == 1:
            return ("aria-labelledby", matches[0].get_text(" ", strip=True))

    return None


def _layout(context: AuditContext, identifier: str, label_text: str) -> dict[str, Any] | None:
    """Lit une preuve explicite, sans inventer de coordonnées à partir du DOM.

    Format : ``context.form_label_layout = {"input#email": {
      "verified": True, "source": "browser", "adjacent": True,
      "position": "above", "direction": "ltr", "label_text": "E-mail"
    }}``.
    Une exception peut être fournie avec ``exception`` et
    ``exception_verified=True``. Elle ne s'applique qu'à 11.4.2/11.4.3.
    """
    records = getattr(context, "form_label_layout", None)
    if not isinstance(records, Mapping):
        return None
    record = records.get(identifier)
    if not isinstance(record, Mapping):
        return None
    if record.get("verified") is not True or record.get("source") not in {"browser", "manual"}:
        return None
    if "label_text" in record and " ".join(str(record["label_text"]).split()) != label_text:
        return None
    return dict(record)


def _result(
    test: "_LabelPositionTest",
    status: TestStatus,
    summary: str,
    *,
    count: int,
    findings: list[Finding],
    metadata: dict[str, Any],
) -> TestResult:
    return TestResult(
        test_id=test.test_id,
        criterion_id=test.criterion_id,
        status=status,
        summary=summary,
        tested_elements=count,
        findings=findings,
        metadata=metadata,
    )


class _LabelPositionTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})
    mode: str

    async def run(
        self, context: AuditContext, services: Any | None = None
    ) -> TestResult:
        soup = context.dom
        if soup is None or not hasattr(soup, "select"):
            return _result(
                self, TestStatus.ERROR, "Le DOM n'est pas exploitable.",
                count=0, findings=[], metadata={},
            )

        fields = find_form_fields(soup)
        selected = [
            (index, field)
            for index, field in enumerate(fields)
            if self.mode == "all"
            or (_is_choice(field) if self.mode == "choice" else not _is_choice(field))
        ]
        if not selected:
            return _result(
                self, TestStatus.NOT_APPLICABLE,
                "Aucun champ concerné par ce test.",
                count=0, findings=[], metadata={"selected_fields": 0},
            )

        failures: list[Finding] = []
        reviews: list[Finding] = []
        confirmed = 0
        exceptions = 0

        for index, field in selected:
            identifier = get_element_identifier(field, index)
            field_id = field.get("id")
            if isinstance(field_id, str) and field_id and len(soup.find_all(id=field_id)) != 1:
                reviews.append(Finding(
                    element=identifier,
                    message="L'identifiant du champ n'est pas unique dans le DOM.",
                    recommendation="Rendre les identifiants uniques avant de vérifier la disposition.",
                    evidence={"id": field_id},
                ))
                continue
            candidate = _label(field, soup)
            if candidate is None or not candidate[1].strip():
                reviews.append(Finding(
                    element=identifier,
                    message=(
                        "Aucune étiquette textuelle potentiellement visible n'a été "
                        "identifiée avec certitude pour contrôler sa proximité."
                    ),
                    recommendation=(
                        "Identifier l'étiquette affichée et vérifier sa position "
                        "par rapport au champ dans le navigateur."
                    ),
                    evidence={"mechanism": candidate[0] if candidate else "unknown"},
                ))
                continue

            mechanism, label_text = candidate
            proof = _layout(context, identifier, label_text)
            if proof is None:
                reviews.append(Finding(
                    element=identifier,
                    message=(
                        f"La proximité visuelle de l'étiquette « {label_text} » "
                        "ne peut pas être établie avec le DOM seul."
                    ),
                    recommendation=(
                        "Contrôler le rendu visuel et fournir une preuve "
                        "de disposition vérifiée."
                    ),
                    evidence={"label": label_text, "mechanism": mechanism},
                ))
                continue

            if self.mode != "all" and proof.get("exception") is not None:
                exception = proof.get("exception")
                allowed_exceptions = (
                    _EXCEPTIONS
                    if self.mode == "choice"
                    else _EXCEPTIONS - {"nonstandard_choice_appearance"}
                )
                if exception in allowed_exceptions and proof.get("exception_verified") is True:
                    # L'exception doit être vérifiée et non seulement supposée.
                    exceptions += 1
                    continue
                reviews.append(Finding(
                    element=identifier,
                    message="Le cas particulier invoqué n'est pas suffisamment justifié.",
                    recommendation="Vérifier si le cas particulier RGAA s'applique réellement.",
                    evidence={"exception": str(exception)},
                ))
                continue

            adjacent = proof.get("adjacent")
            position = proof.get("position")
            direction = proof.get("direction")
            if not isinstance(adjacent, bool):
                reviews.append(Finding(
                    element=identifier,
                    message="La preuve ne précise pas si le champ et l'étiquette sont accolés.",
                    recommendation="Renseigner le constat visuel d'accolement.",
                    evidence={"label": label_text},
                ))
                continue

            if adjacent and self.mode != "all" and (
                position not in _POSITIONS or direction not in {"ltr", "rtl"}
            ):
                reviews.append(Finding(
                    element=identifier,
                    message="La position ou le sens de lecture n'est pas établi.",
                    recommendation="Vérifier la position visuelle et le sens de lecture de l'étiquette.",
                    evidence={"position": position, "direction": direction},
                ))
                continue

            if not adjacent:
                reason = "L'étiquette et son champ ne sont pas visuellement accolés."
            elif self.mode == "standard":
                allowed = {"above", "left"} if direction == "ltr" else {"above", "right"}
                reason = (
                    "La position de l'étiquette ne respecte pas le sens de lecture "
                    "pour ce champ classique."
                    if position not in allowed else ""
                )
            elif self.mode == "choice":
                allowed = {"below", "right"} if direction == "ltr" else {"below", "left"}
                reason = (
                    "La position de l'étiquette ne respecte pas le sens de lecture "
                    "pour cette case à cocher, ce bouton radio ou cet interrupteur."
                    if position not in allowed else ""
                )
            else:
                reason = ""

            if reason:
                failures.append(Finding(
                    element=identifier,
                    message=f"{reason} Étiquette : « {label_text} ».",
                    recommendation=(
                        "Accoler visuellement l'étiquette au champ et respecter "
                        "le placement RGAA applicable, sauf cas particulier justifié."
                    ),
                    evidence={
                        "label": label_text,
                        "mechanism": mechanism,
                        "adjacent": adjacent,
                        "position": position,
                        "direction": direction,
                        "source": proof["source"],
                    },
                ))
            else:
                confirmed += 1

        if failures:
            status = TestStatus.FAIL
            summary = f"{len(failures)} non-conformité(s) visuelle(s) confirmée(s)."
        elif reviews:
            status = TestStatus.NEEDS_REVIEW
            summary = f"{len(reviews)} champ(s) nécessitent une vérification visuelle."
        elif confirmed:
            status = TestStatus.PASS
            summary = f"{confirmed} disposition(s) visuelle(s) conforme(s) vérifiée(s)."
        else:
            status = TestStatus.NOT_APPLICABLE
            summary = "Tous les champs concernés relèvent de cas particuliers vérifiés."

        return _result(
            self, status, summary,
            count=len(selected),
            findings=failures + reviews,
            metadata={
                "selected_fields": len(selected),
                "confirmed_fields": confirmed,
                "failed_fields": len(failures),
                "review_fields": len(reviews),
                "verified_exceptions": exceptions,
                "layout_evidence": "context.form_label_layout",
            },
        )


class Test1141(_LabelPositionTest):
    """11.4.1 — l'étiquette et le champ sont visuellement accolés."""
    test_id = "11.4.1"
    criterion_id = "11.4"
    mode = "all"


class Test1142(_LabelPositionTest):
    """11.4.2 — position des étiquettes des champs classiques."""
    test_id = "11.4.2"
    criterion_id = "11.4"
    mode = "standard"


class Test1143(_LabelPositionTest):
    """11.4.3 — position des étiquettes de checkbox/radio/switch."""
    test_id = "11.4.3"
    criterion_id = "11.4"
    mode = "choice"

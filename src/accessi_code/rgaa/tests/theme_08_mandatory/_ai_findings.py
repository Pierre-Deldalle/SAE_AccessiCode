"""
Conversion des observations renvoyées par les analyseurs IA du thème 8.

Règle commune : une non-conformité n'est retenue que si chaque observation
désigne un élément précis et décrit l'anomalie. La recommandation n'est
qu'un conseil : si l'IA n'en fournit pas, une recommandation par défaut
propre au test est utilisée.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from accessi_code.models.result import Finding


def read_field(value: Any, name: str, default: Any = None) -> Any:
    """Lit un champ d'un résultat IA, sous forme d'objet ou de dictionnaire."""
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def to_finding(raw: Any) -> Finding:
    """Convertit une observation IA en Finding, en ne gardant que des valeurs valides."""
    if isinstance(raw, Finding):
        return raw

    element = read_field(raw, "element", "unknown")
    message = read_field(raw, "message", "")
    recommendation = read_field(raw, "recommendation")
    evidence = read_field(raw, "evidence", {})

    return Finding(
        element=element if isinstance(element, str) else "unknown",
        message=message if isinstance(message, str) else "",
        recommendation=recommendation if isinstance(recommendation, str) and recommendation.strip() else None,
        evidence=evidence if isinstance(evidence, dict) else {},
    )


def convert_findings(raw_findings: Any) -> list[Finding]:
    if not isinstance(raw_findings, (list, tuple)):
        return []
    return [to_finding(raw) for raw in raw_findings]


def is_precise(finding: Finding) -> bool:
    """L'observation désigne un élément identifiable et décrit l'anomalie."""
    element = finding.element.strip()
    return bool(element) and element.lower() != "unknown" and bool(finding.message.strip())


def with_default_recommendation(findings: list[Finding], default: str) -> list[Finding]:
    return [finding if finding.recommendation else replace(finding, recommendation=default) for finding in findings]


def fail_summary(analysis: Any, fallback: str, findings: list[Finding]) -> str:
    """Résumé d'une non-conformité : explication de l'IA puis éléments concernés."""
    explanation = read_field(analysis, "explanation")
    head = explanation.strip() if isinstance(explanation, str) and explanation.strip() else fallback
    details = " ".join(f"{finding.element} : {finding.message}" for finding in findings)
    return f"{head} {details}".strip()

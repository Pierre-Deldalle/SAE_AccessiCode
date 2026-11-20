"""Applique des décisions humaines documentées aux NEEDS_REVIEW d'un rapport.

Utilisation : python -m accessi_code.review.resolve audit.json decisions.json -o audit_verifie.json
Aucune conclusion n'est générée sans une décision humaine explicite.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

PRIORITY = ("fail", "error", "needs_review", "not_tested", "pass", "not_applicable")
ALLOWED = {"pass", "fail", "not_applicable"}


def _overall(statuses: list[str]) -> str:
    return next((status for status in PRIORITY if status in statuses), "not_tested")


def resolve_report(report: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Retourne une copie recalculée. Une décision concerne un test entier.

    Chaque décision doit inclure `test_id`, `status`, `reviewer`, `reason`,
    `evidence` (objet non vide). Un FAIL exige un finding précis.
    """
    output = copy.deepcopy(report)
    criteria = output.get("criteria")
    if not isinstance(criteria, list):
        raise ValueError("Le rapport doit contenir une liste 'criteria'.")
    indexed: dict[str, dict[str, Any]] = {}
    for criterion in criteria:
        for test in criterion.get("tests", []):
            key = test.get("test_id")
            if not isinstance(key, str) or key in indexed:
                raise ValueError("Identifiant de test absent ou dupliqué.")
            indexed[key] = test

    used: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Chaque décision doit être un objet JSON.")
        test_id = decision.get("test_id")
        if test_id in used or test_id not in indexed:
            raise ValueError(f"Test inexistant ou décision dupliquée : {test_id!r}.")
        used.add(test_id)
        test = indexed[test_id]
        if test.get("status") != "needs_review":
            raise ValueError(f"Le test {test_id} n'est pas en NEEDS_REVIEW.")
        status = decision.get("status")
        if status not in ALLOWED:
            raise ValueError("Le statut décidé doit être pass, fail ou not_applicable.")
        for key in ("reviewer", "reason"):
            if not isinstance(decision.get(key), str) or not decision[key].strip():
                raise ValueError(f"La décision {test_id} doit préciser {key}.")
        evidence = decision.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError(f"La décision {test_id} doit contenir une preuve documentée.")
        findings = decision.get("findings", [])
        if status == "fail":
            if not isinstance(findings, list) or not findings:
                raise ValueError(f"Un FAIL doit contenir au moins un finding : {test_id}.")
            for finding in findings:
                if not isinstance(finding, dict) or any(
                    not isinstance(finding.get(k), str) or not finding[k].strip()
                    for k in ("element", "message", "recommendation")
                ):
                    raise ValueError(f"Finding incomplet pour {test_id}.")
        elif findings:
            raise ValueError("Des findings d'anomalie ne sont permis que pour FAIL.")

        old_findings = test.get("findings", [])
        test["status"] = status
        test["summary"] = f"Décision humaine documentée : {decision['reason'].strip()}"
        test["findings"] = findings if status == "fail" else []
        metadata = test.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            test["metadata"] = metadata
        metadata["manual_review"] = {
            "reviewer": decision["reviewer"].strip(),
            "reason": decision["reason"].strip(),
            "evidence": evidence,
            "previous_status": "needs_review",
            "previous_findings": old_findings,
        }

    statuses = []
    for criterion in criteria:
        tests = criterion.get("tests", [])
        count = Counter(test["status"] for test in tests)
        criterion["status"] = _overall([test["status"] for test in tests])
        criterion["summary"] = (
            f"{len(tests)} test(s) : {count['pass']} conforme(s), "
            f"{count['fail']} non conforme(s), {count['needs_review']} à vérifier, "
            f"{count['not_tested']} non testé(s), "
            f"{count['not_applicable']} non applicable(s), {count['error']} erreur(s)."
        )
        statuses.extend(test["status"] for test in tests)
    counts = Counter(statuses)
    output["status"] = _overall([criterion["status"] for criterion in criteria])
    output["statistics"] = {
        "total_criteria": len(criteria), "total_tests": len(statuses),
        "passed_tests": counts["pass"], "failed_tests": counts["fail"],
        "not_applicable_tests": counts["not_applicable"],
        "not_tested_tests": counts["not_tested"],
        "needs_review_tests": counts["needs_review"], "error_tests": counts["error"],
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    if not isinstance(decisions, list):
        raise ValueError("Le fichier de décisions doit contenir une liste JSON.")
    resolved = resolve_report(report, decisions)
    args.output.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapport vérifié : {args.output} ; NEEDS_REVIEW restants : "
          f"{resolved['statistics']['needs_review_tests']}")


if __name__ == "__main__":
    main()

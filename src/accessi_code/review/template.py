"""Prépare une liste des tests NEEDS_REVIEW pour validation humaine.

python -m accessi_code.review.template audit.json -o decisions_a_completer.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def review_template(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "test_id": test["test_id"],
            "status": "A_CHOISIR: pass / fail / not_applicable",
            "reviewer": "",
            "reason": "",
            "evidence": {},
            "findings": [],
            "original_summary": test.get("summary", ""),
            "original_findings": test.get("findings", []),
        }
        for criterion in report.get("criteria", [])
        for test in criterion.get("tests", [])
        if test.get("status") == "needs_review"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.report.read_text(encoding="utf-8"))
    result = review_template(data)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(result)} décision(s) à compléter : {args.output}")


if __name__ == "__main__":
    main()

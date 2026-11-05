import pytest

from accessi_code.review.resolve import resolve_report


def report():
    return {"audit_id": "test", "status": "needs_review", "criteria": [
        {"criterion_id": "11.4", "status": "needs_review", "summary": "", "tests": [
            {"test_id": "11.4.1", "criterion_id": "11.4", "status": "needs_review",
             "summary": "À vérifier", "findings": [{"element": "input#x", "message": "?"}],
             "tested_elements": 1, "metadata": {}}
        ]}
    ], "statistics": {"needs_review_tests": 1}}


def decision(status="pass"):
    result = {"test_id": "11.4.1", "status": status, "reviewer": "Auditeur RGAA",
              "reason": "Contrôle visuel effectué sur le rendu à 1366 px.",
              "evidence": {"capture": "capture-01.png", "champ": "input#x"}}
    if status == "fail":
        result["findings"] = [{"element": "input#x", "message": "Étiquette éloignée du champ.",
                               "recommendation": "Rapprocher l'étiquette."}]
    return result


@pytest.mark.parametrize("status", ["pass", "fail", "not_applicable"])
def test_valid_review_updates_report_and_statistics(status):
    original = report()
    resolved = resolve_report(original, [decision(status)])
    assert original["criteria"][0]["tests"][0]["status"] == "needs_review"
    assert resolved["criteria"][0]["tests"][0]["status"] == status
    assert resolved["statistics"]["needs_review_tests"] == 0
    assert resolved["criteria"][0]["tests"][0]["metadata"]["manual_review"]["reviewer"]


@pytest.mark.parametrize("change", [
    {"reviewer": ""}, {"reason": ""}, {"evidence": {}},
    {"status": "error"}, {"test_id": "inconnu"},
])
def test_invalid_review_rejected(change):
    data = decision()
    data.update(change)
    with pytest.raises(ValueError):
        resolve_report(report(), [data])


def test_fail_without_precise_finding_rejected():
    data = decision("fail")
    data["findings"] = []
    with pytest.raises(ValueError):
        resolve_report(report(), [data])


def test_duplicate_decisions_rejected():
    with pytest.raises(ValueError):
        resolve_report(report(), [decision(), decision()])


def test_empty_decisions_keep_review():
    assert resolve_report(report(), [])["statistics"]["needs_review_tests"] == 1

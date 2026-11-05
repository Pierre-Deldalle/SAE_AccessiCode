from accessi_code.review.template import review_template


def test_template_only_review():
    report = {"criteria": [{"tests": [
        {"test_id": "8.9.1", "status": "needs_review", "summary": "à vérifier"},
        {"test_id": "8.10.2", "status": "fail"},
    ]}]}
    entries = review_template(report)
    assert len(entries) == 1
    assert entries[0]["test_id"] == "8.9.1"
    assert entries[0]["evidence"] == {}

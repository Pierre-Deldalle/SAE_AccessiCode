from accessi_code.analysis.form_layout import classify_geometry, evidence_from_measurements


def rect(x, y, w, h):
    return {"left": x, "top": y, "right": x + w, "bottom": y + h,
            "width": w, "height": h}


def test_label_above():
    proof = classify_geometry(rect(0, 0, 100, 20), rect(0, 24, 100, 20), "ltr")
    assert proof["position"] == "above"
    assert proof["adjacent"] is True


def test_label_right():
    assert classify_geometry(rect(110, 0, 100, 20), rect(0, 0, 100, 20), "ltr")["position"] == "right"


def test_far_label_not_verified():
    assert classify_geometry(rect(0, 0, 100, 20), rect(0, 80, 100, 20), "ltr") is None


def test_overlapping_not_verified():
    assert classify_geometry(rect(0, 0, 100, 20), rect(0, 0, 100, 20), "ltr") is None


def test_invalid_direction_not_verified():
    assert classify_geometry(rect(0, 0, 100, 20), rect(0, 24, 100, 20), "auto") is None


def test_measurements_match_real_field_identifier(context_factory):
    context = context_factory('<label for="e">Courriel</label><input id="e" type="email">')
    records = evidence_from_measurements(context, [{
        "index": 0, "usable": True, "label_text": "Courriel", "direction": "ltr",
        "label": rect(0, 0, 100, 20), "field": rect(0, 25, 100, 20),
    }])
    assert records["input#e"]["position"] == "above"


def test_duplicate_identifier_is_not_verified(context_factory):
    context = context_factory('<label for="e">Courriel</label><input id="e"><input id="e">')
    records = evidence_from_measurements(context, [{
        "index": 0, "usable": True, "label_text": "Courriel", "direction": "ltr",
        "label": rect(0, 0, 100, 20), "field": rect(0, 25, 100, 20),
    }])
    assert records == {}

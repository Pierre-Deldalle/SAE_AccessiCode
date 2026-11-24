from accessi_code.analysis.navigation_browser import _collect_positive_positions, _same_boxes


def box(x=0, y=0, region="header"):
    return {"region": region, "x": x, "y": y, "width": 100, "height": 20}


def test_same_boxes_only_confirm_positive():
    assert _same_boxes([box(), box(2, 3)]) is True
    assert _same_boxes([box(), box(30)]) is False
    assert _same_boxes([box(), None]) is False


def test_multi_page_visual_proof():
    snap = {"nav": [box()], "search": box(0, 40), "sitemap": box(0, 70), "skip": box(0, 0)}
    proofs = _collect_positive_positions([snap, dict(snap)])
    assert proofs["12.2.1"]["same_visual_position"]
    assert proofs["12.4.2"]["same_visual_position"]
    assert proofs["12.5.2"]["same_visual_position"]
    assert proofs["12.7.2"]["same_visual_position"]


def test_inconsistent_position_does_not_invent_fail():
    a = {"nav": [box()], "search": box(), "sitemap": box(), "skip": box()}
    b = {"nav": [box(40)], "search": box(40), "sitemap": box(40), "skip": box(40)}
    assert _collect_positive_positions([a, b]) == {}

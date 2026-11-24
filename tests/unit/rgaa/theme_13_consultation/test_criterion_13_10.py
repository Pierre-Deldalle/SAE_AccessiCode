"""Critères RGAA 13.10, 13.11 et 13.12 : gestes, pointeur et mouvements de l'appareil."""

import asyncio

import pytest
from tests.ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_10 import Test13101, Test13102
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_11 import Test13111
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_12 import Test13121, Test13122, Test13123

PINCH = "map.addEventListener('touchstart', e => { if (e.touches.length > 1) startZoom(e) });"
SWIPE = "c.addEventListener('touchmove', e => { dx = e.touches[0].clientX - x0; });"
SHAKE = "window.addEventListener('devicemotion', e => { if (shake(e)) undo() });"


def _page(code: str, body: str = "") -> str:
    return f"<html><body>{body}<script>{code}</script></body></html>"


# 13.10 ----------------------------------------------------------------------


def test_13101_no_gesture_is_not_applicable(context_factory, run_rgaa):
    ai = text_services()
    html = _page("btn.addEventListener('click', go);", "<button>Go</button>")
    assert run_rgaa(Test13101(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    assert run_rgaa(Test13102(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_13101_multipoint_is_judged_with_page_controls(context_factory, run_rgaa):
    ai = text_services()
    html = _page(PINCH, '<button aria-label="Zoom avant">+</button>')
    assert run_rgaa(Test13101(), context_factory(html), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "gesture_alternative"
    assert "touches.length > 1" in items[0].text
    assert items[0].context == "Contrôles de la page : button « Zoom avant »"
    assert items[0].details["gesture"] == "un contact multipoint"


def test_13101_no_alternative_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test13101(), context_factory(_page(PINCH)), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "script[index=0]"


def test_13102_path_gesture(context_factory, run_rgaa):
    assert run_rgaa(Test13102(), context_factory(_page(SWIPE))).status == Status.NEEDS_REVIEW
    hammer = _page("const h = new Hammer(el); h.on('swipeleft', next);")
    assert run_rgaa(Test13102(), context_factory(hammer), text_services()).status == Status.PASS


def test_13102_comments_are_ignored(context_factory, run_rgaa):
    html = _page("// TODO : gérer le swipe\nbtn.onclick = next;")
    assert run_rgaa(Test13102(), context_factory(html)).status == Status.NOT_APPLICABLE


# 13.11 ----------------------------------------------------------------------


def test_13111_page_without_pointer_action_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test13111(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_13111_click_actions_pass(context_factory, run_rgaa):
    result = run_rgaa(Test13111(), context_factory('<button onclick="send()">Envoyer</button>'))
    assert result.status == Status.PASS
    assert "relâchement" in result.summary


@pytest.mark.parametrize(
    "html",
    [
        '<div onmousedown="supprimer()">Supprimer</div>',
        _page("el.addEventListener('pointerdown', () => { supprimer() });"),
        _page("function del() { supprimer() }\nel.onmousedown = del;"),
    ],
)
def test_13111_action_on_press_fails(html, context_factory, run_rgaa):
    result = run_rgaa(Test13111(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["event"] in {"mousedown", "pointerdown"}


@pytest.mark.parametrize(
    "html",
    [
        '<div onmousedown="armer()" onmouseup="declencher()">Tirer</div>',
        _page("el.addEventListener('pointerdown', armer); el.addEventListener('pointercancel', annuler);"),
        '<div onmousedown="supprimer()">Supprimer</div><button>Annuler</button>',
    ],
)
def test_13111_release_or_undo_needs_review(html, context_factory, run_rgaa):
    assert run_rgaa(Test13111(), context_factory(html)).status == Status.NEEDS_REVIEW


@pytest.mark.parametrize(
    "code",
    [
        "el.addEventListener('mousedown', (e) => { e.preventDefault(); this.classList.add('active'); });",
        PINCH,
        "el.addEventListener('touchstart', start); el.addEventListener('touchmove', move);",
    ],
)
def test_13111_cosmetic_or_gesture_handlers_are_ignored(code, context_factory, run_rgaa):
    assert run_rgaa(Test13111(), context_factory(_page(code))).status == Status.NOT_APPLICABLE


# 13.12 ----------------------------------------------------------------------


def test_13121_device_motion_is_judged_by_ai(context_factory, run_rgaa):
    ai = text_services()
    html = _page(SHAKE, "<button>Annuler</button>")
    assert run_rgaa(Test13121(), context_factory(html), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "motion_alternative"
    assert items[0].details["motion"] == "un mouvement de l'appareil"


def test_13121_screen_rotation_is_not_device_motion(context_factory, run_rgaa):
    html = _page("screen.orientation.lock('landscape'); window.addEventListener('orientationchange', f);")
    for test in (Test13121(), Test13122(), Test13123()):
        assert run_rgaa(test, context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_13122_motion_towards_device(context_factory, run_rgaa):
    html = _page("const s = new ProximitySensor(); s.onreading = next;")
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test13122(), context_factory(html), ai).status == Status.FAIL
    assert run_rgaa(Test13121(), context_factory(html), ai).status == Status.NOT_APPLICABLE


def test_13123_disable_is_judged_with_disable_code(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test13123(), context_factory(_page(SHAKE)), ai)
    assert result.status == Status.FAIL
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "motion_disable"
    assert items[0].details["disable_code"] is False

    with_removal = _page(SHAKE + " off.onclick = () => window.removeEventListener('devicemotion', h);")
    ai = text_services()
    run_rgaa(Test13123(), context_factory(with_removal), ai)
    assert ai.text_relevance_analyzer.analyze_relevance.call_args.args[1][0].details["disable_code"] is True


def test_13123_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test13123(), context_factory(_page(SHAKE))).status == Status.NEEDS_REVIEW


@pytest.mark.parametrize("test", [Test13101(), Test13102(), Test13111(), Test13121(), Test13122(), Test13123()])
def test_13_10_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))

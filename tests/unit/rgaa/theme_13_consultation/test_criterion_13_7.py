"""Critères RGAA 13.7 et 13.8 : flashs, contenus en mouvement et clignotants."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_7 import Test1371, Test1372, Test1373
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_8 import Test1381, Test1382

ANIMATED_GIF = b"GIF89a" + b"\x00" * 10 + b"\x21\xf9\x04" + b"\x00" * 10 + b"\x21\xf9\x04" + b"\x00;"
STATIC_GIF = b"GIF89a" + b"\x00" * 10 + b"\x21\xf9\x04" + b"\x00;"


def _styled(css: str, body: str = '<p class="x">Promo</p>') -> str:
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"


BLINK = "@keyframes blink { 50% { opacity: 0 } }"
SPIN = "@keyframes spin { to { transform: rotate(360deg) } }"


# 13.7.1 ---------------------------------------------------------------------


def test_1371_static_page_is_not_applicable(context_factory, run_rgaa):
    context = context_factory('<img src="logo.gif" alt="">', resources={"logo.gif": STATIC_GIF})
    assert run_rgaa(Test1371(), context).status == Status.NOT_APPLICABLE


def test_1371_video_and_animated_image_need_review(context_factory, run_rgaa):
    html = '<video src="v.mp4"></video><img src="anim.gif" alt="">'
    result = run_rgaa(Test1371(), context_factory(html, resources={"anim.gif": ANIMATED_GIF}))
    assert result.status == Status.NEEDS_REVIEW
    assert [finding.evidence["kind"] for finding in result.findings] == ["vidéo", "image animée"]


def test_1371_small_media_passes(context_factory, run_rgaa):
    html = '<img src="anim.gif" width="100" height="100" alt="">'
    assert run_rgaa(Test1371(), context_factory(html, resources={"anim.gif": ANIMATED_GIF})).status == Status.PASS


def test_1371_svg_animation_of_opacity(context_factory, run_rgaa):
    html = '<svg><rect><animate attributeName="opacity" values="0;1" dur="0.1s"/></rect></svg>'
    assert run_rgaa(Test1371(), context_factory(html)).status == Status.NEEDS_REVIEW


# 13.7.2 ---------------------------------------------------------------------


def test_1372_fast_light_toggle_needs_review(context_factory, run_rgaa):
    html = "<script>setInterval(() => { el.classList.toggle('on') }, 100);</script>"
    result = run_rgaa(Test1372(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["delay_ms"] == 100


def test_1372_slow_toggle_passes_and_other_timers_are_ignored(context_factory, run_rgaa):
    slow = "<script>setInterval(() => { el.style.opacity = o; }, 500);</script>"
    assert run_rgaa(Test1372(), context_factory(slow)).status == Status.PASS
    other = "<script>setInterval(() => { count++ }, 50); setTimeout(() => { el.hidden = true }, 50);</script>"
    assert run_rgaa(Test1372(), context_factory(other)).status == Status.NOT_APPLICABLE


# 13.7.3 ---------------------------------------------------------------------


def test_1373_fast_blink_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1373(), context_factory(_styled(f".x {{ animation: blink .1s infinite }} {BLINK}")))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["frequency"] == 10


@pytest.mark.parametrize(
    "css",
    [
        f".x {{ animation: blink 1s infinite }} {BLINK}",
        f".x {{ animation: blink .1s infinite; width: 50px; height: 50px }} {BLINK}",
    ],
)
def test_1373_slow_or_small_blink_passes(css, context_factory, run_rgaa):
    html = _styled(css, '<p class="x" style="width:50px;height:50px">Promo</p>')
    assert run_rgaa(Test1373(), context_factory(html)).status == Status.PASS


def test_1373_restart_of_the_cycle_counts_as_a_change(context_factory, run_rgaa):
    css = ".x { animation: ms 200ms infinite } @keyframes ms { 0% { opacity: 1 } 100% { opacity: 0 } }"
    result = run_rgaa(Test1373(), context_factory(_styled(css)))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["frequency"] == 5


def test_1373_area_declared_in_the_rule_is_used(context_factory, run_rgaa):
    css = f".x {{ animation: blink .1s infinite; width: 200px; height: 100px }} {BLINK}"
    assert run_rgaa(Test1373(), context_factory(_styled(css))).status == Status.PASS
    big = f".x {{ animation: blink .1s infinite; width: 400px; height: 100px }} {BLINK}"
    assert run_rgaa(Test1373(), context_factory(_styled(big))).status == Status.NEEDS_REVIEW


@pytest.mark.parametrize(
    "css",
    [
        f".x {{ animation: spin .1s infinite }} {SPIN}",
        ".x { animation: fade .3s } @keyframes fade { from { opacity: 0 } to { opacity: 1 } }",
        f".x:hover {{ animation: blink .1s infinite }} {BLINK}",
        f".absent {{ animation: blink .1s infinite }} {BLINK}",
    ],
)
def test_1373_non_flashing_animations_are_ignored(css, context_factory, run_rgaa):
    assert run_rgaa(Test1373(), context_factory(_styled(css))).status == Status.NOT_APPLICABLE


# 13.8.1 ---------------------------------------------------------------------


def test_1381_nothing_moving_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test1381(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_1381_marquee(context_factory, run_rgaa):
    result = run_rgaa(Test1381(), context_factory("<marquee>Défilant</marquee>"))
    assert result.status == Status.FAIL
    with_control = "<marquee>Défilant</marquee><button>Mettre en pause</button>"
    result = run_rgaa(Test1381(), context_factory(with_control))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["pause_controls"] == ["Mettre en pause"]


def test_1381_autoplay_videos(context_factory, run_rgaa):
    assert run_rgaa(Test1381(), context_factory("<video autoplay controls></video>")).status == Status.PASS
    assert run_rgaa(Test1381(), context_factory("<video autoplay muted loop></video>")).status == Status.FAIL
    assert run_rgaa(Test1381(), context_factory("<video autoplay muted></video>")).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1381(), context_factory("<video src='v.mp4'></video>")).status == Status.NOT_APPLICABLE


def test_1381_css_motion(context_factory, run_rgaa):
    short = _styled(f".x {{ animation: spin 1s 3 }} {SPIN}")
    assert run_rgaa(Test1381(), context_factory(short)).status == Status.PASS
    endless = _styled(f".x {{ animation: spin 1s linear infinite }} {SPIN}")
    result = run_rgaa(Test1381(), context_factory(endless))
    assert result.status == Status.NEEDS_REVIEW
    assert "chargement" in result.findings[0].message


def test_1381_script_carousel_needs_review(context_factory, run_rgaa):
    html = "<script>setInterval(function () { showSlide(i++) }, 5000);</script>"
    assert run_rgaa(Test1381(), context_factory(html)).status == Status.NEEDS_REVIEW


# 13.8.2 ---------------------------------------------------------------------


def test_1382_blinking(context_factory, run_rgaa):
    endless = _styled(f".x {{ animation: blink 1s infinite }} {BLINK}")
    assert run_rgaa(Test1382(), context_factory(endless)).status == Status.NEEDS_REVIEW
    short = _styled(f".x {{ animation: blink 1s 3 }} {BLINK}")
    assert run_rgaa(Test1382(), context_factory(short)).status == Status.PASS
    fade = _styled(".x { animation: fade 10s } @keyframes fade { from { opacity: 0 } to { opacity: 1 } }")
    assert run_rgaa(Test1382(), context_factory(fade)).status == Status.NOT_APPLICABLE


def test_1382_script_blink_needs_review(context_factory, run_rgaa):
    html = "<script>setInterval(() => { el.style.visibility = v ? 'hidden' : 'visible' }, 500);</script>"
    assert run_rgaa(Test1382(), context_factory(html)).status == Status.NEEDS_REVIEW


@pytest.mark.parametrize("test", [Test1371(), Test1372(), Test1373(), Test1381(), Test1382()])
def test_13_7_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))

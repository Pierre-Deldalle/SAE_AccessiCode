from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_1 import (
    Test1311 as RGAA1311,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_1 import (
    Test1312 as RGAA1312,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_1 import (
    Test1313 as RGAA1313,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_1 import (
    Test1314 as RGAA1314,
)

# ---------------------------------------------------------------------------
# 13.1.1 : Procédés de rafraîchissement (meta refresh, object, embed, svg, canvas)
# ---------------------------------------------------------------------------


def test_1311_no_refresh_not_applicable(context_factory, run_rgaa):
    """Aucun rafraîchissement détecté -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><head></head><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1311_meta_refresh_20h_plus_passes(context_factory, run_rgaa):
    """Meta refresh ≥ 20h (72000s) -> PASS."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="72000"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("intervalle ≥ 20 heures" in f.message for f in result.findings)


def test_1311_meta_refresh_0s_needs_review(context_factory, run_rgaa):
    """Meta refresh immédiat (0s) -> NEEDS_REVIEW (c'est une redirection, test 13.1.2)."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("immédiat" in f.message for f in result.findings)


def test_1311_meta_refresh_less_than_20h_needs_review(context_factory, run_rgaa):
    """Meta refresh < 20h sans contrôle utilisateur détecté -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="300"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("aucun mécanisme de contrôle" in f.message for f in result.findings)


def test_1311_embedded_elements_detected(context_factory, run_rgaa):
    """Éléments object, embed, svg, canvas détectés -> NEEDS_REVIEW (intervalle inconnu)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<object data="content.html"></object>'
        '<embed src="plugin.swf">'
        '<svg></svg>'
        '<canvas></canvas>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 4
    for finding in result.findings:
        assert finding.evidence.get("needs_manual_check") is True


def test_1311_multiple_refreshes_mixed_results(context_factory, run_rgaa):
    """Plusieurs rafraîchissements : un conforme (≥20h), un à vérifier -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<meta http-equiv="refresh" content="72000">'
        '<meta http-equiv="refresh" content="300">'
        '</head><body></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    # Priorité : NEEDS_REVIEW > PASS (pas de FAIL ici)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2


# ---------------------------------------------------------------------------
# 13.1.2 : Redirection meta immédiate
# ---------------------------------------------------------------------------


def test_1312_no_meta_redirect_not_applicable(context_factory, run_rgaa):
    """Aucune redirection meta -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><head></head><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1312_meta_redirect_immediate_passes(context_factory, run_rgaa):
    """Redirection meta immédiate (0s) -> PASS."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=https://example.com"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("immédiate" in f.message for f in result.findings)


def test_1312_meta_redirect_delayed_fails(context_factory, run_rgaa):
    """Redirection meta différée (>0s) -> FAIL."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="5;url=https://example.com"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any("différée" in f.message for f in result.findings)


def test_1312_meta_refresh_only_not_redirect(context_factory, run_rgaa):
    """Meta refresh sans URL (pas de redirection) -> NOT_APPLICABLE pour 13.1.2."""
    html = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="300"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1312_multiple_redirects_one_delayed_fails(context_factory, run_rgaa):
    """Plusieurs redirections : une immédiate, une différée -> FAIL (priorité FAIL)."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<meta http-equiv="refresh" content="0;url=https://example.com">'
        '<meta http-equiv="refresh" content="5;url=https://other.com">'
        '</head><body></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2


# ---------------------------------------------------------------------------
# 13.1.3 : Redirection via script
# ---------------------------------------------------------------------------


def test_1313_no_js_redirect_not_applicable(context_factory, run_rgaa):
    """Aucune redirection script -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1313(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1313_js_redirect_with_timer_needs_review(context_factory, run_rgaa):
    """Redirection script avec setTimeout -> NEEDS_REVIEW (pas de contrôle détecté)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setTimeout(function() { window.location = "https://example.com"; }, 5000);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("temporisation" in f.message for f in result.findings)


def test_1313_js_redirect_immediate_needs_review(context_factory, run_rgaa):
    """Redirection script immédiate (sans timer) -> NEEDS_REVIEW (vérifier action utilisateur)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>window.location = "https://example.com";</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("immédiate" in f.message for f in result.findings)


def test_1313_js_redirect_various_patterns(context_factory, run_rgaa):
    """Divers patterns de redirection JS détectés."""
    patterns = [
        'window.location.href = "https://example.com"',
        'window.location.replace("https://example.com")',
        'location.href = "https://example.com"',
        'document.location = "https://example.com"',
    ]

    for pattern in patterns:
        html = f'<!DOCTYPE html><html><body><script>{pattern};</script></body></html>'
        context = context_factory(html)

        result = run_rgaa(RGAA1313(), context)

        assert result.status == Status.NEEDS_REVIEW
        assert result.tested_elements == 1


def test_1313_js_redirect_with_setinterval(context_factory, run_rgaa):
    """Redirection avec setInterval -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setInterval(function() { window.location.href = "https://example.com"; }, 60000);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# 13.1.4 : Limite de temps de session
# ---------------------------------------------------------------------------


def test_1314_no_session_timeout_not_applicable(context_factory, run_rgaa):
    """Aucune limite de session détectée -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1314_meta_session_timeout_20h_plus_passes(context_factory, run_rgaa):
    """Meta timeout ≥ 20h -> PASS."""
    html = '<!DOCTYPE html><html><head><meta name="session-timeout" content="72000"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("≥ 20h" in f.message for f in result.findings)


def test_1314_meta_session_timeout_less_than_20h_needs_review(context_factory, run_rgaa):
    """Meta timeout < 20h sans contrôle -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><head><meta name="session-timeout" content="1800"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("< 20h" in f.message for f in result.findings)


def test_1314_js_session_timeout_needs_review(context_factory, run_rgaa):
    """Timeout de session via script -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>var sessionTimeout = 30 * 60 * 1000; // 30 minutes</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("script" in f.message.lower() for f in result.findings)


def test_1314_js_idle_timeout_needs_review(context_factory, run_rgaa):
    """Détection de timeout d'inactivité (idle) -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>function checkIdleTimeout() { /* ... */ }</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1314_js_auto_logout_needs_review(context_factory, run_rgaa):
    """Détection de déconnexion automatique -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>function autoLogout() { /* ... */ }</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1314_multiple_session_timeouts_mixed(context_factory, run_rgaa):
    """Plusieurs limites de session : une ≥20h, une <20h -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<meta name="timeout1" content="72000">'
        '<meta name="timeout2" content="1800">'
        '</head><body></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2


# ---------------------------------------------------------------------------
# Tests d'intégration : cas combinés
# ---------------------------------------------------------------------------


def test_1311_and_1312_both_present(context_factory, run_rgaa):
    """Page avec rafraîchissement ET redirection meta."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<meta http-equiv="refresh" content="300">'
        '<meta http-equiv="refresh" content="0;url=https://example.com">'
        '</head><body></body></html>'
    )
    context = context_factory(html)

    result_1311 = run_rgaa(RGAA1311(), context)
    result_1312 = run_rgaa(RGAA1312(), context)

    # 13.1.1 : refresh 300s -> NEEDS_REVIEW (le redirect 0s est ignoré car is_redirect=True)
    assert result_1311.status == Status.NEEDS_REVIEW
    assert result_1311.tested_elements == 1

    # 13.1.2 : redirect 0s -> PASS
    assert result_1312.status == Status.PASS
    assert result_1312.tested_elements == 1


def test_1313_and_1314_both_present(context_factory, run_rgaa):
    """Page avec redirection script ET timeout session."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setTimeout(function() { window.location = "https://example.com"; }, 5000);</script>'
        '<script>var sessionTimeout = 1800000;</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result_1313 = run_rgaa(RGAA1313(), context)
    result_1314 = run_rgaa(RGAA1314(), context)

    assert result_1313.status == Status.NEEDS_REVIEW
    assert result_1313.tested_elements == 1

    assert result_1314.status == Status.NEEDS_REVIEW
    assert result_1314.tested_elements == 1


# ---------------------------------------------------------------------------
# Tests de régression : parsing robuste
# ---------------------------------------------------------------------------


def test_1311_meta_refresh_case_insensitive(context_factory, run_rgaa):
    """Meta refresh insensible à la casse."""
    html = '<!DOCTYPE html><html><head><META HTTP-EQUIV="REFRESH" CONTENT="72000"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1311(), context)

    assert result.status == Status.PASS


def test_1311_meta_refresh_with_quotes_variations(context_factory, run_rgaa):
    """Meta refresh avec différentes variations de guillemets."""
    variations = [
        'content="300"',
        "content='300'",
        'content=300',
    ]

    for content_attr in variations:
        html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" {content_attr}></head><body></body></html>'
        context = context_factory(html)

        result = run_rgaa(RGAA1311(), context)

        assert result.status == Status.NEEDS_REVIEW
        assert result.tested_elements == 1


def test_1312_meta_redirect_case_insensitive(context_factory, run_rgaa):
    """Meta redirect insensible à la casse."""
    html = '<!DOCTYPE html><html><head><META HTTP-EQUIV="REFRESH" CONTENT="0;URL=HTTPS://EXAMPLE.COM"></head><body></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1312(), context)

    assert result.status == Status.PASS


def test_1313_js_redirect_case_insensitive(context_factory, run_rgaa):
    """Redirection JS insensible à la casse."""
    html = '<!DOCTYPE html><html><body><script>WINDOW.LOCATION.HREF = "https://example.com";</script></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
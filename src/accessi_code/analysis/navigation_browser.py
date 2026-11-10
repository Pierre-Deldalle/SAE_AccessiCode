"""Collecte de preuves *positives* RGAA 12 dans Chromium.

Ne conclut jamais PASS à partir de la simple présence de HTML. Les preuves
sont ajoutées uniquement après observation de pages réellement rendues.
Les cas dynamiques/complexes restent à vérifier.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.analysis.browser import launch_local_browser

# Observation du DOM rendu : on ne modifie pas le document audité.
_SNAPSHOT = r"""() => {
  const visible = e => {
    if (!e) return false;
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' &&
           Number(s.opacity) > 0 && r.width > 0 && r.height > 0;
  };
  const box = e => {
    if (!e || !visible(e)) return null;
    const p = e.closest('header, footer') || document.body;
    const a = e.getBoundingClientRect(), b = p.getBoundingClientRect();
    return {region: p.tagName.toLowerCase(), x: a.left - b.left,
            y: a.top - b.top, width: a.width, height: a.height};
  };
  const text = e => (e.textContent || '').replace(/\s+/g,' ').trim().toLowerCase();
  const nav = [...document.querySelectorAll('nav, [role="navigation"]')];
  const sitemap = [...document.querySelectorAll('a[href]')].find(e =>
    text(e).includes('plan du site') || /sitemap|plan-du-site/i.test(e.getAttribute('href') || ''));
  const search = document.querySelector('form[role="search"], [role="search"], input[type="search"]') ||
    [...document.querySelectorAll('a[href]')].find(e => text(e).includes('recherche') ||
      /search/i.test(e.getAttribute('href') || ''));
  const main = document.querySelector('main, [role="main"]');
  const skip = [...document.querySelectorAll('a[href^="#"]')].find(e => {
    const id = decodeURIComponent((e.getAttribute('href') || '').slice(1));
    if (!id || !main) return false;
    const target = document.getElementById(id);
    return target && (target === main || main.contains(target));
  });
  return {nav: nav.map(box), sitemap: box(sitemap), search: box(search),
          skip: box(skip), skipHref: skip?.getAttribute('href') || null,
          hasScripts: !!document.querySelector('script, iframe, frame, object, embed, dialog, [role="dialog"], [role="tablist"]'),
          hasComplex: !!document.querySelector('[contenteditable], [tabindex]:not([tabindex="0"]), [aria-activedescendant]')};
}"""

_FOCUS_INIT = r"""() => {
  const selector = 'a[href], area[href], button, input:not([type="hidden"]), select, textarea, [tabindex], [contenteditable]';
  const visible = e => {const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;};
  const list = [...document.querySelectorAll(selector)].filter(e =>
    !e.disabled && !e.closest('[inert]') && !e.closest('[hidden]') &&
    e.tabIndex >= 0 && visible(e));
  list.forEach((e, i) => e.dataset.accessicodeFocusIndex = String(i));
  const rects = list.map(e => {const r=e.getBoundingClientRect();
    return {x:r.x, y:r.y, w:r.width, h:r.height};});
  return {count:list.length, rects};
}"""


async def _focus_sequence(page: Any, limit: int = 80) -> tuple[bool, bool]:
    """Vérifie réellement Tab/Maj+Tab ; second bool : cohérence spatiale simple.

    Les pages avec JS, iframe ou widgets personnalisés ne sont PAS déclarées
    conformes par cette routine : il faudrait activer chaque interaction.
    """
    data = await page.evaluate(_FOCUS_INIT)
    count = data["count"]
    if not 0 < count <= limit:
        return False, False
    forward = []
    for _ in range(count):
        await page.keyboard.press("Tab")
        forward.append(await page.evaluate("document.activeElement?.dataset.accessicodeFocusIndex ?? null"))
    if forward != [str(i) for i in range(count)]:
        return False, False
    backward = []
    for _ in range(count - 1):
        await page.keyboard.press("Shift+Tab")
        backward.append(await page.evaluate("document.activeElement?.dataset.accessicodeFocusIndex ?? null"))
    if backward != [str(i) for i in range(count - 2, -1, -1)]:
        return False, False
    # La disposition n'est pas forcément une grille : on ne confirme l'ordre
    # visuel que si les éléments se succèdent dans un flux vertical évident.
    rects = data["rects"]
    obvious = all(rects[i+1]["y"] >= rects[i]["y"] - 3 for i in range(count-1))
    return True, obvious


async def _skip_check(page: Any, href: str) -> tuple[bool, bool]:
    """Vérifie focus visible au clavier puis activation effective du fragment."""
    await page.goto(page.url.split('#')[0], wait_until="load", timeout=8000)
    # Tab depuis le document initial, pas un .focus() programmatique.
    found = False
    for _ in range(30):
        await page.keyboard.press("Tab")
        active = await page.evaluate("""() => {
          const e = document.activeElement;
          if (!e || e.tagName !== 'A') return null;
          const s=getComputedStyle(e), r=e.getBoundingClientRect();
          return {href:e.getAttribute('href'),visible:s.visibility!=='hidden' &&
             s.display!=='none' && r.width>0 && r.height>0};
        }""")
        if active and active.get("href") == href:
            found = bool(active["visible"])
            break
    if not found:
        return False, False
    await page.keyboard.press("Enter")
    functional = await page.evaluate("""() => {
      const id=decodeURIComponent(location.hash.slice(1));
      const target=id && document.getElementById(id);
      if (!target) return false;
      const active=document.activeElement;
      return active===target || target.contains(active);
    }""")
    return found, bool(functional)


def _same_boxes(boxes: list[dict[str, Any] | None], *, tolerance: float = 10) -> bool:
    """Seulement une confirmation positive, jamais une preuve d'échec."""
    if not boxes or any(not isinstance(box, dict) for box in boxes):
        return False
    first = boxes[0]
    return all(
        item["region"] == first["region"] and
        abs(item["x"] - first["x"]) <= tolerance and
        abs(item["y"] - first["y"]) <= tolerance
        for item in boxes[1:]
    )


def _collect_positive_positions(snapshots: list[dict[str, Any]]) -> dict[str, dict[str, bool]]:
    """Aucune preuve négative : différences de contenu ≠ échec RGAA certain."""
    output: dict[str, dict[str, bool]] = {}
    if len(snapshots) < 2:
        return output
    if all(len(s["nav"]) == len(snapshots[0]["nav"]) and s["nav"] for s in snapshots):
        if all(_same_boxes([s["nav"][i] for s in snapshots]) for i in range(len(snapshots[0]["nav"]))):
            output["12.2.1"] = {"same_visual_position": True}
    for key, test_id in (("sitemap", "12.4.2"), ("search", "12.5.2"), ("skip", "12.7.2")):
        if _same_boxes([s[key] for s in snapshots]):
            output.setdefault(test_id, {})["same_visual_position"] = True
    return output


async def collect_navigation_evidence(context: AuditContext) -> None:
    """Une seule session Chromium pour l'ensemble des pages HTML de l'audit.

    En cas d'indisponibilité : aucun PASS inventé, les tests conservent
    NEEDS_REVIEW. Aucune requête HTTP externe n'est effectuée.
    """
    if context.dom is None or context.html_path is None:
        return
    files: dict[str, Path] = {}
    for f in context.files:
        if f.path.suffix.lower() in {".html", ".htm"} and f.path.name in context.page_doms:
            files[f.path.name] = f.path
    if not files:
        files = {context.html_path.name: context.html_path}
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            browser = await launch_local_browser(playwright)
            try:
                page = await browser.new_page(java_script_enabled=False,
                                              viewport={"width": 1366, "height": 900})
                # Ne pas charger de ressources réseau non sollicitées.
                await page.route("http://**/*", lambda route: route.abort())
                await page.route("https://**/*", lambda route: route.abort())
                viewport_results = []
                skip_observations = []
                for width in (1366, 390):
                    await page.set_viewport_size({"width": width, "height": 900})
                    snapshots = []
                    for key, path in files.items():
                        await page.goto(path.resolve().as_uri(), wait_until="load", timeout=8000)
                        snap = await page.evaluate(_SNAPSHOT)
                        snapshots.append(snap)
                        # La géométrie serait faussée si la feuille CSS externe
                        # n'a pas pu être chargée (requêtes réseau bloquées).
                        if await page.evaluate("""() => [...document.querySelectorAll('link[rel="stylesheet"]')]
                            .some(el => /^https?:/i.test(el.href))"""):
                            snap["remoteCSS"] = True
                        if width == 1366:
                            if snap["skipHref"]:
                                skip_observations.append(await _skip_check(page, snap["skipHref"]))
                            else:
                                skip_observations.append((False, False))
                            if key == context.html_path.name and not snap["hasScripts"] and not snap["hasComplex"]:
                                await page.goto(path.resolve().as_uri(), wait_until="load", timeout=8000)
                                escaped, visual_order = await _focus_sequence(page)
                                if escaped:
                                    context.navigation_evidence.setdefault("12.9.1", {})["no_keyboard_trap"] = True
                                if escaped and visual_order:
                                    context.navigation_evidence.setdefault("12.8.1", {})["tab_order_coherent"] = True
                    if not any(s.get("remoteCSS") for s in snapshots):
                        viewport_results.append(_collect_positive_positions(snapshots))
                    else:
                        viewport_results.append({})
                if skip_observations and all(v for v, _ in skip_observations):
                    context.navigation_evidence.setdefault("12.7.1", {})["visible_on_focus"] = True
                    context.navigation_evidence.setdefault("12.7.2", {})["visible_on_focus"] = True
                if skip_observations and all(f for _, f in skip_observations):
                    context.navigation_evidence.setdefault("12.7.2", {})["functional"] = True
                # Deux tailles d'écran : une preuve seulement si elle est
                # confirmée sur desktop ET mobile pour chaque page.
                if len(viewport_results) == 2:
                    for test_id, props in viewport_results[0].items():
                        for key, value in props.items():
                            if value is True and viewport_results[1].get(test_id, {}).get(key) is True:
                                context.navigation_evidence.setdefault(test_id, {})[key] = True
            finally:
                await browser.close()
    except Exception as error:
        # Ne pas cacher l'échec de collecte : visible dans le contexte/log.
        context.visual_evidence_error = (
            (context.visual_evidence_error + "; " if context.visual_evidence_error else "") +
            f"Navigation Chromium : {type(error).__name__}: {error}"
        )
        print(f"[NAVIGATION] Preuves navigateur indisponibles : {type(error).__name__}: {error}", flush=True)

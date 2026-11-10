"""Mesures prudentes de proximité étiquette/champ dans Chromium (RGAA 11.4).

La limite de distance est un seuil de confirmation heuristique, PAS une norme
RGAA. Si la disposition n'est pas évidente, aucune preuve n'est fournie.
"""
from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.dom import find_form_fields, get_element_identifier
from accessi_code.models.audit_context import AuditContext
from accessi_code.analysis.browser import launch_local_browser

MAX_OBVIOUS_GAP_PX = 16


def classify_geometry(label: dict[str, float], field: dict[str, float],
                      direction: str, *, max_gap: float = MAX_OBVIOUS_GAP_PX) -> dict[str, Any] | None:
    if direction not in {"ltr", "rtl"}:
        return None
    for rect in (label, field):
        if not all(isinstance(rect.get(k), (int, float)) for k in
                   ("left", "right", "top", "bottom", "width", "height")):
            return None
        if rect["width"] <= 0 or rect["height"] <= 0:
            return None
    overlap_x = max(0, min(label["right"], field["right"]) - max(label["left"], field["left"]))
    overlap_y = max(0, min(label["bottom"], field["bottom"]) - max(label["top"], field["top"]))
    ratio_x = overlap_x / min(label["width"], field["width"])
    ratio_y = overlap_y / min(label["height"], field["height"])
    options = []
    if label["bottom"] <= field["top"] and ratio_x >= 0.35:
        options.append(("above", field["top"] - label["bottom"]))
    if label["top"] >= field["bottom"] and ratio_x >= 0.35:
        options.append(("below", label["top"] - field["bottom"]))
    if label["right"] <= field["left"] and ratio_y >= 0.35:
        options.append(("left", field["left"] - label["right"]))
    if label["left"] >= field["right"] and ratio_y >= 0.35:
        options.append(("right", label["left"] - field["right"]))
    if not options:
        return None
    position, gap = min(options, key=lambda option: option[1])
    if gap > max_gap:
        return None
    return {"adjacent": True, "position": position, "direction": direction,
            "gap_px": round(gap, 2), "heuristic_gap_px": max_gap}


_MEASURE_SCRIPT = r"""() => {
 const box = el => { const r=el.getBoundingClientRect();
   return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
 const visible = el => {if(!el)return false;const s=getComputedStyle(el),r=el.getBoundingClientRect();
   return s.display!=='none'&&s.visibility==='visible'&&Number(s.opacity)>0&&r.width>0&&r.height>0;};
 return [...document.querySelectorAll('[data-accessicode-field-index]')].map(el => {
   const index=Number(el.getAttribute('data-accessicode-field-index'));
   let label=el.labels?.length===1 ? el.labels[0] : el.closest('label');
   if(!label){const ids=(el.getAttribute('aria-labelledby')||'').trim().split(/\s+/).filter(Boolean);
     if(ids.length===1){const candidates=[...document.querySelectorAll('[id]')].filter(n=>n.id===ids[0]);
       if(candidates.length===1)label=candidates[0];}}
   if(!visible(el)||!visible(label))return {index,usable:false};
   return {index,usable:true,field:box(el),label:box(label),
     label_text:(label.innerText||label.textContent||'').trim().replace(/\s+/g,' '),
     direction:getComputedStyle(label).direction};
 });
}"""


def evidence_from_measurements(context: AuditContext, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    fields = find_form_fields(context.dom)
    identifiers = [get_element_identifier(field, i) for i, field in enumerate(fields)]
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        index = row.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(fields):
            continue
        if row.get("usable") is not True:
            continue
        identifier = identifiers[index]
        if identifiers.count(identifier) != 1:
            continue
        element_id = fields[index].get("id")
        if element_id and len(context.dom.find_all(id=element_id)) != 1:
            continue
        label_text = " ".join(str(row.get("label_text", "")).split())
        if not label_text or (re.search(r"[\u0590-\u08ff]", label_text) and
                              re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", label_text)):
            continue
        geometry = classify_geometry(row.get("label", {}), row.get("field", {}), row.get("direction", ""))
        if geometry is not None:
            records[identifier] = {"verified": True, "source": "browser",
                                   "label_text": label_text, **geometry}
    return records


async def collect_form_label_layout(context: AuditContext) -> None:
    """Renseigne les preuves visuelles lorsque Chromium est disponible.

    Les scripts de la page sont désactivés ; les pages dynamiques pourront
    nécessiter une vérification humaine. Ne modifie pas le DOM de l'audit.
    """
    if context.dom is None or context.html_path is None or not context.html_source:
        return
    if not find_form_fields(context.dom):
        return
    temporary_path: Path | None = None
    browser = None
    try:
        from playwright.async_api import async_playwright
        instrumented = BeautifulSoup(context.html_source, "html.parser")
        for index, field in enumerate(find_form_fields(instrumented)):
            field["data-accessicode-field-index"] = str(index)
        with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".html",
                                prefix=".accessicode_layout_", dir=context.html_path.parent,
                                delete=False) as temporary:
            temporary.write(str(instrumented))
            temporary_path = Path(temporary.name)
        async with async_playwright() as playwright:
            browser = await launch_local_browser(playwright)
            page = await browser.new_page(java_script_enabled=False,
                                          viewport={"width": 1366, "height": 900})
            await page.route("http://**/*", lambda route: route.abort())
            await page.route("https://**/*", lambda route: route.abort())
            await page.goto(temporary_path.as_uri(), wait_until="load", timeout=15000)
            rows = await page.evaluate(_MEASURE_SCRIPT)
            context.form_label_layout = evidence_from_measurements(context, rows)
            await browser.close()
            browser = None
    except Exception as exc:
        context.visual_evidence_error = f"{type(exc).__name__}: {exc}"
    finally:
        if browser is not None:
            await browser.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

"""Lancement Chromium/Edge pour les preuves visuelles locales.

Playwright peut être installé sans son binaire Chromium. Dans ce cas,
utiliser un navigateur local compatible, sans modifier les conclusions RGAA.
"""
from __future__ import annotations

import shutil
from pathlib import Path


async def launch_local_browser(playwright):
    errors = []
    candidates = [{}]
    candidates.append({"channel": "msedge"})  # Edge présent sur de nombreux Windows
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        executable = shutil.which(name)
        if executable:
            candidates.append({"executable_path": executable})
    for path in (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ):
        if path.is_file():
            candidates.append({"executable_path": str(path)})
    for options in candidates:
        try:
            return await playwright.chromium.launch(headless=True, timeout=10000, **options)
        except Exception as exc:
            errors.append(f"{options or 'Playwright Chromium'} : {type(exc).__name__}: {str(exc)[:140]}")
    raise RuntimeError("Aucun navigateur compatible accessible. " + " ; ".join(errors))

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from bs4 import BeautifulSoup

from accessi_code.analysis.page import get_document_doctype
from accessi_code.models.audit_context import AuditContext

_AUTO_DOCTYPE = object()
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


@pytest.fixture
def context_factory(tmp_path: Path):
    """
    Construit directement un AuditContext minimal pour les tests unitaires RGAA.

    On n'utilise volontairement pas AuditContextBuilder ici : ces tests doivent
    isoler les algorithmes RGAA du pipeline d'entrée, déjà testé séparément.
    """

    def build(
        html: str,
        *,
        resources: dict[str, str | bytes] | None = None,
        doctype: str | None | object = _AUTO_DOCTYPE,
    ) -> AuditContext:
        html_path = tmp_path / "index.html"
        html_path.write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "html.parser")

        # Crée de faux fichiers image locaux pour que les chemins référencés
        # dans le HTML puissent être résolus sans dépendre d'images réelles.
        image_files: list[Path] = []

        for tag in soup.find_all(["img", "input"]):
            if tag.name == "input" and str(tag.get("type", "")).lower() != "image":
                continue

            src = str(tag.get("src", "")).strip()
            if not src:
                continue

            parsed = urlparse(src)
            if parsed.scheme or parsed.netloc or src.startswith("data:"):
                continue

            local_path = tmp_path / parsed.path
            if local_path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue

            local_path.parent.mkdir(parents=True, exist_ok=True)
            if not local_path.exists():
                local_path.write_bytes(b"fake-image")
            image_files.append(local_path)

        for name, content in (resources or {}).items():
            resource_path = tmp_path / name
            resource_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, bytes):
                resource_path.write_bytes(content)
            else:
                resource_path.write_text(content, encoding="utf-8")

            if resource_path.suffix.lower() in _IMAGE_EXTENSIONS:
                image_files.append(resource_path)

        resolved_doctype = get_document_doctype(html) if doctype is _AUTO_DOCTYPE else doctype

        return AuditContext(
            audit_id="unit-test",
            workspace_path=tmp_path,
            html_path=html_path,
            html_source=html,
            dom=soup,
            doctype=resolved_doctype,
            image_files=list(dict.fromkeys(image_files)),
        )

    return build


@pytest.fixture
def run_rgaa():
    """
    Exécute directement un RGAATest async sans dépendre de pytest-asyncio.
    """

    def run(test: Any, context: AuditContext, services: Any | None = None):
        return asyncio.run(test.run(context, services))

    return run

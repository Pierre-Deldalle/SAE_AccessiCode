"""
RGAA 4.1.2 — critère 11.9 : dans chaque formulaire, l'intitulé de chaque bouton
est-il pertinent (hors cas particuliers) ?

- 11.9.1 : bouton sans nom accessible : non conforme ; sinon l'IA juge si
  l'intitulé indique l'action déclenchée.
- 11.9.2 : chaque source de nom accessible contient l'intitulé visible
  (majuscules et ponctuation ignorées, cas particuliers du critère 11.2).
  Pour un bouton image, le texte affiché dans l'image est lu par le VLM.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import ImageProfile, RelevanceItem
from accessi_code.analysis.forms import (
    button_name,
    button_visible,
    buttons,
    clean,
    form_summary,
    identifier,
    referenced_text,
)
from accessi_code.analysis.images import ImageInfo, resolve_image_source
from accessi_code.analysis.location import opening_tag
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.ai_decision import NO_AI_MESSAGE, get_analyzer, judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable
from accessi_code.rgaa.tests.theme_11_forms._examples import example


def _visible_name_example(tag: Tag, visible: str, missing: list[str]) -> str:
    """Attributs de nom (aria-label, title, alt, value) qui reprennent l'intitulé visible ; aria-labelledby exclu."""
    changes = {source: visible for source in missing if source != "aria-labelledby"}
    return example(opening_tag(tag), opening_tag(tag, **changes)) if changes else ""


def _comparable(text: str) -> str:
    """Majuscules, accents et ponctuation ignorés (cas particuliers du critère 11.2)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    kept = "".join(
        " " if unicodedata.category(char).startswith("P") else char
        for char in decomposed
        if not unicodedata.combining(char)
    )
    return " ".join(kept.split())


def name_sources(tag: Tag, soup: BeautifulSoup) -> dict[str, str]:
    """Sources de nom accessible présentes sur le bouton."""
    sources = {
        "aria-label": clean(tag.get("aria-label")),
        "aria-labelledby": referenced_text(tag, soup, "aria-labelledby"),
        "title": clean(tag.get("title")),
    }
    if tag.name == "input":
        sources["alt" if clean(tag.get("type")).lower() == "image" else "value"] = clean(
            tag.get("alt") if clean(tag.get("type")).lower() == "image" else tag.get("value")
        )
    return {key: value for key, value in sources.items() if value}


class Test1191(RGAATest):
    """11.9.1 : l'intitulé de chaque bouton est-il pertinent ?"""

    test_id = "11.9.1"
    criterion_id = "11.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.9.1 nécessite un DOM.")
        candidates = buttons(soup)
        if not candidates:
            return not_applicable(self, "Aucun bouton de formulaire.")

        recommendation = "Rédiger un intitulé de bouton qui décrit l'action déclenchée."
        outcomes = []
        pending: list[tuple[Tag, str]] = []
        for tag in candidates:
            name = button_name(tag, soup)
            if name:
                pending.append((tag, name))
            else:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        identifier(tag, soup),
                        "Le bouton n'a pas d'intitulé.",
                        recommendation,
                        node=tag,
                    )
                )

        items = [
            RelevanceItem(
                text=name,
                element_html=str(tag)[:300],
                context=form_summary(tag.find_parent("form"), soup) if tag.find_parent("form") else "",
                details={"type": clean(tag.get("type")) or tag.name},
            )
            for tag, name in pending
        ]
        verdicts = await judge_relevance(services, "button", items)
        for (tag, name), verdict in zip(pending, verdicts, strict=True):
            outcomes.append(
                make_outcome(
                    verdict.status,
                    identifier(tag, soup),
                    verdict.message(
                        f"L'intitulé « {name[:100]} » n'indique pas l'action du bouton.",
                        f"La pertinence de l'intitulé « {name[:100]} » reste à vérifier.",
                    ),
                    verdict.recommendation(recommendation),
                    node=tag,
                    accessible_name=name,
                    **verdict.evidence,
                )
            )
        return build_result(self, outcomes, empty_summary="Aucun bouton de formulaire.", noun="bouton(s)")


class Test1192(RGAATest):
    """11.9.2 : chaque source de nom accessible contient-elle au moins l'intitulé visible ?"""

    test_id = "11.9.2"
    criterion_id = "11.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError("Le test 11.9.2 nécessite un DOM.")

        outcomes = []
        for tag in buttons(soup):
            sources = name_sources(tag, soup)
            if clean(tag.get("type")).lower() == "image":
                outcomes.append(await self._image_button(tag, soup, sources, context, services))
                continue
            visible = button_visible(tag)
            if not visible or not sources:
                continue
            outcomes.append(self._compare(tag, soup, visible, sources))

        return build_result(self, outcomes, empty_summary="Aucun bouton avec un intitulé visible.", noun="bouton(s)")

    @staticmethod
    def _compare(tag: Tag, soup: BeautifulSoup, visible: str, sources: dict[str, str]):
        missing = [source for source, text in sources.items() if _comparable(visible) not in _comparable(text)]
        if not missing:
            return make_outcome(TestStatus.PASS)
        symbol_only = not any(char.isalnum() for char in visible)
        return make_outcome(
            TestStatus.NEEDS_REVIEW if symbol_only else TestStatus.FAIL,
            identifier(tag, soup),
            (
                f"L'intitulé visible « {visible} » est un symbole : vérifier que le nom accessible exprime sa fonction."
                if symbol_only
                else f"L'intitulé visible « {visible[:80]} » n'est pas contenu dans : "
                + ", ".join(f"{source} « {sources[source][:80]} »" for source in missing)
                + "."
            ),
            "Faire commencer le nom accessible par l'intitulé visible du bouton."
            + ("" if symbol_only else _visible_name_example(tag, visible, missing)),
            node=tag,
            visible_text=visible,
            sources=sources,
        )

    async def _image_button(self, tag, soup, sources, context, services):
        analyzer = get_analyzer(services, "image_analyzer")
        recommendation = "Reprendre dans l'attribut alt le texte affiché dans l'image du bouton."
        if analyzer is None:
            return make_outcome(
                TestStatus.NEEDS_REVIEW,
                identifier(tag, soup),
                f"Le texte affiché dans l'image du bouton doit être comparé à son nom accessible. {NO_AI_MESSAGE}",
                recommendation,
                node=tag,
            )
        src = clean(tag.get("src"))
        base_dir = context.html_path.parent if context.html_path is not None else None
        image_path, image_data = resolve_image_source(src, base_dir)
        image = ImageInfo(
            src=src,
            alt=tag.get("alt"),
            element_html=str(tag)[:500],
            context_text=form_summary(tag.find_parent("form"), soup) if tag.find_parent("form") else "",
            image_path=image_path,
            image_data=image_data,
        )
        try:
            profile = await analyzer.profile(image)
            if not isinstance(profile, ImageProfile):
                raise TypeError("ImageProfile attendu.")
        except Exception as error:
            return make_outcome(
                TestStatus.ERROR,
                identifier(tag, soup),
                "L'analyse IA de l'image du bouton a échoué.",
                "Relancer l'audit ou vérifier manuellement.",
                node=tag,
                error=f"{type(error).__name__}: {error}",
            )
        if profile.confidence == "low" or profile.contains_text is None:
            return make_outcome(
                TestStatus.NEEDS_REVIEW,
                identifier(tag, soup),
                "Le texte affiché dans l'image du bouton n'a pas pu être lu avec certitude.",
                recommendation,
                node=tag,
            )
        if profile.contains_text is False or not profile.text_content:
            return make_outcome(TestStatus.NOT_APPLICABLE)
        if not sources:
            return make_outcome(
                TestStatus.FAIL,
                identifier(tag, soup),
                "Le bouton image n'a pas de nom accessible.",
                recommendation,
                node=tag,
            )
        return self._compare(tag, soup, profile.text_content, sources)

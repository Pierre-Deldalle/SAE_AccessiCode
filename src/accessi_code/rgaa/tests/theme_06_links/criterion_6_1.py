"""
RGAA 4.1.2 — critère 6.1 : chaque lien est-il explicite ?

Tests 6.1.1 (lien texte), 6.1.2 (lien image), 6.1.3 (lien composite) et
6.1.4 (lien SVG) : l'intitulé du lien, seul ou associé à son contexte,
permet-il d'en comprendre la fonction et la destination ?

- l'intitulé (nom accessible) et le contexte du lien sont extraits du DOM ;
- un lien sans intitulé est non conforme sans appel à l'IA (voir aussi 6.2.1) ;
- sinon l'IA juge le caractère explicite, par lots, avec la destination
  (href), le contexte et, le cas échéant, les autres destinations désignées
  par le même intitulé dans la page.

Test 6.1.5 : l'intitulé visible est-il contenu dans le nom accessible ?
Contrôle déterministe, sans IA.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.analysis.links import (
    COMPOSITE_LINK,
    IMAGE_LINK,
    SVG_LINK,
    TEXT_LINK,
    accessible_name,
    image_alternative,
    is_html_link,
    is_svg_link,
    link_context,
    link_href,
    link_identifier,
    link_images,
    link_kind,
    page_links,
    svg_text,
    visible_text,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.ai_decision import judge_relevance
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome, not_applicable

RECOMMENDATION = (
    "Rendre le lien explicite : préciser son intitulé ou le placer dans un contexte "
    "(phrase, item de liste, cellule, titre de section) qui indique sa destination."
)
EMPTY_LABEL_RECOMMENDATION = "Donner un intitulé au lien (texte, alternative de l'image ou aria-label)."


def _destinations_by_label(links: list[Tag], soup: BeautifulSoup) -> dict[str, set[str]]:
    """Destinations désignées par chaque intitulé (insensible à la casse) dans la page."""
    destinations: dict[str, set[str]] = defaultdict(set)
    for link in links:
        name, _ = accessible_name(link, soup)
        href = link_href(link)
        if name and href:
            destinations[name.casefold()].add(href.strip())
    return destinations


class ExplicitLinkTest(RGAATest):
    """Base des tests 6.1.1 à 6.1.4 : un type de lien, jugé par l'IA."""

    criterion_id = "6.1"
    required_capabilities = frozenset({Capability.DOM})

    link_type: str = TEXT_LINK
    noun: str = "lien(s)"
    empty_summary: str = "Aucun lien concerné."

    def details(self, link: Tag, soup: BeautifulSoup) -> dict[str, Any]:
        """Informations propres au type de lien transmises à l'IA."""
        return {}

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM HTML.")

        soup = context.dom
        all_links = page_links(soup)
        links = [link for link in all_links if link_kind(link) == self.link_type]
        if not links:
            return not_applicable(self, self.empty_summary)

        destinations = _destinations_by_label(all_links, soup)
        outcomes: list[Outcome | None] = [None] * len(links)
        to_judge: list[tuple[int, RelevanceItem]] = []

        for position, link in enumerate(links):
            name, source = accessible_name(link, soup)
            if not name:
                outcomes[position] = make_outcome(
                    TestStatus.FAIL,
                    link_identifier(link, position),
                    "Le lien n'a pas d'intitulé : il ne peut pas être explicite.",
                    EMPTY_LABEL_RECOMMENDATION,
                    node=link,
                    href=link_href(link),
                )
                continue

            href = (link_href(link) or "").strip()
            details: dict[str, Any] = {"href": href, "label_source": source, **self.details(link, soup)}
            others = sorted(destinations.get(name.casefold(), set()) - {href})
            if others:
                details["same_label_other_destinations"] = ", ".join(others[:5])
            item = RelevanceItem(text=name, element_html=str(link)[:400], context=link_context(link), details=details)
            to_judge.append((position, item))

        verdicts = await judge_relevance(services, "link", [item for _, item in to_judge])

        for (position, item), verdict in zip(to_judge, verdicts, strict=True):
            link = links[position]
            outcomes[position] = make_outcome(
                verdict.status,
                link_identifier(link, position),
                verdict.message(
                    f"Le lien « {item.text[:100]} » n'est pas explicite, même avec son contexte.",
                    f"Le caractère explicite du lien « {item.text[:100]} » reste à vérifier.",
                ),
                verdict.recommendation(RECOMMENDATION),
                node=link,
                label=item.text,
                context=item.context,
                **item.details,
                **verdict.evidence,
            )

        return build_result(
            self,
            [item for item in outcomes if item is not None],
            empty_summary=self.empty_summary,
            noun=self.noun,
        )


def _image_details(link: Tag, soup: BeautifulSoup) -> dict[str, Any]:
    images = [link] if link.name == "area" else link_images(link)
    described = [f"{image.name} : « {image_alternative(image, soup)} »" for image in images]
    return {"images": " / ".join(described)}


class Test611(ExplicitLinkTest):
    """6.1.1 : chaque lien texte est-il explicite (intitulé seul ou avec son contexte) ?"""

    test_id = "6.1.1"
    link_type = TEXT_LINK
    noun = "lien(s) texte"
    empty_summary = "Aucun lien texte."


class Test612(ExplicitLinkTest):
    """
    6.1.2 : chaque lien image est-il explicite ?

    L'alternative de l'image tient lieu d'intitulé : l'IA juge si elle indique
    la destination du lien. La correspondance entre l'alternative et le contenu
    visuel de l'image relève du critère 1.3, qui la vérifie déjà avec le VLM.
    """

    test_id = "6.1.2"
    link_type = IMAGE_LINK
    noun = "lien(s) image"
    empty_summary = "Aucun lien image."

    def details(self, link: Tag, soup: BeautifulSoup) -> dict[str, Any]:
        return _image_details(link, soup)


class Test613(ExplicitLinkTest):
    """6.1.3 : chaque lien composite (texte et image) est-il explicite ?"""

    test_id = "6.1.3"
    link_type = COMPOSITE_LINK
    noun = "lien(s) composite(s)"
    empty_summary = "Aucun lien composite."

    def details(self, link: Tag, soup: BeautifulSoup) -> dict[str, Any]:
        return _image_details(link, soup)


class Test614(ExplicitLinkTest):
    """6.1.4 : chaque lien SVG est-il explicite ?"""

    test_id = "6.1.4"
    link_type = SVG_LINK
    noun = "lien(s) SVG"
    empty_summary = "Aucun lien SVG."

    def details(self, link: Tag, soup: BeautifulSoup) -> dict[str, Any]:
        root = link.find_parent("svg")
        description = root.find("desc", recursive=False) if isinstance(root, Tag) else None
        if isinstance(description, Tag) and description.get_text(strip=True):
            return {"svg_description": " ".join(description.get_text(" ", strip=True).split())}
        return {}


class Test615(RGAATest):
    """
    RGAA 4.1.2 — Test 6.1.5.

    Vérifie que le nom accessible candidat d'un lien contient
    son intitulé visible.

    Les verdicts automatiques sont réservés aux cas simples
    où les informations du DOM sont suffisamment fiables.
    """

    test_id = "6.1.5"
    criterion_id = "6.1"

    required_capabilities = frozenset({Capability.DOM})

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def _comparable(cls, value: str) -> str:
        """Ignore la casse et la ponctuation pour la comparaison."""
        value = value.casefold()
        value = "".join(" " if unicodedata.category(char).startswith("P") else char for char in value)
        return cls._normalize(value)

    @staticmethod
    def _has_symbol(value: str) -> bool:
        """Repère les symboles potentiellement non littéraux."""
        return any(unicodedata.category(char).startswith("S") for char in value)

    @staticmethod
    def _is_svg_link(element: Tag) -> bool:
        return is_svg_link(element)

    @classmethod
    def _is_link(cls, element: Tag) -> bool:
        if cls._is_svg_link(element):
            return True

        if element.name == "area" and element.has_attr("href"):
            return True

        return is_html_link(element)

    @staticmethod
    def _is_hidden(element: Tag) -> bool:
        """Vérifie les indices explicites de masquage."""
        for ancestor in [element, *element.parents]:
            if not isinstance(ancestor, Tag):
                continue

            if ancestor.has_attr("hidden"):
                return True

            if str(ancestor.get("aria-hidden", "")).strip().lower() == "true":
                return True

        return False

    @classmethod
    def _has_uncertain_visibility(cls, element: Tag) -> bool:
        """
        Repère les cas où la visibilité ou le nom accessible
        peuvent dépendre du rendu CSS ou de composants complexes.
        """
        for node in [element, *element.descendants]:
            if not isinstance(node, Tag):
                continue

            if node.has_attr("class") or node.has_attr("style"):
                return True

            if node.has_attr("aria-labelledby") and node is not element:
                return True

            if node.has_attr("aria-label") and node is not element:
                return True

            if node.has_attr("aria-hidden"):
                return True

            if node.has_attr("hidden"):
                return True

            if node.name in {
                "img",
                "canvas",
                "object",
                "iframe",
                "math",
            }:
                return True

            if node.name == "svg" and not cls._is_svg_link(element):
                return True

            if node.has_attr("role") and node is not element:
                return True

        return False

    @classmethod
    def _visible_label(cls, element: Tag) -> str:
        """
        Extrait une approximation textuelle de l'intitulé visible.

        Les intitulés représentés graphiquement, par CSS ou par
        des images nécessiteront une vérification manuelle.
        """
        if element.name == "area":
            return ""

        if cls._is_svg_link(element):
            return svg_text(element)

        return visible_text(element)

    @classmethod
    def _get_accessible_name_candidate(
        cls,
        element: Tag,
        soup: BeautifulSoup,
        visible_label: str,
    ) -> tuple[str, str, bool]:
        """
        Retourne : nom candidat, source, incertitude.

        Attention : ne constitue pas une implémentation complète
        de l'algorithme Accessible Name Computation.
        """

        if element.has_attr("aria-labelledby"):
            references = cls._normalize(str(element.get("aria-labelledby", ""))).split()

            if not references:
                return "", "aria-labelledby_empty", True

            texts: list[str] = []

            for reference in references:
                target = soup.find(id=reference)

                if not isinstance(target, Tag):
                    return "", "aria-labelledby_invalid", True

                if target.find(["img", "svg", "object", "canvas", "math"]) is not None:
                    return "", "aria-labelledby_complex", True

                if (
                    target.has_attr("style")
                    or target.has_attr("class")
                    or target.has_attr("aria-label")
                    or target.has_attr("aria-labelledby")
                ):
                    return "", "aria-labelledby_complex", True

                text = cls._normalize(target.get_text(" ", strip=True))

                if not text:
                    return "", "aria-labelledby_empty_target", True

                texts.append(text)

            return " ".join(texts), "aria-labelledby", False

        aria_label = cls._normalize(str(element.get("aria-label", "")))

        if aria_label:
            return aria_label, "aria-label", False

        if cls._is_svg_link(element):
            # Le nom d'un lien SVG peut aussi dépendre d'un
            # title ou de mécanismes SVG spécifiques.
            direct_title = element.find("title", recursive=False)

            if isinstance(direct_title, Tag):
                title = cls._normalize(direct_title.get_text(" ", strip=True))

                if title:
                    return title, "svg_title_candidate", True

            xlink_title = cls._normalize(str(element.get("xlink:title", "")))

            if xlink_title:
                return xlink_title, "xlink_title_candidate", True

            if visible_label:
                return visible_label, "svg_text_candidate", True

            return "", "svg_name_unknown", True

        # Pour un lien HTML textuel simple, le nom accessible
        # est normalement calculé à partir du contenu.
        if visible_label:
            return visible_label, "text_content", False

        return "", "unknown", True

    @classmethod
    def _check_link(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[TestStatus | None, dict[str, Any], str]:
        """
        Évalue un lien.

        None signifie que le lien ne possède pas d'intitulé
        visible exploitable par cette analyse.
        """
        visible = cls._visible_label(link)

        evidence: dict[str, Any] = {
            "href": link_href(link),
            "visible_label": visible,
            "accessible_name_candidate": "",
            "name_source": "none",
        }

        if cls._is_hidden(link):
            return None, evidence, "Lien masqué."

        if not visible:
            # Une image ou un contenu CSS peut constituer
            # un intitulé visible sans texte HTML détectable.
            if cls._has_uncertain_visibility(link):
                return (
                    TestStatus.NEEDS_REVIEW,
                    evidence,
                    "L'intitulé visible doit être vérifié.",
                )

            return None, evidence, "Aucun intitulé visible détecté."

        name, source, uncertain = cls._get_accessible_name_candidate(
            link,
            soup,
            visible,
        )

        evidence["accessible_name_candidate"] = name
        evidence["name_source"] = source

        if uncertain or cls._has_uncertain_visibility(link):
            return (
                TestStatus.NEEDS_REVIEW,
                evidence,
                "Nom accessible ou visibilité à confirmer.",
            )

        # Un symbole peut devoir être exprimé par une
        # formulation différente de son caractère visible.
        if cls._has_symbol(visible):
            return (
                TestStatus.NEEDS_REVIEW,
                evidence,
                "Cas particulier possible : intitulé symbolique.",
            )

        comparable_visible = cls._comparable(visible)
        comparable_name = cls._comparable(name)

        if not comparable_visible:
            return (
                TestStatus.NEEDS_REVIEW,
                evidence,
                "L'intitulé visible ne permet pas une comparaison automatique fiable.",
            )

        if comparable_visible in comparable_name:
            return (
                TestStatus.PASS,
                evidence,
                "L'intitulé visible est contenu dans le nom accessible candidat.",
            )

        return (
            TestStatus.FAIL,
            evidence,
            "Le nom accessible candidat ne contient pas l'intitulé visible.",
        )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Exécute le contrôle partiel RGAA 6.1.5."""
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 6.1.5 nécessite un DOM HTML.")
        soup = context.dom

        links = [node for node in soup.find_all(True) if self._is_link(node)]

        findings: list[Finding] = []
        counts = {
            TestStatus.PASS: 0,
            TestStatus.FAIL: 0,
            TestStatus.NEEDS_REVIEW: 0,
        }
        not_applicable = 0

        for index, link in enumerate(links):
            status, evidence, reason = self._check_link(
                link,
                soup,
            )

            if status is None:
                not_applicable += 1
                continue

            counts[status] += 1

            if status == TestStatus.PASS:
                continue

            findings.append(
                Finding(
                    element=link_identifier(link, index),
                    message=reason,
                    recommendation=(
                        "Vérifier le nom accessible réellement "
                        "calculé dans le navigateur. S'il ne "
                        "contient pas l'intitulé visible, "
                        "adapter aria-label, aria-labelledby "
                        "ou le contenu du lien en respectant "
                        "les cas particuliers du RGAA."
                    ),
                    evidence=evidence,
                )
            )

        tested = sum(counts.values())

        if tested == 0:
            result_status = TestStatus.NOT_APPLICABLE
        elif counts[TestStatus.FAIL]:
            result_status = TestStatus.FAIL
        elif counts[TestStatus.NEEDS_REVIEW]:
            result_status = TestStatus.NEEDS_REVIEW
        else:
            result_status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=result_status,
            summary=(
                f"{tested} lien(s) évalué(s) : "
                f"{counts[TestStatus.PASS]} conforme(s) "
                "selon l'analyse statique, "
                f"{counts[TestStatus.FAIL]} échec(s), "
                f"{counts[TestStatus.NEEDS_REVIEW]} "
                "à vérifier."
            ),
            findings=findings,
            tested_elements=tested,
            metadata={
                "candidate_links": len(links),
                "checked_links": tested,
                "passed_links": counts[TestStatus.PASS],
                "failed_links": counts[TestStatus.FAIL],
                "needs_review": counts[TestStatus.NEEDS_REVIEW],
                "without_detected_visible_label": not_applicable,
                "browser_accessible_name_verified": False,
            },
        )

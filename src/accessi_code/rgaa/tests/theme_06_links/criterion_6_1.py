"""
RGAA 4.1.2 — Critère 6.1 — Liens explicites.

Test 6.1.1 : liens textuels.

Cette implémentation prépare une analyse sémantique :
- identification des liens textuels ;
- extraction de leur intitulé ;
- extraction d'un contexte pertinent ;
- signalement des éléments à vérifier.

Aucun verdict sémantique n'est inventé à partir du DOM seul.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


class Test611(RGAATest):
    """Prépare l'évaluation du caractère explicite des liens textuels."""

    test_id = "6.1.1"
    criterion_id = "6.1"

    required_capabilities = frozenset({Capability.DOM})

    # Un lien contenant ces éléments ne relève pas du
    # seul test des liens textuels.
    IMAGE_ELEMENTS = frozenset({"img", "svg", "object", "canvas"})

    @classmethod
    def _normalize(cls, value: str) -> str:
        """Supprime les espaces superflus."""
        return " ".join(value.split())

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        """Récupère le DOM de l'audit."""
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 6.1.1 nécessite un DOM HTML.")

        return context.dom

    @staticmethod
    def _is_link(element: Tag) -> bool:
        """Détecte un lien HTML ou un élément role=link."""
        role = str(element.get("role", "")).strip().lower()

        if role == "link":
            return True

        return element.name == "a" and element.has_attr("href") and role == ""

    @classmethod
    def _is_text_link(cls, element: Tag) -> bool:
        """
        Écarte les liens image et composites.

        Leur analyse sera effectuée dans les autres
        tests du critère 6.1.
        """
        if not cls._is_link(element):
            return False

        # Un lien <a> interne à un SVG relève du test 6.1.4,
        # et non du test 6.1.1, même s'il contient du texte SVG.
        if element.name == "a" and element.find_parent("svg") is not None:
            return False

        for descendant in element.descendants:
            if not isinstance(descendant, Tag):
                continue

            if descendant.name in cls.IMAGE_ELEMENTS:
                return False

            role = str(descendant.get("role", "")).strip().lower()

            if role == "img":
                return False

        return True

    @classmethod
    def _visible_text(cls, element: Tag) -> str:
        """
        Extrait le texte du lien en écartant les
        éléments explicitement masqués ou non textuels.

        Il s'agit d'une approximation statique.
        """
        parts = []

        for child in element.descendants:
            if not isinstance(child, str):
                continue

            parent = child.parent

            if not isinstance(parent, Tag):
                continue

            ignored = False

            for ancestor in [parent, *parent.parents]:
                if not isinstance(ancestor, Tag):
                    continue

                if ancestor is element.parent:
                    break

                if ancestor.name in {
                    "script",
                    "style",
                    "template",
                }:
                    ignored = True
                    break

                if str(ancestor.get("aria-hidden", "")).lower() == "true":
                    ignored = True
                    break

                if ancestor.has_attr("hidden"):
                    ignored = True
                    break

            if not ignored:
                text = cls._normalize(str(child))

                if text:
                    parts.append(text)

        return cls._normalize(" ".join(parts))

    @classmethod
    def _get_label(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str]:
        """
        Extrait une proposition d'intitulé accessible.

        Le calcul complet appartient au navigateur.
        """

        labelledby = str(link.get("aria-labelledby", "")).split()

        if labelledby:
            texts = []

            for reference in labelledby:
                target = soup.find(id=reference)

                if isinstance(target, Tag):
                    text = cls._normalize(target.get_text(" ", strip=True))

                    if text:
                        texts.append(text)

            if texts and len(texts) == len(labelledby):
                return " ".join(texts), "aria-labelledby"

            return "", "aria-labelledby_incomplete"

        aria_label = cls._normalize(str(link.get("aria-label", "")))

        if aria_label:
            return aria_label, "aria-label"

        content = cls._visible_text(link)

        if content:
            return content, "content"

        title = cls._normalize(str(link.get("title", "")))

        if title:
            return title, "title"

        return "", "none"

    @classmethod
    def _get_context(cls, link: Tag) -> dict[str, str]:
        """
        Extrait quelques contextes structurés du RGAA.

        Les associations complexes (notamment en tableau)
        et les phrases doivent encore être validées.
        """
        context: dict[str, str] = {}

        paragraph = link.find_parent("p")

        if isinstance(paragraph, Tag):
            context["paragraph"] = cls._normalize(paragraph.get_text(" ", strip=True))

        list_item = link.find_parent("li")

        if isinstance(list_item, Tag):
            context["list_item"] = cls._normalize(list_item.get_text(" ", strip=True))

        cell = link.find_parent(["td", "th"])

        if isinstance(cell, Tag):
            context["table_cell"] = cls._normalize(cell.get_text(" ", strip=True))

        # On ne recherche pas de titre arbitraire dans
        # toute la page : seulement un titre frère précédent.
        heading = link.find_previous_sibling(["h1", "h2", "h3", "h4", "h5", "h6"])

        if isinstance(heading, Tag):
            context["preceding_heading"] = cls._normalize(heading.get_text(" ", strip=True))

        return {key: value for key, value in context.items() if value}

    @staticmethod
    def _identifier(link: Tag, index: int) -> str:
        """Identifie le lien dans les observations."""
        element_id = link.get("id")

        if isinstance(element_id, str) and element_id.strip():
            return f"{link.name}#{element_id}"

        return f"{link.name}[index={index}]"

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Exécute la phase de préparation du test 6.1.1."""
        soup = self._get_dom(context)

        links = [element for element in soup.find_all(True) if self._is_text_link(element)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien textuel concerné détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []

        for index, link in enumerate(links):
            label, label_source = self._get_label(
                link,
                soup,
            )

            visible_text = self._visible_text(link)
            link_context = self._get_context(link)

            findings.append(
                Finding(
                    element=self._identifier(link, index),
                    message=(
                        "Le caractère explicite du lien textuel "
                        "reste à évaluer : il faut vérifier que "
                        "l'intitulé seul ou associé à son contexte "
                        "permet de comprendre sa fonction "
                        "et sa destination."
                    ),
                    recommendation=(
                        "Vérifier le sens du lien et, si nécessaire, "
                        "préciser son intitulé ou son contexte. "
                        "Un intitulé absent doit également être "
                        "contrôlé avec le test RGAA 6.2.1."
                    ),
                    evidence={
                        "href": link.get("href"),
                        "label": label,
                        "label_source": label_source,
                        "visible_text": visible_text,
                        "context": link_context,
                    },
                )
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=(
                f"{len(links)} lien(s) textuel(s) détecté(s) : "
                "leur caractère explicite nécessite "
                "une évaluation sémantique."
            ),
            findings=findings,
            tested_elements=len(links),
            metadata={
                "candidate_text_links": len(links),
                "needs_review": len(links),
                "semantic_analysis_performed": False,
            },
        )


class Test612(RGAATest):
    """
    RGAA 6.1.2 — Caractère explicite des liens images.

    Prépare les éléments nécessaires à une évaluation
    sémantique de l'intitulé et du contexte.

    Ce test ne produit pas de verdict sémantique définitif
    à partir du seul DOM statique.
    """

    test_id = "6.1.2"
    criterion_id = "6.1"

    required_capabilities = frozenset({Capability.DOM})

    IMAGE_TAGS = frozenset({"img", "svg", "object", "canvas"})

    @classmethod
    def _is_image_element(cls, element: Tag) -> bool:
        """Identifie une image native ou un rôle image."""
        if element.name in cls.IMAGE_TAGS:
            return True

        role = str(element.get("role", "")).strip().lower()
        return role == "img"

    @classmethod
    def _is_image_link(cls, element: Tag) -> bool:
        """
        Repère les liens images, à l'exclusion des liens
        composites et des liens SVG internes.

        Les liens SVG contenant leur propre élément <a>
        seront traités séparément en 6.1.4.
        """

        if element.name == "area":
            return element.has_attr("href")

        if element.name == "a" and element.find_parent("svg"):
            return False

        if not Test611._is_link(element):
            return False

        image_elements = [
            child for child in element.descendants if isinstance(child, Tag) and cls._is_image_element(child)
        ]

        if not image_elements:
            return False

        # Les liens associant du texte et une image
        # relèvent de 6.1.3.
        visible_text = cls._visible_link_text(element)

        if visible_text:
            return False

        return True

    @classmethod
    def _visible_link_text(cls, element: Tag) -> str:
        """
        Récupère le texte du lien hors images.

        Le texte situé dans les SVG et les composants image
        ne doit pas transformer un lien image en lien composite.
        """
        parts: list[str] = []

        for descendant in element.descendants:
            if not isinstance(descendant, str):
                continue

            parent = descendant.parent

            if not isinstance(parent, Tag):
                continue

            ignored = False

            for ancestor in [parent, *parent.parents]:
                if not isinstance(ancestor, Tag):
                    continue

                if ancestor is element.parent:
                    break

                if cls._is_image_element(ancestor):
                    ignored = True
                    break

                if ancestor.name in {
                    "script",
                    "style",
                    "template",
                }:
                    ignored = True
                    break

                if ancestor.has_attr("hidden"):
                    ignored = True
                    break

                if str(ancestor.get("aria-hidden", "")).strip().lower() == "true":
                    ignored = True
                    break

            if not ignored:
                text = Test611._normalize(str(descendant))

                if text:
                    parts.append(text)

        return Test611._normalize(" ".join(parts))

    @classmethod
    def _image_alternative(
        cls,
        image: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str]:
        """
        Extrait une proposition d'alternative textuelle.

        Le calcul complet du nom accessible devra être
        réalisé ou vérifié dans le navigateur.
        """

        references = str(image.get("aria-labelledby", "")).split()

        if references:
            texts: list[str] = []

            for reference in references:
                target = soup.find(id=reference)

                if isinstance(target, Tag):
                    text = Test611._normalize(target.get_text(" ", strip=True))

                    if text:
                        texts.append(text)

            if len(texts) == len(references):
                return " ".join(texts), "aria-labelledby"

            return "", "aria-labelledby_incomplete"

        for attribute in ("aria-label", "alt"):
            value = Test611._normalize(str(image.get(attribute, "")))

            if value:
                return value, attribute

        if image.name == "svg":
            svg_title = image.find("title", recursive=False)

            if isinstance(svg_title, Tag):
                text = Test611._normalize(svg_title.get_text(" ", strip=True))

                if text:
                    return text, "svg_title"

        if image.name in {"object", "canvas"}:
            fallback = Test611._normalize(image.get_text(" ", strip=True))

            if fallback:
                return fallback, "fallback_content"

        title = Test611._normalize(str(image.get("title", "")))

        if title:
            return title, "title"

        return "", "none"

    @classmethod
    def _get_image_link_label(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str, list[dict[str, str]]]:
        """
        Récupère une proposition d'intitulé de lien
        et les alternatives des images concernées.
        """

        if link.name == "area":
            label, source = cls._image_alternative(link, soup)

            return (
                label,
                source,
                [
                    {
                        "element": "area",
                        "alternative": label,
                        "source": source,
                    }
                ],
            )

        image_evidence: list[dict[str, str]] = []

        for image in link.descendants:
            if not isinstance(image, Tag):
                continue

            if not cls._is_image_element(image):
                continue

            # Évite de compter séparément les descendants
            # d'un élément image, par exemple le SVG lui-même.
            if any(
                isinstance(parent, Tag) and cls._is_image_element(parent)
                for parent in image.parents
                if parent is not link
            ):
                continue

            alternative, source = cls._image_alternative(
                image,
                soup,
            )

            image_evidence.append(
                {
                    "element": image.name,
                    "alternative": alternative,
                    "source": source,
                }
            )

        # Les attributs ARIA du lien lui-même ont priorité
        # dans cette approximation du nom accessible.
        labelledby = str(link.get("aria-labelledby", "")).split()

        if labelledby:
            texts: list[str] = []

            for reference in labelledby:
                target = soup.find(id=reference)

                if isinstance(target, Tag):
                    text = Test611._normalize(target.get_text(" ", strip=True))

                    if text:
                        texts.append(text)

            if len(texts) == len(labelledby):
                return (
                    " ".join(texts),
                    "link_aria-labelledby",
                    image_evidence,
                )

            return (
                "",
                "link_aria-labelledby_incomplete",
                image_evidence,
            )

        aria_label = Test611._normalize(str(link.get("aria-label", "")))

        if aria_label:
            return aria_label, "link_aria-label", image_evidence

        alternatives = [item["alternative"] for item in image_evidence if item["alternative"]]

        if alternatives:
            return (
                " ".join(alternatives),
                "image_alternative",
                image_evidence,
            )

        title = Test611._normalize(str(link.get("title", "")))

        if title:
            return title, "link_title", image_evidence

        return "", "none", image_evidence

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Analyse les liens images candidats au test 6.1.2."""

        soup = Test611._get_dom(context)

        links = [element for element in soup.find_all(True) if self._is_image_link(element)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien image concerné détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        with_alternative = 0
        without_alternative = 0

        for index, link in enumerate(links):
            label, source, images = self._get_image_link_label(link, soup)

            if label:
                with_alternative += 1
            else:
                without_alternative += 1

            context_data = {} if link.name == "area" else Test611._get_context(link)

            findings.append(
                Finding(
                    element=Test611._identifier(link, index),
                    message=(
                        "Le caractère explicite de ce lien image "
                        "nécessite une évaluation de son intitulé "
                        "et éventuellement de son contexte."
                    ),
                    recommendation=(
                        "Vérifier que l'alternative textuelle "
                        "permet de comprendre la fonction et la "
                        "destination du lien, seule ou associée "
                        "à son contexte. Vérifier séparément "
                        "la présence d'un intitulé avec le "
                        "critère RGAA 6.2."
                    ),
                    evidence={
                        "href": link.get("href"),
                        "label": label,
                        "label_source": source,
                        "images": images,
                        "context": context_data,
                    },
                )
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=(
                f"{len(links)} lien(s) image détecté(s) : "
                f"{with_alternative} avec intitulé candidat, "
                f"{without_alternative} sans intitulé détecté. "
                "Leur caractère explicite reste à vérifier."
            ),
            findings=findings,
            tested_elements=len(links),
            metadata={
                "candidate_image_links": len(links),
                "with_label_candidate": with_alternative,
                "without_label_candidate": without_alternative,
                "needs_review": len(links),
                "semantic_analysis_performed": False,
            },
        )


class Test613(Test612):
    """
    RGAA 6.1.3 — Caractère explicite des liens composites.

    Un lien composite associe du texte et un contenu image.

    Cette implémentation extrait les éléments utiles à une
    vérification sémantique, sans produire de verdict RGAA
    automatique sur le caractère explicite du lien.
    """

    test_id = "6.1.3"
    criterion_id = "6.1"

    required_capabilities = frozenset({Capability.DOM})

    @classmethod
    def _is_composite_link(cls, element: Tag) -> bool:
        """Repère les liens contenant texte et image."""

        if element.name == "a" and element.find_parent("svg"):
            return False

        if not Test611._is_link(element):
            return False

        has_image = any(isinstance(child, Tag) and cls._is_image_element(child) for child in element.descendants)

        if not has_image:
            return False

        return bool(cls._visible_link_text(element))

    @classmethod
    def _combined_content(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, list[dict[str, str]]]:
        """
        Reconstitue le contenu candidat dans l'ordre du DOM.

        Le calcul du nom accessible reste approximatif :
        CSS, ARIA complexes et rendu dynamique nécessitent
        une validation dans le navigateur.
        """

        parts: list[str] = []
        image_evidence: list[dict[str, str]] = []

        def visit(node: Tag) -> None:
            for child in node.children:
                if isinstance(child, Tag):
                    if child.name in {
                        "script",
                        "style",
                        "template",
                    }:
                        continue

                    if child.has_attr("hidden"):
                        continue

                    if str(child.get("aria-hidden", "")).strip().lower() == "true":
                        continue

                    if cls._is_image_element(child):
                        alternative, source = cls._image_alternative(child, soup)

                        image_evidence.append(
                            {
                                "element": child.name,
                                "alternative": alternative,
                                "source": source,
                            }
                        )

                        if alternative:
                            parts.append(alternative)

                        # Ne pas traverser une seconde fois
                        # le contenu interne de l'image.
                        continue

                    visit(child)

                else:
                    text = Test611._normalize(str(child))

                    if text:
                        parts.append(text)

        visit(link)

        return (
            Test611._normalize(" ".join(parts)),
            image_evidence,
        )

    @classmethod
    def _get_composite_label(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str, str, list[dict[str, str]]]:
        """
        Retourne :
        - l'intitulé accessible candidat ;
        - sa source ;
        - le contenu texte + alternatives ;
        - les preuves associées aux images.
        """

        combined, images = cls._combined_content(link, soup)

        references = str(link.get("aria-labelledby", "")).split()

        if references:
            texts: list[str] = []

            for reference in references:
                target = soup.find(id=reference)

                if not isinstance(target, Tag):
                    return (
                        "",
                        "aria-labelledby_incomplete",
                        combined,
                        images,
                    )

                text = Test611._normalize(target.get_text(" ", strip=True))

                if not text:
                    return (
                        "",
                        "aria-labelledby_incomplete",
                        combined,
                        images,
                    )

                texts.append(text)

            return (
                " ".join(texts),
                "aria-labelledby",
                combined,
                images,
            )

        aria_label = Test611._normalize(str(link.get("aria-label", "")))

        if aria_label:
            return (
                aria_label,
                "aria-label",
                combined,
                images,
            )

        if combined:
            return (
                combined,
                "combined_content",
                combined,
                images,
            )

        title = Test611._normalize(str(link.get("title", "")))

        if title:
            return (
                title,
                "title",
                combined,
                images,
            )

        return "", "none", combined, images

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Prépare l'évaluation des liens composites."""

        soup = Test611._get_dom(context)

        links = [element for element in soup.find_all(True) if self._is_composite_link(element)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien composite détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        labelled = 0
        unlabelled = 0

        for index, link in enumerate(links):
            (
                label,
                label_source,
                combined,
                images,
            ) = self._get_composite_label(link, soup)

            if label:
                labelled += 1
            else:
                unlabelled += 1

            findings.append(
                Finding(
                    element=Test611._identifier(link, index),
                    message=(
                        "Le caractère explicite de ce lien "
                        "composite nécessite une vérification "
                        "de son intitulé et de son contexte."
                    ),
                    recommendation=(
                        "Vérifier que la combinaison du texte "
                        "et des alternatives des images permet "
                        "de comprendre la fonction et la "
                        "destination du lien. Vérifier aussi "
                        "le nom accessible dans le navigateur."
                    ),
                    evidence={
                        "href": link.get("href"),
                        "label": label,
                        "label_source": label_source,
                        "combined_content": combined,
                        "visible_text": (self._visible_link_text(link)),
                        "images": images,
                        "context": Test611._get_context(link),
                    },
                )
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=(
                f"{len(links)} lien(s) composite(s) : "
                f"{labelled} avec intitulé candidat, "
                f"{unlabelled} sans intitulé confirmé. "
                "Leur caractère explicite reste à vérifier."
            ),
            findings=findings,
            tested_elements=len(links),
            metadata={
                "candidate_composite_links": len(links),
                "with_label_candidate": labelled,
                "without_label_candidate": unlabelled,
                "needs_review": len(links),
                "semantic_analysis_performed": False,
            },
        )


class Test614(RGAATest):
    """
    RGAA 4.1.2 — Test 6.1.4.

    Prépare l'évaluation du caractère explicite des
    liens SVG (<a> descendant d'un <svg>).

    L'analyse du DOM extrait des éléments de preuve.
    La conformité sémantique reste à vérifier.
    """

    test_id = "6.1.4"
    criterion_id = "6.1"

    required_capabilities = frozenset({Capability.DOM})

    LINK_ATTRIBUTES = (
        "href",
        "xlink:href",
        "xlink-href",
        "xlink_href",
        "{http://www.w3.org/1999/xlink}href",
    )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def _get_href(cls, element: Tag) -> str | None:
        """
        Lit les différentes formes possibles de href,
        dont xlink:href pour SVG 1.1.

        Un href vide reste un attribut de lien.
        """
        for attribute in cls.LINK_ATTRIBUTES:
            if element.has_attr(attribute):
                value = element.get(attribute)
                return "" if value is None else str(value)

        return None

    @classmethod
    def _is_svg_link(cls, element: Tag) -> bool:
        """Identifie uniquement les liens internes à un SVG."""
        if element.name != "a":
            return False

        if element.find_parent("svg") is None:
            return False

        return any(element.has_attr(attribute) for attribute in cls.LINK_ATTRIBUTES)

    @classmethod
    def _svg_text(cls, link: Tag) -> str:
        """
        Extrait les textes SVG candidats (<text> et <tspan>).

        Les <tspan> inclus dans un <text> ne sont pas comptés
        une deuxième fois.
        """
        parts: list[str] = []

        for text_element in link.find_all("text"):
            if text_element.has_attr("hidden"):
                continue

            if str(text_element.get("aria-hidden", "")).strip().lower() == "true":
                continue

            value = cls._normalize(text_element.get_text(" ", strip=True))

            if value:
                parts.append(value)

        # <tspan> autonome : cas atypique mais possible
        # dans certains documents SVG.
        for tspan in link.find_all("tspan"):
            if tspan.find_parent("text") is not None:
                continue

            value = cls._normalize(tspan.get_text(" ", strip=True))

            if value:
                parts.append(value)

        return cls._normalize(" ".join(parts))

    @classmethod
    def _referenced_label(
        cls,
        element: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, bool]:
        """Résout les références simples d'aria-labelledby."""

        references = str(element.get("aria-labelledby", "")).split()

        if not references:
            return "", False

        parts: list[str] = []

        for reference in references:
            target = soup.find(id=reference)

            if not isinstance(target, Tag):
                return "", True

            value = cls._normalize(target.get_text(" ", strip=True))

            if not value:
                return "", True

            parts.append(value)

        return " ".join(parts), False

    @classmethod
    def _svg_label(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str, dict[str, str]]:
        """
        Construit une proposition d'intitulé.

        L'ordre de priorité est une approximation du
        nom accessible et non son calcul navigateur.
        """
        svg_root = link.find_parent("svg")
        visible_text = cls._svg_text(link)

        evidence: dict[str, str] = {
            "visible_svg_text": visible_text,
        }

        # Priorité aux mécanismes de nommage présents
        # directement sur le lien SVG.
        if link.has_attr("aria-labelledby"):
            label, incomplete = cls._referenced_label(
                link,
                soup,
            )

            if incomplete or not label:
                return (
                    "",
                    "aria-labelledby_incomplete",
                    evidence,
                )

            return label, "aria-labelledby", evidence

        aria_label = cls._normalize(str(link.get("aria-label", "")))

        if aria_label:
            return aria_label, "aria-label", evidence

        # On récupère ensuite les éventuelles informations
        # portées par le SVG et son contenu.
        if visible_text:
            return visible_text, "svg_text", evidence

        direct_title = link.find("title", recursive=False)

        if isinstance(direct_title, Tag):
            title_text = cls._normalize(direct_title.get_text(" ", strip=True))

            if title_text:
                return title_text, "link_svg_title", evidence

        xlink_title = cls._normalize(
            str(
                link.get(
                    "xlink:title",
                    link.get("xlink-title", ""),
                )
            )
        )

        if xlink_title:
            return xlink_title, "xlink_title", evidence

        if isinstance(svg_root, Tag):
            root_title = svg_root.find(
                "title",
                recursive=False,
            )

            if isinstance(root_title, Tag):
                title_text = cls._normalize(root_title.get_text(" ", strip=True))

                if title_text:
                    evidence["svg_root_title"] = title_text
                    return (
                        title_text,
                        "svg_root_title_candidate",
                        evidence,
                    )

        return "", "none", evidence

    @classmethod
    def _get_svg_context(
        cls,
        link: Tag,
    ) -> dict[str, str]:
        """Collecte un contexte DOM exploitable."""

        context: dict[str, str] = {}
        root = link.find_parent("svg")

        if not isinstance(root, Tag):
            return context

        description = root.find(
            "desc",
            recursive=False,
        )

        if isinstance(description, Tag):
            text = cls._normalize(description.get_text(" ", strip=True))

            if text:
                context["svg_description"] = text

        paragraph = root.find_parent("p")

        if isinstance(paragraph, Tag):
            text = cls._normalize(paragraph.get_text(" ", strip=True))

            if text:
                context["paragraph"] = text

        list_item = root.find_parent("li")

        if isinstance(list_item, Tag):
            text = cls._normalize(list_item.get_text(" ", strip=True))

            if text:
                context["list_item"] = text

        return context

    @staticmethod
    def _identifier(link: Tag, index: int) -> str:
        element_id = link.get("id")

        if isinstance(element_id, str) and element_id.strip():
            return f"a#{element_id}"

        return f"svg a[index={index}]"

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Analyse les liens SVG candidats au test 6.1.4."""
        soup = Test611._get_dom(context)

        links = [element for element in soup.find_all("a") if self._is_svg_link(element)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien SVG concerné détecté.",
                tested_elements=0,
            )

        findings: list[Finding] = []
        with_label = 0
        without_label = 0

        for index, link in enumerate(links):
            label, source, label_evidence = self._svg_label(
                link,
                soup,
            )

            if label:
                with_label += 1
            else:
                without_label += 1

            findings.append(
                Finding(
                    element=self._identifier(link, index),
                    message=(
                        "Le caractère explicite de ce lien SVG "
                        "nécessite une vérification sémantique "
                        "de son intitulé et de son contexte."
                    ),
                    recommendation=(
                        "Vérifier le nom accessible réel du "
                        "lien SVG et confirmer que son intitulé, "
                        "seul ou avec son contexte, permet "
                        "de comprendre sa fonction et sa "
                        "destination."
                    ),
                    evidence={
                        "href": self._get_href(link),
                        "label": label,
                        "label_source": source,
                        "label_evidence": label_evidence,
                        "context": self._get_svg_context(link),
                    },
                )
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.NEEDS_REVIEW,
            summary=(
                f"{len(links)} lien(s) SVG détecté(s) : "
                f"{with_label} avec intitulé candidat, "
                f"{without_label} sans intitulé confirmé. "
                "Le caractère explicite reste à vérifier."
            ),
            findings=findings,
            tested_elements=len(links),
            metadata={
                "candidate_svg_links": len(links),
                "with_label_candidate": with_label,
                "without_label_candidate": without_label,
                "needs_review": len(links),
                "semantic_analysis_performed": False,
            },
        )



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
        value = "".join(
            " " if unicodedata.category(char).startswith("P") else char
            for char in value
        )
        return cls._normalize(value)

    @staticmethod
    def _has_symbol(value: str) -> bool:
        """Repère les symboles potentiellement non littéraux."""
        return any(
            unicodedata.category(char).startswith("S")
            for char in value
        )

    @staticmethod
    def _is_svg_link(element: Tag) -> bool:
        return (
            element.name == "a"
            and element.find_parent("svg") is not None
            and any(
                element.has_attr(attribute)
                for attribute in Test614.LINK_ATTRIBUTES
            )
        )

    @classmethod
    def _is_link(cls, element: Tag) -> bool:
        if cls._is_svg_link(element):
            return True

        if element.name == "area" and element.has_attr("href"):
            return True

        return Test611._is_link(element)

    @staticmethod
    def _is_hidden(element: Tag) -> bool:
        """Vérifie les indices explicites de masquage."""
        for ancestor in [element, *element.parents]:
            if not isinstance(ancestor, Tag):
                continue

            if ancestor.has_attr("hidden"):
                return True

            if (
                str(ancestor.get("aria-hidden", ""))
                .strip()
                .lower()
                == "true"
            ):
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
            return Test614._svg_text(element)

        return Test611._visible_text(element)

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
            references = cls._normalize(
                str(element.get("aria-labelledby", ""))
            ).split()

            if not references:
                return "", "aria-labelledby_empty", True

            texts: list[str] = []

            for reference in references:
                target = soup.find(id=reference)

                if not isinstance(target, Tag):
                    return "", "aria-labelledby_invalid", True

                if (
                    target.find(["img", "svg", "object", "canvas", "math"])
                    is not None
                ):
                    return "", "aria-labelledby_complex", True

                if (
                    target.has_attr("style")
                    or target.has_attr("class")
                    or target.has_attr("aria-label")
                    or target.has_attr("aria-labelledby")
                ):
                    return "", "aria-labelledby_complex", True

                text = cls._normalize(
                    target.get_text(" ", strip=True)
                )

                if not text:
                    return "", "aria-labelledby_empty_target", True

                texts.append(text)

            return " ".join(texts), "aria-labelledby", False

        aria_label = cls._normalize(
            str(element.get("aria-label", ""))
        )

        if aria_label:
            return aria_label, "aria-label", False

        if cls._is_svg_link(element):
            # Le nom d'un lien SVG peut aussi dépendre d'un
            # title ou de mécanismes SVG spécifiques.
            direct_title = element.find("title", recursive=False)

            if isinstance(direct_title, Tag):
                title = cls._normalize(
                    direct_title.get_text(" ", strip=True)
                )

                if title:
                    return title, "svg_title_candidate", True

            xlink_title = cls._normalize(
                str(element.get("xlink:title", ""))
            )

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
            "href": (
                Test614._get_href(link)
                if cls._is_svg_link(link)
                else link.get("href")
            ),
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

        name, source, uncertain = (
            cls._get_accessible_name_candidate(
                link,
                soup,
                visible,
            )
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
                "L'intitulé visible ne permet pas une "
                "comparaison automatique fiable.",
            )

        if comparable_visible in comparable_name:
            return (
                TestStatus.PASS,
                evidence,
                "L'intitulé visible est contenu dans "
                "le nom accessible candidat.",
            )

        return (
            TestStatus.FAIL,
            evidence,
            "Le nom accessible candidat ne contient pas "
            "l'intitulé visible.",
        )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """Exécute le contrôle partiel RGAA 6.1.5."""
        soup = Test611._get_dom(context)

        links = [
            node
            for node in soup.find_all(True)
            if self._is_link(node)
        ]

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
                    element=Test611._identifier(link, index),
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

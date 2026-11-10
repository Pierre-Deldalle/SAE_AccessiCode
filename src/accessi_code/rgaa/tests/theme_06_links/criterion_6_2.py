"""
RGAA 4.1.2 — Thème 6 : Liens.

Critère 6.2 :
Dans chaque page web, chaque lien a-t-il un intitulé ?

Test 6.2.1 :
Contrôle de la présence d'un intitulé de lien.

Analyse partielle du DOM HTML. Les cas nécessitant le
calcul complet du nom accessible sont signalés pour
vérification manuelle.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test621(RGAATest):
    """Vérifie la présence d'un intitulé pour les liens."""

    test_id = "6.2.1"
    criterion_id = "6.2"

    required_capabilities = frozenset({Capability.DOM})

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        links = [element for element in soup.find_all(True) if self._is_link(element)]

        if not links:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun lien concerné détecté.",
            )

        findings: list[Finding] = []
        passed = 0
        failed = 0
        needs_review = 0

        for index, link in enumerate(links):
            identifier = self._identifier(link, index)

            label, source, uncertain = self._get_link_label(
                link,
                soup,
            )

            evidence = {
                "href": link.get("href"),
                "role": link.get("role"),
                "label_source": source,
                "detected_label": label,
            }

            if uncertain:
                needs_review += 1

                findings.append(
                    Finding(
                        element=identifier,
                        message=(
                            "L'intitulé accessible de ce lien ne peut pas être confirmé à partir du DOM statique."
                        ),
                        recommendation=(
                            "Vérifier le nom accessible du lien "
                            "dans le navigateur et avec une "
                            "technologie d'assistance."
                        ),
                        evidence=evidence,
                    )
                )
                continue

            if label:
                passed += 1
                continue

            failed += 1

            findings.append(
                Finding(
                    element=identifier,
                    message=("Aucun intitulé accessible exploitable n'a été détecté pour ce lien."),
                    recommendation=(
                        "Ajouter un texte de lien, une alternative "
                        "textuelle appropriée ou un nom accessible "
                        "adapté à la fonction du lien."
                    ),
                    evidence=evidence,
                )
            )

        if failed:
            status = TestStatus.FAIL
        elif needs_review:
            status = TestStatus.NEEDS_REVIEW
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(links)} lien(s) analysé(s) : "
                f"{passed} avec intitulé détecté, "
                f"{failed} sans intitulé, "
                f"{needs_review} à vérifier."
            ),
            findings=findings,
            tested_elements=len(links),
            metadata={
                "candidate_links": len(links),
                "links_with_label": passed,
                "links_without_label": failed,
                "needs_review": needs_review,
            },
        )

    @staticmethod
    def _get_dom(context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 6.2.1 nécessite un DOM HTML.")
        return context.dom

    @staticmethod
    def _is_link(element: Tag) -> bool:
        """
        Identifie les liens HTML et ARIA.

        Les ancres de positionnement sans href ni role=link
        ne sont pas retenues.
        """
        role = str(element.get("role", "")).strip().lower()

        if role == "link":
            return True

        if element.name == "a" and element.has_attr("href"):
            # Un rôle ARIA explicite différent de link
            # peut changer la nature du composant.
            return role in {"", "link"}

        return False

    @classmethod
    def _get_link_label(
        cls,
        link: Tag,
        soup: BeautifulSoup,
    ) -> tuple[str, str | None, bool]:
        """
        Retourne (intitulé, source, incertain).

        Ce calcul est volontairement partiel : il ne
        remplace pas le calcul du nom accessible du navigateur.
        """

        # Un élément masqué aux technologies d'assistance
        # nécessite une évaluation plus complète.
        if cls._is_aria_hidden(link):
            return "", None, True

        # Priorité 1 : aria-labelledby.
        if link.has_attr("aria-labelledby"):
            ids = str(link.get("aria-labelledby", "")).split()

            if ids:
                texts = []
                missing_reference = False

                for reference_id in ids:
                    target = soup.find(id=reference_id)

                    if not isinstance(target, Tag):
                        missing_reference = True
                        continue

                    text = cls._content_text(target)

                    if text:
                        texts.append(text)

                if texts and not missing_reference:
                    return " ".join(texts), "aria-labelledby", False

                # Le comportement de repli doit être vérifié
                # lorsque les références sont invalides.
                return "", "aria-labelledby", True

        # Priorité 2 : aria-label.
        if link.has_attr("aria-label"):
            label = cls._normalize(str(link.get("aria-label", "")))

            if label:
                return label, "aria-label", False

            # Un attribut vide ne suffit pas à condamner
            # le lien : son contenu peut encore le nommer.

        # Priorité 3 : contenu du lien.
        content_label = cls._content_text(link)

        if content_label:
            return content_label, "content", False

        # Certains contenus peuvent nécessiter une analyse
        # navigateur plutôt qu'un verdict statique.
        if cls._has_complex_content(link):
            return "", "complex_content", True

        # Priorité 4 : title HTML.
        title = cls._normalize(str(link.get("title", "")))

        if title:
            return title, "title", False

        # Les mécanismes dynamiques ne peuvent pas être
        # correctement évalués depuis le seul HTML fourni.
        if cls._has_dynamic_indicators(link):
            return "", "dynamic_content", True

        return "", None, False

    @classmethod
    def _content_text(cls, element: Tag) -> str:
        """Récupère le texte et les alternatives simples."""

        parts: list[str] = []

        for child in element.children:
            if isinstance(child, NavigableString):
                value = cls._normalize(str(child))

                if value:
                    parts.append(value)

            elif isinstance(child, Tag):
                if child.name in {
                    "script",
                    "style",
                    "template",
                }:
                    continue

                if cls._is_aria_hidden(child):
                    continue

                if child.name in {"img", "area"}:
                    alternative = cls._normalize(str(child.get("alt", "")))

                    if alternative:
                        parts.append(alternative)
                    continue

                if child.name == "svg":
                    svg_title = child.find("title")

                    if isinstance(svg_title, Tag):
                        value = cls._normalize(svg_title.get_text(" ", strip=True))

                        if value:
                            parts.append(value)
                    continue

                nested = cls._content_text(child)

                if nested:
                    parts.append(nested)

        return cls._normalize(" ".join(parts))

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalise les espaces sans modifier le contenu."""
        return " ".join(text.split())

    @staticmethod
    def _is_aria_hidden(element: Tag) -> bool:
        return str(element.get("aria-hidden", "")).strip().lower() == "true"

    @staticmethod
    def _has_complex_content(element: Tag) -> bool:
        """
        Repère du contenu qui demande une vérification
        du nom accessible dans le navigateur.
        """
        for child in element.descendants:
            if not isinstance(child, Tag):
                continue

            if child.name in {"svg", "canvas", "object"}:
                return True

            if child.has_attr("aria-labelledby"):
                return True

            if child.has_attr("aria-label"):
                return True

        return False

    @staticmethod
    def _has_dynamic_indicators(element: Tag) -> bool:
        """Repère des indices de comportement dynamique."""

        for attribute in element.attrs:
            name = str(attribute).lower()

            if name.startswith("on"):
                return True

            if name.startswith("data-"):
                return True

        href = str(element.get("href", "")).strip().lower()

        return href.startswith("javascript:")

    @staticmethod
    def _identifier(element: Tag, index: int) -> str:
        element_id = element.get("id")

        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={index}]"

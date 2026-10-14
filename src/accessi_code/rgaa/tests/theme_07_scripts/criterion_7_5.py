# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus, Finding
from accessi_code.rgaa.base import RGAATest
from bs4 import BeautifulSoup, Tag
import re


class Test751(RGAATest):
    test_id = "7.5.1"
    criterion_id = "7.5"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        status_candidates = []

        all_elements = soup.find_all(True)
        for element in all_elements:
            if element.name in ['script', 'style']:
                continue

            text = element.get_text(strip=True)
            if text and len(text) > 0:
                if self._is_status_message_state(text):
                    status_candidates.append(element)

        elements_with_role = soup.find_all(attrs={"role": True})
        for element in elements_with_role:
            role = element.get("role")
            if role in ["status", "log", "progressbar", "alert"]:
                if element not in status_candidates:
                    status_candidates.append(element)

        elements_with_aria_live = soup.find_all(attrs={"aria-live": True})
        for element in elements_with_aria_live:
            if element not in status_candidates:
                status_candidates.append(element)

        status_candidates = self._filter_container_elements(status_candidates, soup)

        if not status_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun message de statut détecté.",
            )

        findings: list = []
        compliant_count = 0

        for element in status_candidates:
            role = element.get("role")
            aria_live = element.get("aria-live")
            aria_atomic = element.get("aria-atomic")

            is_compliant = False

            if role == "status":
                is_compliant = True
            elif aria_live == "polite" and aria_atomic == "true":
                is_compliant = True

            if is_compliant:
                compliant_count += 1
            else:
                element_id = self._get_element_id(element)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Le message de statut n'utilise pas le rôle WAI-ARIA approprié ou les attributs aria-live/aria-atomic requis.",
                        recommendation=("Utiliser role='status' ou les attributs aria-live='polite' et aria-atomic='true' pour les messages de statut."),
                    )
                )

        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(status_candidates)} message(s) de statut détecté(s) : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(status_candidates),
        )

    def _is_status_message_state(self, text: str) -> bool:
        text_lower = text.lower().strip()

        state_indicators = [
            r'\bterminé\b',
            r'\bcompleted\b',
            r'\bfinished\b',
            r'\bsauvegarde?\s*réussie?\b',
            r'\bsave\s*successful\b',
            r'\bchargement\s*terminé\b',
            r'\bloading\s*completed\b',
            r'\btéléchargement\s*terminé\b',
            r'\bdownload\s*completed\b',
            r'\bopération\s*réussie\b',
            r'\boperation\s*successful\b',
            r'\bmise\s*à\s*jour\s*effectuée\b',
            r'\bupdate\s*completed\b',
            r'\b enregistrée?\b',
            r'\bsaved\b',
            r'\b valide\b',
            r'\bvalid\b',
            r'\bcorrect\b',
            r'\bconforme\b',
            r'\bnon\s*conforme\b',
            r'\bétat\b',
            r'\bstate\b',
            r'\bstatus\b',
            r'\bcondition\b',
        ]

        for pattern in state_indicators:
            if re.search(pattern, text_lower):
                return True

        return False

    def _get_element_id(self, element: Tag) -> str:
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={len(element.find_previous_siblings())}]"

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 7.5.1 nécessite un DOM.")

        return context.dom

    def _filter_container_elements(self, candidates: list[Tag], soup: BeautifulSoup) -> list[Tag]:
        if len(candidates) <= 1:
            return candidates

        candidate_set = set(candidates)
        filtered_candidates = []

        for element in candidates:
            direct_text = self._get_direct_text_content(element)

            if not direct_text.strip():
                text_children = [
                    child for child in element.children
                    if isinstance(child, Tag) and child.get_text(strip=True)
                ]

                if text_children and all(child in candidate_set for child in text_children):
                    continue

            filtered_candidates.append(element)

        return filtered_candidates

    def _get_direct_text_content(self, element: Tag) -> str:
        direct_text_parts = []
        for content in element.contents:
            if isinstance(content, str):
                direct_text_parts.append(content)
        return ''.join(direct_text_parts)


class Test752(RGAATest):
    test_id = "7.5.2"
    criterion_id = "7.5"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        status_candidates = []

        all_elements = soup.find_all(True)
        for element in all_elements:
            if element.name in ['script', 'style']:
                continue

            text = element.get_text(strip=True)
            if text and len(text) > 0:
                if self._is_status_message_suggestion_error(text):
                    status_candidates.append(element)

        elements_with_role = soup.find_all(attrs={"role": True})
        for element in elements_with_role:
            role = element.get("role")
            if role in ["status", "log", "progressbar", "alert"]:
                if element not in status_candidates:
                    status_candidates.append(element)

        elements_with_aria_live = soup.find_all(attrs={"aria-live": True})
        for element in elements_with_aria_live:
            if element not in status_candidates:
                status_candidates.append(element)

        status_candidates = self._filter_container_elements(status_candidates, soup)

        if not status_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun message de statut détecté.",
            )

        findings: list = []
        compliant_count = 0

        for element in status_candidates:
            role = element.get("role")
            aria_live = element.get("aria-live")
            aria_atomic = element.get("aria-atomic")

            is_compliant = False

            if role == "alert":
                is_compliant = True
            elif aria_live == "assertive" and aria_atomic == "true":
                is_compliant = True

            if is_compliant:
                compliant_count += 1
            else:
                element_id = self._get_element_id(element)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Le message de suggestion ou d'erreur n'utilise pas le rôle WAI-ARIA approprié ou les attributs aria-live/aria-atomic requis.",
                        recommendation=("Utiliser role='alert' ou les attributs aria-live='assertive' et aria-atomic='true' pour les messages de suggestion ou d'erreur."),
                    )
                )

        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(status_candidates)} message(s) de statut détecté(s) : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(status_candidates),
        )

    def _is_status_message_suggestion_error(self, text: str) -> bool:
        text_lower = text.lower().strip()

        error_indicators = [
            r'\berreur\b',
            r'\berror\b',
            r'\bavertissement\b',
            r'\bwarning\b',
            r'\battention\b',
            r'\b caution\b',
            r'\bproblème\b',
            r'\bproblem\b',
            r'\bdifficulté\b',
            r'\bdifficulty\b',
            r'\bechoue?\b',
            r'\bfailed\b',
            r'\b échoué\b',
            r'\b inattendu\b',
            r'\b unexpected\b',
            r'\b invalide\b',
            r'\b invalid\b',
            r'\b incorrect\b',
            r'\b suggestion\b',
            r'\b conseille?\b',
            r'\b recommande?\b',
            r'\b recommend\b',
        ]

        absence_indicators = [
            r'\baucu?n?\s+message\s+d\'?erreur\b',
            r'\bno\s+error\s+message\b',
            r'\bpas\s+d\'?erreur\b',
            r'\bsans\s+erreur\b',
            r'\bwithout\s+error\b',
        ]

        for pattern in absence_indicators:
            if re.search(pattern, text_lower):
                return False

        for pattern in error_indicators:
            if re.search(pattern, text_lower):
                return True

        return False

    def _get_element_id(self, element: Tag) -> str:
        """Generate a unique identifier for an element."""
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        # Fallback to index-based identifier
        return f"{element.name}[index={len(element.find_previous_siblings())}]"

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 7.5.2 nécessite un DOM.")

        return context.dom

    def _filter_container_elements(self, candidates: list[Tag], soup: BeautifulSoup) -> list[Tag]:
        if len(candidates) <= 1:
            return candidates

        # Create a set for faster lookup
        candidate_set = set(candidates)
        filtered_candidates = []

        for element in candidates:
            # Get the element's direct text content (not including children's text)
            direct_text = self._get_direct_text_content(element)

            # If the element has no direct text content of its own,
            # and all of its text-containing children are status candidates,
            # then this is likely just a container wrapper
            if not direct_text.strip():
                # Check if all text-containing children are already status candidates
                text_children = [
                    child for child in element.children
                    if isinstance(child, Tag) and child.get_text(strip=True)
                ]

                if text_children and all(child in candidate_set for child in text_children):
                    # This element is just a container - skip it
                    continue

            # Otherwise, keep this element
            filtered_candidates.append(element)

        return filtered_candidates

    def _get_direct_text_content(self, element: Tag) -> str:
        direct_text_parts = []
        for content in element.contents:
            if isinstance(content, str):
                direct_text_parts.append(content)
            # Skip Tag objects - we only want direct text
        return ''.join(direct_text_parts)


class Test753(RGAATest):
    test_id = "7.5.3"
    criterion_id = "7.5"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = self._get_dom(context)

        status_candidates = []

        all_elements = soup.find_all(True)
        for element in all_elements:
            if element.name in ['script', 'style']:
                continue

            text = element.get_text(strip=True)
            if text and len(text) > 0:
                if self._is_status_message_process_progression(text):
                    status_candidates.append(element)

        elements_with_role = soup.find_all(attrs={"role": True})
        for element in elements_with_role:
            role = element.get("role")
            if role in ["status", "log", "progressbar"]:
                if element not in status_candidates:
                    status_candidates.append(element)

        elements_with_aria_live = soup.find_all(attrs={"aria-live": True})
        for element in elements_with_aria_live:
            if element not in status_candidates:
                status_candidates.append(element)

        status_candidates = self._filter_container_elements(status_candidates, soup)

        if not status_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun message de statut détecté.",
            )

        findings: list = []
        compliant_count = 0

        for element in status_candidates:
            role = element.get("role")
            aria_live = element.get("aria-live")
            aria_atomic = element.get("aria-atomic")

            is_compliant = False

            if role in ["log", "progressbar", "status"]:
                is_compliant = True
            elif aria_live == "polite":
                is_compliant = True
            elif aria_live == "polite" and aria_atomic == "true":
                is_compliant = True

            if is_compliant:
                compliant_count += 1
            else:
                element_id = self._get_element_id(element)
                findings.append(
                    Finding(
                        element=element_id,
                        message="Le message indiquant la progression d'un processus n'utilise pas le rôle WAI-ARIA approprié ou les attributs aria-live/aria-atomic requis.",
                        recommendation=("Utiliser role='log', role='progressbar', ou role='status' ; ou les attributs aria-live='polite' (pour log) ou aria-live='polite' et aria-atomic='true' (pour status)."),
                    )
                )

        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"{len(status_candidates)} message(s) de statut détecté(s) : "
                f"{compliant_count} conforme(s), {len(findings)} non conforme(s)."
            ),
            findings=findings,
            tested_elements=len(status_candidates),
        )

    def _is_status_message_process_progression(self, text: str) -> bool:
        text_lower = text.lower().strip()

        progression_indicators = [
            r'\b(en\s+cours?|in\s+progress)\b',
            r'\bchargement\b',
            r'\bloading\b',
            r'\btéléchargement\b',
            r'\bdownload\b',
            r'\btraitement\b',
            r'\bprocessing\b',
            r'\betape\s*\d+\b',
            r'\bstep\s*\d+\b',
            r'\bprogression\b',
            r'\bprogress\b',
            r'\battente?\b',
            r'\bwait(ing)?\b',
            r'\bpause?\b',
            r'\binitialisation\b',
            r'\binitialization\b',
            r'\bfinalisation\b',
            r'\bfinalization\b',
            r'\bsynchronisation\b',
            r'\bsynchronization\b',
            r'\b mise\s*en\s*mémoire\s*tampon\b',
            r'\b buffering\b',
            r'\betape\b',
            r'\bstep\b',
            r'\bterminé\b',
            r'\bcompleted\b',
            r'\bfinished\b',
        ]

        for pattern in progression_indicators:
            if re.search(pattern, text_lower):
                return True

        return False

    def _get_element_id(self, element: Tag) -> str:
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            return f"{element.name}#{element_id}"

        return f"{element.name}[index={len(element.find_previous_siblings())}]"

    @staticmethod
    def _get_dom(
        context: AuditContext,
    ) -> BeautifulSoup:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 7.5.3 nécessite un DOM.")

        return context.dom

    def _filter_container_elements(self, candidates: list[Tag], soup: BeautifulSoup) -> list[Tag]:
        if len(candidates) <= 1:
            return candidates

        candidate_set = set(candidates)
        filtered_candidates = []

        for element in candidates:
            direct_text = self._get_direct_text_content(element)

            if not direct_text.strip():
                text_children = [
                    child for child in element.children
                    if isinstance(child, Tag) and child.get_text(strip=True)
                ]

                if text_children and all(child in candidate_set for child in text_children):
                    continue

            filtered_candidates.append(element)

        return filtered_candidates

    def _get_direct_text_content(self, element: Tag) -> str:
        direct_text_parts = []
        for content in element.contents:
            if isinstance(content, str):
                direct_text_parts.append(content)
        return ''.join(direct_text_parts)
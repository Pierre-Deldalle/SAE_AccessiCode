from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class IntegrityGrade:
    """
    Évaluation déterministe de l'intégrité technique d'une réponse IA.

    Cette note ne juge PAS si l'explication est sémantiquement correcte.
    Elle détecte uniquement certaines formes de génération dégradée.
    """

    score: float
    issues: tuple[str, ...] = ()


class ResponseIntegrityGrader:
    """
    Détecte des anomalies de génération sans utiliser d'autre IA.
    """

    PENALTIES: dict[str, float] = {
        "missing_explanation": 25.0,
        "fallback_explanation": 20.0,
        "meta_generation_marker": 40.0,
        "excessive_repetition": 30.0,
        "overlong_output": 20.0,
        "truncated_explanation": 15.0,
    }

    META_MARKERS = (
        "the user's prompt",
        "the user wants",
        "let me re-read",
        "let me reread",
        "system prompt",
        "thought:",
        "thoughtful_content:",
        "analysis:",
        "<|assistant|>",
        "<|system|>",
    )

    def grade(
        self,
        actual: dict[str, Any],
    ) -> IntegrityGrade:
        issues: list[str] = []

        explanation = actual.get("explanation")

        if not isinstance(explanation, str) or not explanation.strip():
            issues.append(
                "missing_explanation",
            )
            explanation_text = ""

        else:
            explanation_text = explanation.strip()

            if self._is_fallback_explanation(
                explanation_text,
            ):
                issues.append(
                    "fallback_explanation",
                )

            if self._looks_truncated(
                explanation_text,
            ):
                issues.append(
                    "truncated_explanation",
                )

        texts = self._collect_texts(actual)

        combined_text = "\n".join(texts)

        if self._contains_meta_marker(
            combined_text,
        ):
            issues.append(
                "meta_generation_marker",
            )

        if any(self._has_excessive_repetition(text) for text in texts):
            issues.append(
                "excessive_repetition",
            )

        if self._is_overlong(texts):
            issues.append(
                "overlong_output",
            )

        # Évite de compter deux fois le même problème.
        unique_issues = tuple(dict.fromkeys(issues))

        penalty = sum(self.PENALTIES[issue] for issue in unique_issues)

        return IntegrityGrade(
            score=max(
                0.0,
                100.0 - penalty,
            ),
            issues=unique_issues,
        )

    @staticmethod
    def _collect_texts(
        actual: dict[str, Any],
    ) -> list[str]:
        texts: list[str] = []

        for key in (
            "explanation",
            "uncertainties",
            "contradictions",
        ):
            value = actual.get(key)

            if isinstance(value, str):
                texts.append(value)

            elif isinstance(value, list):
                texts.extend(str(item) for item in value if item is not None)

        return texts

    @staticmethod
    def _is_fallback_explanation(
        explanation: str,
    ) -> bool:
        lowered = explanation.casefold()

        return "n'a pas pu être détermin" in lowered

    def _contains_meta_marker(
        self,
        text: str,
    ) -> bool:
        lowered = text.casefold()

        return any(marker.casefold() in lowered for marker in self.META_MARKERS)

    @staticmethod
    def _looks_truncated(
        explanation: str,
    ) -> bool:
        text = explanation.strip()

        if not text:
            return False

        bracket_pairs = (
            ("(", ")"),
            ("[", "]"),
            ("{", "}"),
        )

        for opening, closing in bracket_pairs:
            if text.count(opening) > text.count(closing):
                return True

        if text.endswith(
            (
                "(",
                "[",
                "{",
                "/",
                "\\",
                "-",
            )
        ):
            return True

        return False

    @staticmethod
    def _is_overlong(
        texts: list[str],
    ) -> bool:
        if any(len(text) > 1000 for text in texts):
            return True

        total_length = sum(len(text) for text in texts)

        return total_length > 2500

    @staticmethod
    def _has_excessive_repetition(
        text: str,
    ) -> bool:
        """
        Détecte plusieurs répétitions consécutives d'un mot
        ou d'un petit groupe de mots.

        Exemples détectés :
        - "que que que que que"
        - "Mismatch-Mismatch-Mismatch..."
        - "de de de de..."
        - répétition d'un bigramme ou trigramme.
        """
        tokens = re.findall(
            r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_']+",
            text.casefold(),
        )

        if len(tokens) < 4:
            return False

        for group_size in (
            1,
            2,
            3,
        ):
            required_length = group_size * 4

            if len(tokens) < required_length:
                continue

            for start in range(len(tokens) - required_length + 1):
                group = tokens[start : start + group_size]

                repeated = True

                for repetition in range(
                    1,
                    4,
                ):
                    other_start = start + repetition * group_size

                    other_group = tokens[other_start : other_start + group_size]

                    if other_group != group:
                        repeated = False
                        break

                if repeated:
                    return True

        return False

from __future__ import annotations

from dataclasses import dataclass

from accessi_code.ai.schemas import AIConfidence

DecisionValue = bool | None


@dataclass(frozen=True, slots=True)
class DecisionGrade:
    """
    Résultat de l'évaluation du verdict principal produit par l'IA.

    score :
        note comprise entre 0 et 100.

    correct :
        True uniquement lorsque le verdict obtenu correspond exactement
        au verdict humain attendu.

    issues :
        codes décrivant les problèmes détectés afin de permettre
        la production de métriques détaillées.
    """

    correct: bool
    score: float
    issues: tuple[str, ...] = ()


class DecisionGrader:
    """
    Évalue conjointement :

    - le verdict produit par l'IA ;
    - le verdict humain attendu ;
    - la confiance exprimée par l'IA.

    La confiance ne peut pas rendre une mauvaise réponse correcte.
    Elle sert uniquement à récompenser ou pénaliser la manière
    dont le modèle estime sa propre certitude.
    """

    CORRECT_SCORES: dict[AIConfidence, float] = {
        "high": 100.0,
        "medium": 90.0,
        "low": 75.0,
    }

    # Le modèle refuse de conclure alors qu'un verdict était possible.
    ABSTENTION_SCORES: dict[AIConfidence, float] = {
        "low": 60.0,
        "medium": 50.0,
        "high": 40.0,
    }

    # Le modèle force un verdict alors que les informations
    # ne permettaient pas de conclure.
    FORCED_VERDICT_SCORES: dict[AIConfidence, float] = {
        "low": 30.0,
        "medium": 15.0,
        "high": 0.0,
    }

    # Le modèle choisit le verdict binaire opposé.
    WRONG_VERDICT_SCORES: dict[AIConfidence, float] = {
        "low": 20.0,
        "medium": 10.0,
        "high": 0.0,
    }

    def grade(
        self,
        *,
        expected: DecisionValue,
        actual: DecisionValue,
        confidence: AIConfidence,
    ) -> DecisionGrade:
        self._validate_decision(
            expected,
            field_name="expected",
        )
        self._validate_decision(
            actual,
            field_name="actual",
        )
        self._validate_confidence(confidence)

        # Réponse exactement correcte.
        if actual is expected:
            issues: list[str] = []

            if confidence == "low":
                issues.append(
                    "unnecessary_low_confidence",
                )

            return DecisionGrade(
                correct=True,
                score=self.CORRECT_SCORES[confidence],
                issues=tuple(issues),
            )

        # Le modèle répond null alors qu'un verdict était possible.
        if expected is not None and actual is None:
            issues = [
                "unnecessary_abstention",
            ]

            if confidence == "high":
                issues.append(
                    "critical_confidence_error",
                )

            return DecisionGrade(
                correct=False,
                score=self.ABSTENTION_SCORES[confidence],
                issues=tuple(issues),
            )

        # Le modèle force true/false alors que null était attendu.
        if expected is None and actual is not None:
            issues = [
                "forced_verdict",
            ]

            if confidence == "high":
                issues.append(
                    "critical_confidence_error",
                )

            return DecisionGrade(
                correct=False,
                score=self.FORCED_VERDICT_SCORES[confidence],
                issues=tuple(issues),
            )

        # Il ne reste que true <-> false.
        issues = [
            "wrong_verdict",
        ]

        if confidence == "high":
            issues.append(
                "critical_confidence_error",
            )

        return DecisionGrade(
            correct=False,
            score=self.WRONG_VERDICT_SCORES[confidence],
            issues=tuple(issues),
        )

    @staticmethod
    def _validate_decision(
        value: DecisionValue,
        *,
        field_name: str,
    ) -> None:
        if (
            value is not True
            and value is not False
            and value is not None
        ):
            raise ValueError(
                f"{field_name} doit être true, false ou null."
            )

    @staticmethod
    def _validate_confidence(
        confidence: str,
    ) -> None:
        if confidence not in {
            "low",
            "medium",
            "high",
        }:
            raise ValueError(
                "confidence doit être 'low', 'medium' ou 'high'."
            )

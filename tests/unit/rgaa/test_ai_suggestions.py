"""Propositions de correction de l'IA dans les recommandations (Verdict.recommendation)."""

import asyncio

from ai_fakes import relevance, text_services

from accessi_code.ai.schemas import RelevanceItem
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import Verdict, judge_relevance

BASE = "Rendre l'intitulé du lien explicite."


def _judge(answer) -> Verdict:
    services = text_services(relevance_answer=answer)
    [verdict] = asyncio.run(judge_relevance(services, "link", [RelevanceItem("En savoir plus")]))
    return verdict


def test_suggestion_is_added_to_recommendation_on_fail():
    verdict = _judge(relevance(False, suggestion="Horaires d'ouverture du magasin"))

    assert verdict.status is TestStatus.FAIL
    assert verdict.recommendation(BASE) == f"{BASE} Proposition : Horaires d'ouverture du magasin"


def test_suggestion_without_base_recommendation():
    verdict = _judge(relevance(False, suggestion="Horaires d'ouverture"))

    assert verdict.recommendation(None) == "Proposition : Horaires d'ouverture"


def test_suggestion_is_ignored_on_pass():
    verdict = _judge(relevance(True, suggestion="Texte inutile"))

    assert verdict.status is TestStatus.PASS
    assert verdict.suggestion is None
    assert verdict.recommendation(BASE) == BASE


def test_low_confidence_needs_review_without_suggestion():
    verdict = _judge(relevance(False, confidence="low", suggestion="Horaires d'ouverture"))

    # La proposition ne change jamais le statut : confiance faible → NEEDS_REVIEW.
    assert verdict.status is TestStatus.NEEDS_REVIEW
    assert verdict.suggestion is None
    assert verdict.recommendation(BASE) == BASE


def test_unknown_conclusion_needs_review_without_suggestion():
    verdict = _judge(relevance(None, suggestion="Horaires d'ouverture"))

    assert verdict.status is TestStatus.NEEDS_REVIEW
    assert verdict.recommendation(BASE) == BASE


def test_fail_without_suggestion_keeps_recommendation():
    verdict = _judge(relevance(False))

    assert verdict.status is TestStatus.FAIL
    assert verdict.suggestion is None
    assert verdict.recommendation(BASE) == BASE


def test_blank_suggestion_is_ignored():
    verdict = _judge(relevance(False, suggestion="   "))

    assert verdict.recommendation(BASE) == BASE


def test_no_suggestion_without_ai_or_on_error():
    [unavailable] = asyncio.run(judge_relevance(None, "link", [RelevanceItem("En savoir plus")]))
    failing = text_services(relevance_answer=RuntimeError("panne"))
    [error] = asyncio.run(judge_relevance(failing, "link", [RelevanceItem("En savoir plus")]))

    assert unavailable.status is TestStatus.NEEDS_REVIEW
    assert error.status is TestStatus.ERROR
    assert unavailable.recommendation(BASE) == BASE
    assert error.recommendation(BASE) == BASE


def test_suggestion_is_kept_in_finding_evidence():
    verdict = _judge(relevance(False, suggestion="Horaires d'ouverture"))

    assert verdict.evidence["analysis"]["suggestion"] == "Horaires d'ouverture"


def test_analysis_without_suggestion_field_does_not_break():
    verdict = Verdict(TestStatus.FAIL, explanation="x", analysis=object())

    assert verdict.suggestion is None
    assert verdict.recommendation(BASE) == BASE

"""Comptage des tokens consommés par les appels à l'IA pendant un audit."""

import asyncio

import pytest

from accessi_code.ai.token_usage import TokenUsage, format_tokens, record_response, track_tokens


def test_responses_are_counted_only_inside_an_audit():
    record_response({"prompt_eval_count": 100, "eval_count": 20})  # hors audit : ignorée

    with track_tokens() as usage:
        record_response({"prompt_eval_count": 1200, "eval_count": 80})
        record_response({"prompt_eval_count": 300})  # réponse sans eval_count
        record_response({"prompt_eval_count": "?", "eval_count": -5})  # valeurs invalides

    assert (usage.prompt_tokens, usage.completion_tokens, usage.total, usage.calls) == (1500, 80, 1580, 3)


def test_calls_from_child_tasks_and_threads_are_counted():
    async def call() -> None:
        await asyncio.sleep(0)
        record_response({"eval_count": 10})

    async def audit() -> TokenUsage:
        with track_tokens() as usage:
            await asyncio.gather(*(call() for _ in range(3)))
            await asyncio.create_task(call())
            await asyncio.to_thread(record_response, {"prompt_eval_count": 5})
            return usage

    usage = asyncio.run(audit())
    assert usage.total == 45


def test_two_audits_do_not_mix_their_counts():
    async def audit(tokens: int) -> int:
        with track_tokens() as usage:
            for _ in range(5):
                await asyncio.sleep(0)
                record_response({"eval_count": tokens})
            return usage.total

    async def both():
        return await asyncio.gather(audit(1), audit(100))

    assert asyncio.run(both()) == [5, 500]


@pytest.mark.parametrize(("count", "text"), [(0, "0 token"), (1, "1 token"), (12345, "12 345 tokens")])
def test_format_tokens(count, text):
    assert format_tokens(count) == text
